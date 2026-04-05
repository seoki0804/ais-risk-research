#!/usr/bin/env python3
"""Validate the remaining human-input fields for 61day submission handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=(
            "/Users/seoki/Desktop/research/outputs/"
            "presentation_deck_outline_61day_2026-03-13/"
            "submission_intake_template_61day.json"
        ),
        help="Path to the submission intake JSON file.",
    )
    parser.add_argument(
        "--output",
        default=(
            "/Users/seoki/Desktop/research/outputs/"
            "presentation_deck_outline_61day_2026-03-13/"
            "submission_intake_validation_61day.md"
        ),
        help="Path to write the markdown validation report.",
    )
    return parser.parse_args()


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def review_mode_is_blind(review_mode: str) -> bool:
    return "blind" in review_mode.lower()


def get_nested(data: dict[str, Any], keys: list[str]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def require(data: dict[str, Any], keys: list[str], sink: list[str]) -> None:
    value = get_nested(data, keys)
    if is_empty(value):
        sink.append(".".join(keys))


def validate(data: dict[str, Any]) -> dict[str, list[str]]:
    venue_missing: list[str] = []
    author_missing: list[str] = []
    disclosure_missing: list[str] = []
    release_missing: list[str] = []
    portal_missing: list[str] = []

    for keys in (
        ["venue", "name"],
        ["venue", "type"],
        ["venue", "template_type"],
        ["venue", "review_mode"],
        ["venue", "main_page_limit"],
        ["venue", "supplementary_policy"],
        ["venue", "abstract_word_limit"],
        ["venue", "keyword_limit"],
    ):
        require(data, keys, venue_missing)

    for keys in (
        ["authors", "author_names"],
        ["authors", "affiliations"],
        ["authors", "corresponding_author_name"],
        ["authors", "corresponding_author_email"],
    ):
        require(data, keys, author_missing)

    for keys in (
        ["release_policy", "submission_has_anonymized_repo"],
        ["release_policy", "code_release_timing"],
    ):
        require(data, keys, release_missing)

    for keys in (
        ["portal_selection", "chosen_abstract_variant"],
        ["portal_selection", "chosen_keyword_set"],
    ):
        require(data, keys, portal_missing)

    review_mode = str(get_nested(data, ["venue", "review_mode"]) or "")
    if review_mode_is_blind(review_mode):
        for keys in (
            ["venue", "repository_link_allowed"],
            ["venue", "supplementary_anonymity_required"],
        ):
            require(data, keys, venue_missing)

    if get_nested(data, ["release_policy", "submission_has_anonymized_repo"]) is True:
        require(data, ["release_policy", "repo_url"], release_missing)

    if get_nested(data, ["venue", "data_code_field_required"]) is True:
        for keys in (
            ["release_policy", "data_availability_final_text"],
            ["release_policy", "code_availability_final_text"],
        ):
            require(data, keys, release_missing)

    if get_nested(data, ["venue", "author_contribution_required"]) is True:
        require(data, ["authors", "author_contribution_statement"], author_missing)

    if get_nested(data, ["venue", "funding_statement_required"]) is True:
        require(data, ["disclosures", "funding_statement"], disclosure_missing)

    if get_nested(data, ["venue", "conflict_statement_required"]) is True:
        require(data, ["disclosures", "conflict_statement"], disclosure_missing)

    track = get_nested(data, ["venue", "track_or_subject_area"])
    if not is_empty(track):
        require(data, ["portal_selection", "chosen_track"], portal_missing)

    return {
        "venue_policy": venue_missing,
        "author_metadata": author_missing,
        "disclosures": disclosure_missing,
        "release_policy": release_missing,
        "portal_selection": portal_missing,
    }


def build_report(input_path: Path, missing: dict[str, list[str]]) -> str:
    total_missing = sum(len(items) for items in missing.values())
    status = "READY" if total_missing == 0 else "BLOCKED"
    lines = [
        "# Submission Intake Validation 61day",
        "",
        f"- Status: `{status}`",
        f"- Input: `{input_path}`",
        f"- Missing field count: `{total_missing}`",
        "",
        "## Summary",
    ]

    if total_missing == 0:
        lines.append("- No required human-input field is missing under the current rules.")
    else:
        lines.append(
            "- The technical packet is ready, but the fields below still require human input."
        )

    for section, items in missing.items():
        lines.extend(["", f"## {section.replace('_', ' ').title()}"])
        if not items:
            lines.append("- none")
            continue
        for item in items:
            lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Interpretation",
            "- `READY` means the intake JSON contains the minimum operational inputs needed for final handoff.",
            "- `BLOCKED` means venue policy, author metadata, or release-policy values are still missing.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    missing = validate(data)
    report = build_report(input_path, missing)
    output_path.write_text(report, encoding="utf-8")

    total_missing = sum(len(items) for items in missing.values())
    status = "READY" if total_missing == 0 else "BLOCKED"
    print(f"Status: {status}")
    print(f"Missing field count: {total_missing}")
    print(f"Report: {output_path}")


if __name__ == "__main__":
    main()
