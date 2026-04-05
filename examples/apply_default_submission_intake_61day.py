#!/usr/bin/env python3
"""Apply safe default assumptions to 61day submission intake JSON."""

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
        help="Path to intake JSON to update in place.",
    )
    return parser.parse_args()


def get_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key, "")
    if isinstance(value, str):
        return value
    return ""


def ensure_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if isinstance(value, dict):
        return value
    value = {}
    data[key] = value
    return value


def apply_defaults(data: dict[str, Any]) -> None:
    venue = ensure_dict(data, "venue")
    release = ensure_dict(data, "release_policy")
    portal = ensure_dict(data, "portal_selection")
    defaults = ensure_dict(data, "recommended_defaults")

    data["submission_mode"] = "blind"

    # Venue defaults are intentionally "working assumptions", not final venue facts.
    venue["name"] = "Applied Conference Default"
    venue["type"] = "conference"
    venue["round_or_deadline"] = "rehearsal default"
    venue["template_type"] = "LaTeX"
    venue["review_mode"] = "double-blind"
    venue["main_page_limit"] = "8 pages plus references"
    venue["references_excluded_from_limit"] = True
    venue["appendix_policy"] = "limited"
    venue["supplementary_policy"] = "allowed, separate upload"
    venue["abstract_word_limit"] = "250"
    venue["keyword_limit"] = "5"
    venue["track_or_subject_area"] = "maritime AI / decision support"
    venue["ethics_field_required"] = True
    venue["data_code_field_required"] = True
    venue["repository_link_allowed"] = False
    venue["supplementary_anonymity_required"] = True
    venue["figure_formats_allowed"] = ["PDF", "PNG"]
    venue["pdf_size_limit_mb"] = "25"
    venue["font_embedding_required"] = True
    venue["camera_ready_required"] = True

    # Keep these as tri-state unknown to avoid accidental false declarations.
    venue["author_contribution_required"] = venue.get("author_contribution_required")
    venue["funding_statement_required"] = venue.get("funding_statement_required")
    venue["conflict_statement_required"] = venue.get("conflict_statement_required")

    # Release policy defaults avoid forcing repo URL when blind policy disallows links.
    release["submission_has_anonymized_repo"] = False
    release["repo_url"] = ""
    release["code_release_timing"] = "private during review, public at camera-ready"
    release["data_availability_final_text"] = get_text(defaults, "data_availability")
    release["code_availability_final_text"] = get_text(defaults, "code_availability")

    # Portal selections are the minimal choices required by validator.
    portal["chosen_abstract_variant"] = "250-word"
    portal["chosen_keyword_set"] = "primary"
    portal["chosen_track"] = venue["track_or_subject_area"]


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)

    with input_path.open("r", encoding="utf-8") as handle:
        data: dict[str, Any] = json.load(handle)

    apply_defaults(data)

    input_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Default intake assumptions applied: {input_path}")
    print("Next:")
    print("  bash /Users/seoki/Desktop/research/examples/run_submission_hard_gate_61day.sh")


if __name__ == "__main__":
    main()
