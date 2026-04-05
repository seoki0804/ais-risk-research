#!/usr/bin/env python3
"""Run strict advisory audit on submission metadata text fields."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


DEFAULT_ROOT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13"
)
DEFAULT_INPUT = DEFAULT_ROOT / "submission_portal_metadata_filled_61day.json"
DEFAULT_OUTPUT = DEFAULT_ROOT / "submission_metadata_strict_audit_61day.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def text_value(data: dict, key: str) -> str:
    value = data.get(key, "")
    return str(value) if value is not None else ""


def build_report(
    generated_date: str,
    input_path: Path,
    output_path: Path,
    status: str,
    warnings: list[str],
) -> str:
    lines = [
        "# Submission Metadata Strict Audit 61day",
        "",
        f"- Generated: `{generated_date}`",
        f"- Input: `{input_path}`",
        f"- Output: `{output_path}`",
        f"- Status: `{status}`",
        "",
        "## Advisory Findings",
    ]

    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Interpretation",
            "- `PASS` means no obvious placeholder/provisional metadata text was detected.",
            "- `ATTENTION` means at least one metadata field still looks provisional and should be reviewed before final submit.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    warnings: list[str] = []

    funding = text_value(data, "funding_statement")
    conflict = text_value(data, "conflict_statement")
    contribution = text_value(data, "author_contribution_statement")
    acknowledgements = text_value(data, "acknowledgements")
    repo_url = text_value(data, "repo_url")
    code_timing = text_value(data, "code_release_timing")
    anon_repo = data.get("submission_has_anonymized_repo")

    if "No external funding statement has been provided" in funding:
        warnings.append("Funding statement still uses provisional placeholder text.")
    if "currently available in the workspace" in conflict:
        warnings.append("Conflict statement still uses provisional workspace placeholder wording.")
    if "should be filled in according to the actual author list" in contribution:
        warnings.append("Author contribution statement still uses guidance placeholder wording.")
    if "Acknowledgements are not fixed" in acknowledgements:
        warnings.append("Acknowledgements still use provisional placeholder wording.")
    if anon_repo is False and not repo_url.strip():
        warnings.append("Repository URL is empty while anonymized repo is set to false.")
    if not code_timing.strip():
        warnings.append("Code release timing is empty.")

    status = "PASS" if not warnings else "ATTENTION"
    report = build_report(
        generated_date=dt.date.today().isoformat(),
        input_path=input_path,
        output_path=output_path,
        status=status,
        warnings=warnings,
    )
    output_path.write_text(report, encoding="utf-8")

    print(f"Status: {status}")
    print(f"Warning count: {len(warnings)}")
    print(f"Report: {output_path}")


if __name__ == "__main__":
    main()
