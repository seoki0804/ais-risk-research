#!/usr/bin/env python3
"""Interactively fill the 61day submission intake JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13/"
    "submission_intake_template_61day.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to the submission intake JSON file to edit in place.",
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


def prompt_text(
    label: str,
    current: str,
    *,
    suggestion: str | None = None,
    hint: str | None = None,
) -> str:
    prompt_parts = [label]
    if hint:
        prompt_parts.append(f"[{hint}]")
    if not is_empty(current):
        prompt_parts.append(f"(current: {current})")
    elif suggestion is not None and suggestion != "":
        prompt_parts.append(f"(suggested: {suggestion})")
    prompt = " ".join(prompt_parts) + ": "

    entered = input(prompt).strip()
    if entered:
        return entered
    if not is_empty(current):
        return current
    if suggestion is not None:
        return suggestion
    return ""


def prompt_bool(
    label: str,
    current: bool | None,
    *,
    suggestion: bool | None = None,
    hint: str | None = None,
) -> bool | None:
    current_text = (
        "true"
        if current is True
        else "false"
        if current is False
        else ""
    )
    suggestion_text = (
        "true"
        if suggestion is True
        else "false"
        if suggestion is False
        else ""
    )

    prompt_parts = [label]
    if hint:
        prompt_parts.append(f"[{hint}]")
    if current_text:
        prompt_parts.append(f"(current: {current_text})")
    elif suggestion_text:
        prompt_parts.append(f"(suggested: {suggestion_text})")
    prompt = " ".join(prompt_parts) + ": "

    while True:
        entered = input(prompt).strip().lower()
        if entered == "":
            if current is not None:
                return current
            return suggestion
        if entered in {"y", "yes", "true", "t", "1"}:
            return True
        if entered in {"n", "no", "false", "f", "0"}:
            return False
        if entered in {"null", "none"}:
            return None
        print("Enter yes/no/true/false or press Enter to keep the current/suggested value.")


def prompt_list(
    label: str,
    current: list[str],
    *,
    separator: str,
    hint: str,
) -> list[str]:
    current_text = separator.join(current)
    prompt = f"{label} [{hint}]"
    if current_text:
        prompt += f" (current: {current_text})"
    prompt += ": "

    entered = input(prompt).strip()
    if not entered:
        return current
    items = [item.strip() for item in entered.split(separator) if item.strip()]
    return items


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)

    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    print("61day submission intake interactive fill")
    print(f"Editing: {input_path}")
    print("Press Enter to keep the current value or accept the suggested value.")
    print()

    submission_mode = prompt_text(
        "submission_mode",
        str(data.get("submission_mode", "")),
        suggestion="blind",
        hint="blind / camera-ready",
    )
    data["submission_mode"] = submission_mode

    venue = data["venue"]
    authors = data["authors"]
    release = data["release_policy"]
    portal = data["portal_selection"]

    default_review_mode = "double-blind" if "blind" in submission_mode.lower() else "single-blind"

    print("\n[Venue core]")
    venue["name"] = prompt_text("venue.name", venue.get("name", ""), hint="example: IEEE OCEANS 2026")
    venue["type"] = prompt_text(
        "venue.type",
        venue.get("type", ""),
        suggestion="conference",
        hint="conference / journal / workshop / internal",
    )
    venue["template_type"] = prompt_text(
        "venue.template_type",
        venue.get("template_type", ""),
        suggestion="LaTeX",
        hint="LaTeX / Word / portal-only",
    )
    venue["review_mode"] = prompt_text(
        "venue.review_mode",
        venue.get("review_mode", ""),
        suggestion=default_review_mode,
        hint="double-blind / single-blind / open",
    )
    venue["main_page_limit"] = prompt_text(
        "venue.main_page_limit",
        venue.get("main_page_limit", ""),
        hint="example: 8 pages excluding references",
    )
    venue["supplementary_policy"] = prompt_text(
        "venue.supplementary_policy",
        venue.get("supplementary_policy", ""),
        hint="example: allowed, anonymous PDF only",
    )
    venue["abstract_word_limit"] = prompt_text(
        "venue.abstract_word_limit",
        venue.get("abstract_word_limit", ""),
        hint="example: 150",
    )
    venue["keyword_limit"] = prompt_text(
        "venue.keyword_limit",
        venue.get("keyword_limit", ""),
        hint="example: 5",
    )
    venue["track_or_subject_area"] = prompt_text(
        "venue.track_or_subject_area",
        venue.get("track_or_subject_area", ""),
        hint="optional; leave blank if venue has no track field",
    )

    if "blind" in venue["review_mode"].lower():
        print("\n[Blind-review policy]")
        venue["repository_link_allowed"] = prompt_bool(
            "venue.repository_link_allowed",
            venue.get("repository_link_allowed"),
            hint="yes/no",
        )
        venue["supplementary_anonymity_required"] = prompt_bool(
            "venue.supplementary_anonymity_required",
            venue.get("supplementary_anonymity_required"),
            suggestion=True,
            hint="yes/no",
        )

    print("\n[Author metadata]")
    authors["author_names"] = prompt_list(
        "authors.author_names",
        list(authors.get("author_names", [])),
        separator=",",
        hint='comma-separated, e.g. Author One, Author Two',
    )
    authors["affiliations"] = prompt_list(
        "authors.affiliations",
        list(authors.get("affiliations", [])),
        separator=";",
        hint='semicolon-separated, e.g. Affiliation A; Affiliation B',
    )
    authors["corresponding_author_name"] = prompt_text(
        "authors.corresponding_author_name",
        authors.get("corresponding_author_name", ""),
    )
    authors["corresponding_author_email"] = prompt_text(
        "authors.corresponding_author_email",
        authors.get("corresponding_author_email", ""),
    )

    print("\n[Release policy]")
    release["submission_has_anonymized_repo"] = prompt_bool(
        "release_policy.submission_has_anonymized_repo",
        release.get("submission_has_anonymized_repo"),
        suggestion=True if "blind" in venue["review_mode"].lower() else False,
        hint="yes/no",
    )
    if release["submission_has_anonymized_repo"] is True:
        release["repo_url"] = prompt_text(
            "release_policy.repo_url",
            release.get("repo_url", ""),
            hint="anonymous repo URL if allowed",
        )
    release["code_release_timing"] = prompt_text(
        "release_policy.code_release_timing",
        release.get("code_release_timing", ""),
        suggestion="private during review, public at camera-ready",
    )

    print("\n[Portal selection]")
    portal["chosen_abstract_variant"] = prompt_text(
        "portal_selection.chosen_abstract_variant",
        portal.get("chosen_abstract_variant", ""),
        suggestion="150-word",
        hint="100-word / 150-word / 250-word / long",
    )
    portal["chosen_keyword_set"] = prompt_text(
        "portal_selection.chosen_keyword_set",
        portal.get("chosen_keyword_set", ""),
        suggestion="primary",
        hint="primary / extended",
    )
    if not is_empty(venue.get("track_or_subject_area", "")):
        portal["chosen_track"] = prompt_text(
            "portal_selection.chosen_track",
            portal.get("chosen_track", ""),
            suggestion=str(venue["track_or_subject_area"]),
        )

    input_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("\nSaved updated intake JSON.")
    print(f"Path: {input_path}")
    print("Next:")
    print("  bash /Users/seoki/Desktop/research/examples/run_submission_intake_pipeline_61day.sh")


if __name__ == "__main__":
    main()
