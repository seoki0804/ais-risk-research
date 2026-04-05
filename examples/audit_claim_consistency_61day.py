#!/usr/bin/env python3
"""Audit claim consistency for the 61day manuscript/rebuttal package."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


DEFAULT_ROOT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13"
)
DEFAULT_OUTPUT = DEFAULT_ROOT / "claim_consistency_audit_61day.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def find_pattern(path: Path, pattern: str) -> bool:
    text = read_text(path)
    return re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) is not None


def count_forbidden_hits(root: Path, pattern: str) -> int:
    total = 0
    for md_path in root.rglob("*.md"):
        text = read_text(md_path)
        total += len(re.findall(pattern, text, flags=re.IGNORECASE))
    return total


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    output = Path(args.output)

    paper = root / "paper_conference_8page_final_pass_61day_en.md"
    rebuttal_short = root / "reviewer_rebuttal_short_pack_61day_ko_en.md"
    rebuttal_section = root / "reviewer_rebuttal_section_pack_61day_ko_en.md"

    required_checks: list[tuple[str, Path, str]] = [
        ("Scope anchor in paper", paper, r"AIS-only decision support"),
        ("Main label anchor in paper", paper, r"0\.5 nm"),
        ("Relaxed label mention in paper", paper, r"1\.6 nm"),
        (
            "Point estimate + interval in paper",
            paper,
            r"(point estimate(?:s)?(?:\s+plus|\s+\+)?\s+interval|point estimates?\s+with\s+row-bootstrap[^.\n]*intervals?)",
        ),
        ("Descriptive uncertainty wording in paper", paper, r"descriptive uncertainty (?:layer|band)"),
        (
            "Appendix-only coverage framing in paper",
            paper,
            r"(appendix(?:-level)?[^.\n]*coverage|coverage[^.\n]*appendix[^.\n]*check)",
        ),
        ("Main label anchor in rebuttal short", rebuttal_short, r"formal manuscript reporting[^.\n]*0\.5 nm"),
        (
            "Relaxed label appendix framing in rebuttal short",
            rebuttal_short,
            r"1\.6 nm[^.\n]*appendix-level coverage check",
        ),
        ("Point estimate + interval in rebuttal short", rebuttal_short, r"point estimate(?:\s+plus|\s+\+)?\s+interval"),
        ("Row-bootstrap interval in rebuttal section", rebuttal_section, r"row-bootstrap\s+`?95%`?\s+interval"),
    ]

    forbidden_patterns: list[tuple[str, str]] = [
        ("stale_cleaned_input_claim_nola", r"materially improves tabular NOLA performance"),
        ("stale_cleaned_input_claim_seattle_nola", r"improves Seattle/NOLA"),
    ]

    passed = 0
    failed_rows: list[str] = []
    passed_rows: list[str] = []
    for name, path, pattern in required_checks:
        ok = find_pattern(path, pattern)
        if ok:
            passed += 1
            passed_rows.append(f"- PASS: {name} (`{path.name}`)")
        else:
            failed_rows.append(f"- FAIL: {name} (`{path.name}`)")

    forbidden_hits: list[str] = []
    total_forbidden = 0
    for name, pattern in forbidden_patterns:
        hits = count_forbidden_hits(root, pattern)
        total_forbidden += hits
        forbidden_hits.append(f"- {name}: `{hits}`")

    required_total = len(required_checks)
    status = "PASS" if passed == required_total and total_forbidden == 0 else "FAIL"
    date_str = dt.date.today().isoformat()

    lines = [
        "# Claim Consistency Audit 61day",
        "",
        f"- Generated: `{date_str}`",
        f"- Root: `{root}`",
        f"- Output: `{output}`",
        f"- Status: `{status}`",
        f"- Required checks passed: `{passed}/{required_total}`",
        f"- Forbidden hits: `{total_forbidden}`",
        "",
        "## Required Checks",
    ]
    lines.extend(passed_rows)
    if failed_rows:
        lines.append("")
        lines.extend(failed_rows)

    lines.extend(
        [
            "",
            "## Forbidden Pattern Hits",
        ]
    )
    lines.extend(forbidden_hits)
    lines.extend(
        [
            "",
            "## Interpretation",
            "- Required checks ensure the current paper/rebuttal spine is preserved (0.5 nm main, 1.6 nm appendix-only, point estimate + interval, descriptive uncertainty).",
            "- Forbidden checks guard against reintroducing stale cleaned-input improvement claims.",
        ]
    )

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Status: {status}")
    print(f"Required checks passed: {passed}/{required_total}")
    print(f"Forbidden hits: {total_forbidden}")
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
