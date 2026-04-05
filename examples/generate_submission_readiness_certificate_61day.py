#!/usr/bin/env python3
"""Generate a submission readiness certificate from canonical 61day outputs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
from pathlib import Path


DEFAULT_ROOT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13"
)
DEFAULT_OUTPUT = DEFAULT_ROOT / "submission_readiness_certificate_61day.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def find_text(pattern: str, text: str, default: str = "UNKNOWN") -> str:
    match = re.search(pattern, text)
    if not match:
        return default
    return match.group(1).strip()


def parse_int(text: str, pattern: str, default: int = -1) -> int:
    match = re.search(pattern, text)
    if not match:
        return default
    return int(match.group(1))


def parse_real_value_gate(path: Path) -> tuple[str, int]:
    text = read_text(path)
    status = find_text(r"- Status:\s*`([^`]+)`", text, default="UNKNOWN")
    blockers = parse_int(text, r"- Blocker count:\s*`(\d+)`", default=-1)
    if blockers < 0:
        blockers = 0 if status == "PASS" else 1
    return status, blockers


def sha256(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def build_report(
    generated_at: str,
    output_path: Path,
    intake_status: str,
    intake_missing: int,
    claim_status: str,
    claim_forbidden_hits: int,
    score_paper: int,
    score_intake: int,
    score_publication: int,
    hard_gate_status: str,
    hard_gate_checks: str,
    real_value_status: str,
    real_value_blockers: int,
    checks: list[tuple[str, bool, str]],
    tracked_files: list[Path],
) -> str:
    passed = all(p for _, p, _ in checks)
    cert_status = "VALID" if passed else "INVALID"
    lines = [
        "# Submission Readiness Certificate 61day",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Output: `{output_path}`",
        f"- Certificate status: `{cert_status}`",
        "",
        "## Canonical Snapshot",
        f"- Intake validation: `{intake_status}` (missing={intake_missing})",
        f"- Claim consistency: `{claim_status}` (forbidden_hits={claim_forbidden_hits})",
        f"- Completion scores: paper `{score_paper}%`, intake `{score_intake}%`, publication `{score_publication}%`",
        f"- Hard gate: `{hard_gate_status}` (checks={hard_gate_checks})",
        f"- Real-value gate: `{real_value_status}` (blockers={real_value_blockers})",
        "",
        "## Certificate Checks",
    ]
    for label, ok, observed in checks:
        lines.append(f"- {'PASS' if ok else 'FAIL'}: {label} (observed: `{observed}`)")

    lines.extend(["", "## File Hashes (SHA256)"])
    for path in tracked_files:
        lines.append(f"- `{path.name}`: `{sha256(path)}`")

    lines.extend(
        [
            "",
            "## Interpretation",
            "- `VALID` means all canonical pre-submit checks currently pass.",
            "- `INVALID` means at least one canonical check failed and submission should be paused.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    output = Path(args.output)

    intake_path = root / "submission_intake_validation_61day.md"
    claim_path = root / "claim_consistency_audit_61day.md"
    score_path = root / "submission_completion_scorecard_61day.md"
    hard_gate_path = root / "submission_hard_gate_61day.md"
    real_value_gate_path = root / "submission_metadata_real_value_gate_61day.md"
    intake_json_path = root / "submission_intake_template_61day.json"
    handoff_path = root / "submission_intake_handoff_61day.md"
    copy_path = root / "submission_portal_copy_paste_filled_61day.md"

    intake_text = read_text(intake_path)
    claim_text = read_text(claim_path)
    score_text = read_text(score_path)
    hard_gate_text = read_text(hard_gate_path)

    intake_status = find_text(r"- Status:\s*`([^`]+)`", intake_text)
    intake_missing = parse_int(intake_text, r"- Missing field count:\s*`(\d+)`", default=999)

    claim_status = find_text(r"- Status:\s*`([^`]+)`", claim_text)
    claim_forbidden_hits = parse_int(claim_text, r"- Forbidden hits:\s*`(\d+)`", default=999)

    score_paper = parse_int(score_text, r"- Paper completeness score:\s*`(\d+)%`", default=-1)
    score_intake = parse_int(
        score_text, r"- Submission intake readiness score:\s*`(\d+)%`", default=-1
    )
    score_publication = parse_int(score_text, r"- Publication readiness score:\s*`(\d+)%`", default=-1)

    hard_gate_status = find_text(r"- Final status:\s*`([^`]+)`", hard_gate_text)
    hard_gate_checks = find_text(r"- Gate checks passed:\s*`([^`]+)`", hard_gate_text, default="UNKNOWN")
    real_value_status, real_value_blockers = parse_real_value_gate(real_value_gate_path)

    checks: list[tuple[str, bool, str]] = [
        ("Intake validation READY", intake_status == "READY" and intake_missing == 0, f"{intake_status}, missing={intake_missing}"),
        (
            "Claim consistency PASS with zero forbidden hits",
            claim_status == "PASS" and claim_forbidden_hits == 0,
            f"{claim_status}, forbidden_hits={claim_forbidden_hits}",
        ),
        (
            "Completion scorecard all 100%",
            score_paper == 100 and score_intake == 100 and score_publication == 100,
            f"paper={score_paper}, intake={score_intake}, publication={score_publication}",
        ),
        ("Hard gate PASS", hard_gate_status == "PASS", hard_gate_status),
        (
            "Real-value gate PASS with zero blockers",
            real_value_status == "PASS" and real_value_blockers == 0,
            f"{real_value_status}, blockers={real_value_blockers}",
        ),
    ]

    tracked_files = [
        intake_json_path,
        intake_path,
        handoff_path,
        copy_path,
        claim_path,
        real_value_gate_path,
        score_path,
        hard_gate_path,
    ]

    generated_at = dt.datetime.now().isoformat(timespec="seconds")
    report = build_report(
        generated_at=generated_at,
        output_path=output,
        intake_status=intake_status,
        intake_missing=intake_missing,
        claim_status=claim_status,
        claim_forbidden_hits=claim_forbidden_hits,
        score_paper=score_paper,
        score_intake=score_intake,
        score_publication=score_publication,
        hard_gate_status=hard_gate_status,
        hard_gate_checks=hard_gate_checks,
        real_value_status=real_value_status,
        real_value_blockers=real_value_blockers,
        checks=checks,
        tracked_files=tracked_files,
    )
    output.write_text(report, encoding="utf-8")

    cert_valid = all(ok for _, ok, _ in checks)
    print(f"Certificate status: {'VALID' if cert_valid else 'INVALID'}")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()
