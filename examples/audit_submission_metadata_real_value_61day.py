#!/usr/bin/env python3
"""Audit real-value completeness for venue-bound submission metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13"
)
DEFAULT_INPUT = DEFAULT_ROOT / "submission_portal_metadata_filled_61day.json"
DEFAULT_OUTPUT = DEFAULT_ROOT / "submission_metadata_real_value_gate_61day.md"
DEFAULT_TEX_PATHS = [
    DEFAULT_ROOT / "paper_conference_8page_asset_locked_61day.tex",
    DEFAULT_ROOT
    / "venue_packets/applied_conf_default_camera-ready_61day/manuscript_bundle_61day/"
    "paper_camera-ready_bound_61day.tex",
]

GENERIC_VALUE_PATTERN = re.compile(
    r"\b(default|rehearsal|sample|placeholder|tbd|todo|unknown|pending)\b",
    flags=re.IGNORECASE,
)
PLACEHOLDER_PHRASES = (
    "placeholder",
    "to be filled",
    "to be inserted",
    "not fixed",
    "pending",
    "tbd",
    "unknown",
)
TEX_PLACEHOLDER_PATTERNS = (
    (r"TODO\(venue\)", "contains unresolved `TODO(venue)` markers"),
    (
        r"should be inserted during the venue-specific final pass",
        "contains venue-final-pass placeholder sentences",
    ),
    (
        r"Author Metadata Pending Final Intake",
        "contains pending author metadata front matter",
    ),
)


def find_line_hits(text: str, pattern: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if re.search(pattern, line):
            hits.append((index, line.strip()))
    return hits


def summarize_line_hits(hits: list[tuple[int, str]], limit: int = 5) -> str:
    if not hits:
        return "none"
    sampled = hits[:limit]
    labels = ", ".join(f"L{line}" for line, _ in sampled)
    if len(hits) > limit:
        labels += f", +{len(hits) - limit} more"
    return labels


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--tex",
        action="append",
        dest="tex_paths",
        help="TeX files to audit for unresolved venue placeholders. Repeatable.",
    )
    return parser.parse_args()


def text_value(data: dict[str, Any], key: str) -> str:
    value = data.get(key, "")
    return str(value) if value is not None else ""


def is_generic_value(value: str) -> bool:
    return bool(GENERIC_VALUE_PATTERN.search(value.strip()))


def has_placeholder_phrase(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in PLACEHOLDER_PHRASES)


def looks_like_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value.strip()))


def build_report(
    generated_date: str,
    input_path: Path,
    output_path: Path,
    tex_paths: list[Path],
    status: str,
    blockers: list[str],
    todos: list[str],
) -> str:
    lines = [
        "# Submission Metadata Real-Value Gate 61day",
        "",
        f"- Generated: `{generated_date}`",
        f"- Input: `{input_path}`",
        f"- Output: `{output_path}`",
        f"- Status: `{status}`",
        f"- Blocker count: `{len(blockers)}`",
        "",
        "## TeX Inputs",
    ]
    if tex_paths:
        for path in tex_paths:
            lines.append(f"- `{path}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Real-Value Blockers"])
    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(["", "## To Do"])
    if todos:
        for item in todos:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Interpretation",
            "- `PASS` means venue-bound metadata and manuscript placeholders are operationally clean for final real-value handoff.",
            "- `HOLD` means at least one value is still generic/provisional or unresolved venue placeholders remain in TeX.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    tex_paths = [Path(p) for p in args.tex_paths] if args.tex_paths else DEFAULT_TEX_PATHS

    with input_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    blockers: list[str] = []
    todos: list[str] = []

    venue_name = text_value(data, "venue_name")
    venue_round = text_value(data, "venue_round_or_deadline")
    corresponding_name = text_value(data, "corresponding_author_name")
    corresponding_email = text_value(data, "corresponding_author_email")
    funding = text_value(data, "funding_statement")
    conflict = text_value(data, "conflict_statement")
    contribution = text_value(data, "author_contribution_statement")
    acknowledgements = text_value(data, "acknowledgements")
    repo_url = text_value(data, "repo_url")
    repo_allowed = bool(data.get("repository_link_allowed"))
    has_anon_repo = data.get("submission_has_anonymized_repo")

    if not venue_name.strip() or is_generic_value(venue_name):
        blockers.append(
            f"venue_name is still generic/provisional (`{venue_name or 'EMPTY'}`)."
        )
        todos.append("Replace `venue_name` with the actual target venue.")

    if not venue_round.strip() or is_generic_value(venue_round):
        blockers.append(
            "venue_round_or_deadline is still generic/provisional "
            f"(`{venue_round or 'EMPTY'}`)."
        )
        todos.append("Set the actual submission round/deadline value.")

    if not corresponding_name.strip():
        blockers.append("corresponding_author_name is empty.")
        todos.append("Fill `corresponding_author_name` with the final contact author.")

    if not looks_like_email(corresponding_email):
        blockers.append(
            "corresponding_author_email is missing or malformed "
            f"(`{corresponding_email or 'EMPTY'}`)."
        )
        todos.append("Set a valid corresponding author email.")

    for label, value in (
        ("funding_statement", funding),
        ("conflict_statement", conflict),
        ("author_contribution_statement", contribution),
    ):
        if not value.strip():
            blockers.append(f"{label} is empty.")
            todos.append(f"Fill `{label}` with venue-ready final text.")
            continue
        if has_placeholder_phrase(value):
            blockers.append(f"{label} still contains provisional phrasing.")
            todos.append(f"Replace provisional wording in `{label}` with final text.")

    if not acknowledgements.strip():
        blockers.append("acknowledgements is empty.")
        todos.append("Fill `acknowledgements` with final venue-ready text or explicit `None.`")
    elif has_placeholder_phrase(acknowledgements) and acknowledgements.strip().lower() != "none.":
        blockers.append("acknowledgements still contains provisional phrasing.")
        todos.append("Replace provisional acknowledgements wording with final text.")

    repo_url_is_na = repo_url.strip().lower().startswith("n/a")
    if repo_allowed and has_anon_repo is False and (not repo_url.strip() or repo_url_is_na):
        blockers.append(
            "repository links are allowed and anonymized repo is false, but repo_url is not a real link."
        )
        todos.append("Provide a real repository URL for camera-ready/public submission.")

    for tex_path in tex_paths:
        if not tex_path.exists():
            blockers.append(f"TeX file missing for gate check: `{tex_path}`.")
            todos.append(f"Regenerate the manuscript bundle that should contain `{tex_path.name}`.")
            continue

        text = tex_path.read_text(encoding="utf-8")
        for pattern, message in TEX_PLACEHOLDER_PATTERNS:
            line_hits = find_line_hits(text, pattern)
            count = len(line_hits)
            if count > 0:
                line_summary = summarize_line_hits(line_hits)
                blockers.append(
                    f"`{tex_path}` {message} (count={count}, lines={line_summary})."
                )
                todos.append(
                    f"Resolve venue placeholder text in `{tex_path.name}` and re-run this gate."
                )

    if not blockers:
        todos.append("No real-value blocker detected.")

    dedup_todos = list(dict.fromkeys(todos))
    status = "PASS" if not blockers else "HOLD"
    report = build_report(
        generated_date=dt.date.today().isoformat(),
        input_path=input_path,
        output_path=output_path,
        tex_paths=tex_paths,
        status=status,
        blockers=blockers,
        todos=dedup_todos,
    )
    output_path.write_text(report, encoding="utf-8")

    print(f"Status: {status}")
    print(f"Blocker count: {len(blockers)}")
    print(f"Report: {output_path}")
    if blockers:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
