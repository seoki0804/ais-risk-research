#!/usr/bin/env python3
"""Assess final submission hard-gate readiness for the 61day package."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


DEFAULT_ROOT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13"
)
DEFAULT_OUTPUT = DEFAULT_ROOT / "submission_hard_gate_61day.md"
DEFAULT_PACKET = DEFAULT_ROOT / "venue_packets" / "applied_conf_default_blind_61day"
DEFAULT_REAL_VALUE_GATE = DEFAULT_ROOT / "submission_metadata_real_value_gate_61day.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--packet-dir", default=str(DEFAULT_PACKET))
    parser.add_argument("--real-value-gate", default=str(DEFAULT_REAL_VALUE_GATE))
    parser.add_argument(
        "--allow-provisional-values",
        action="store_true",
        help="Allow hard-gate PASS even when real-value gate is HOLD.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def parse_status_line(text: str) -> str:
    match = re.search(r"- Status:\s*`([^`]+)`", text)
    return match.group(1).strip() if match else "UNKNOWN"


def parse_count_line(text: str, label: str) -> int:
    match = re.search(rf"- {re.escape(label)}:\s*`(\d+)`", text)
    return int(match.group(1)) if match else 999


def parse_score(text: str, label: str) -> int:
    match = re.search(rf"- {re.escape(label)}:\s*`(\d+)%`", text)
    return int(match.group(1)) if match else 0


def parse_real_value_gate(path: Path) -> tuple[str, int]:
    text = read_text(path)
    status_match = re.search(r"- Status:\s*`([^`]+)`", text)
    blocker_match = re.search(r"- Blocker count:\s*`(\d+)`", text)
    status = status_match.group(1).strip() if status_match else "UNKNOWN"
    if blocker_match:
        blockers = int(blocker_match.group(1))
    else:
        blockers = 0 if status == "PASS" else 1
    return status, blockers


def parse_missing_sections(validation_text: str) -> dict[str, list[str]]:
    sections = {
        "Venue Policy": [],
        "Author Metadata": [],
        "Disclosures": [],
        "Release Policy": [],
        "Portal Selection": [],
    }
    current: str | None = None

    for raw_line in validation_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            heading = line[3:].strip()
            current = heading if heading in sections else None
            continue
        if not current:
            continue
        if not line.startswith("- "):
            continue
        item = line[2:].strip()
        if item and item != "none":
            sections[current].append(item)

    return sections


def build_report(
    output: Path,
    date_str: str,
    intake_status: str,
    intake_missing: int,
    claim_status: str,
    claim_forbidden_hits: int,
    packet_validation_status: str,
    packet_readiness_status: str,
    paper_score: int,
    intake_score: int,
    publication_score: int,
    real_value_status: str,
    real_value_blockers: int,
    require_real_values: bool,
    intake_missing_by_section: dict[str, list[str]],
    rule_results: list[tuple[str, bool, str]],
    blockers: list[str],
    todo_items: list[str],
) -> str:
    final_status = "PASS" if not blockers else "BLOCKED"
    passed_rules = sum(1 for _, passed, _ in rule_results if passed)
    lines = [
        "# Submission Hard Gate 61day",
        "",
        f"- Generated: `{date_str}`",
        f"- Output: `{output}`",
        f"- Final status: `{final_status}`",
        f"- Gate checks passed: `{passed_rules}/{len(rule_results)}`",
        "",
        "## Inputs",
        f"- Intake status: `{intake_status}`",
        f"- Intake missing fields: `{intake_missing}`",
        f"- Claim consistency status: `{claim_status}`",
        f"- Claim forbidden hits: `{claim_forbidden_hits}`",
        f"- Canonical packet validation: `{packet_validation_status}`",
        f"- Canonical packet readiness: `{packet_readiness_status}`",
        f"- Paper completeness score: `{paper_score}%`",
        f"- Submission intake readiness score: `{intake_score}%`",
        f"- Publication readiness score: `{publication_score}%`",
        f"- Real-value gate status: `{real_value_status}`",
        f"- Real-value gate blockers: `{real_value_blockers}`",
        f"- Strict real-value requirement: `{require_real_values}`",
        "",
        "## Intake Missing Detail",
    ]

    has_missing_detail = False
    for section_name, items in intake_missing_by_section.items():
        if items:
            has_missing_detail = True
            lines.append(f"- {section_name}: `{len(items)}`")
    if not has_missing_detail:
        lines.append("- none")

    lines.extend(
        [
            "",
        "## Gate Rules",
        "- Rule 1: Intake status must be `READY` with missing fields `0`.",
        "- Rule 2: Claim consistency must be `PASS` with forbidden hits `0`.",
        "- Rule 3: Canonical packet validation must be `PASS`.",
        "- Rule 4: Canonical packet readiness must be `READY`.",
        "- Rule 5: Publication readiness score must be at least `95%`.",
        "- Rule 6: Real-value gate must be `PASS` with blocker count `0` when strict mode is enabled.",
        "",
        "## Rule Outcomes",
        ]
    )

    for idx, (rule_text, passed, observed) in enumerate(rule_results, start=1):
        status = "PASS" if passed else "FAIL"
        lines.append(f"- Rule {idx} `{status}`: {rule_text} (observed: `{observed}`)")

    lines.extend(["", "## Blockers"])

    if blockers:
        for blocker in blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- none")

    lines.extend(["", "## To Do (Hard Gate Recovery)"])

    if todo_items:
        for item in todo_items:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Interpretation",
            "- `PASS` means the package is operationally ready for portal submission under the current lane.",
            "- `BLOCKED` means at least one hard pre-submission requirement is still unmet.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    output = Path(args.output)
    packet_dir = Path(args.packet_dir)
    real_value_gate_path = Path(args.real_value_gate)
    require_real_values = not args.allow_provisional_values

    intake_text = read_text(root / "submission_intake_validation_61day.md")
    claim_text = read_text(root / "claim_consistency_audit_61day.md")
    score_text = read_text(root / "submission_completion_scorecard_61day.md")
    packet_validation_text = read_text(packet_dir / "VENUE_PACKET_VALIDATION.md")
    packet_readiness_text = read_text(packet_dir / "VENUE_PACKET_READINESS.md")

    intake_status = parse_status_line(intake_text)
    intake_missing = parse_count_line(intake_text, "Missing field count")
    intake_missing_by_section = parse_missing_sections(intake_text)
    claim_status = parse_status_line(claim_text)
    claim_forbidden_hits = parse_count_line(claim_text, "Forbidden hits")
    packet_validation_status = parse_status_line(packet_validation_text)
    packet_readiness_status = parse_status_line(packet_readiness_text)
    paper_score = parse_score(score_text, "Paper completeness score")
    intake_score = parse_score(score_text, "Submission intake readiness score")
    publication_score = parse_score(score_text, "Publication readiness score")
    real_value_status, real_value_blockers = parse_real_value_gate(real_value_gate_path)

    blockers: list[str] = []
    todo_items: list[str] = []
    rule_results: list[tuple[str, bool, str]] = []

    rule1_pass = intake_status == "READY" and intake_missing == 0
    rule_results.append(
        (
            "Intake status must be READY with missing fields 0",
            rule1_pass,
            f"status={intake_status}, missing={intake_missing}",
        )
    )
    if not rule1_pass:
        blockers.append(f"intake not ready (`status={intake_status}`, missing={intake_missing})")
        nonempty_sections = [
            section_name
            for section_name, items in intake_missing_by_section.items()
            if items
        ]
        if nonempty_sections:
            joined = ", ".join(nonempty_sections)
            todo_items.append(
                "Fill missing intake fields in `submission_intake_template_61day.json` "
                f"(sections: {joined})."
            )
        else:
            todo_items.append(
                "Fill missing intake fields in `submission_intake_template_61day.json`."
            )
        if intake_missing_by_section["Author Metadata"]:
            todo_items.append(
                "Complete author metadata (names, affiliations, corresponding author name/email)."
            )
        if intake_missing_by_section["Venue Policy"]:
            todo_items.append(
                "Complete venue policy fields (name/type/review mode/page/supplementary/abstract/keyword)."
            )
        if intake_missing_by_section["Release Policy"]:
            todo_items.append(
                "Complete release policy fields (anonymized repo choice and code release timing)."
            )
        if intake_missing_by_section["Portal Selection"]:
            todo_items.append(
                "Complete portal selection fields (abstract variant and keyword set)."
            )
        if intake_missing_by_section["Disclosures"]:
            todo_items.append(
                "Complete disclosure statements required by current venue flags."
            )
        todo_items.append(
            "Run `bash /Users/seoki/Desktop/research/examples/run_submission_intake_interactive_61day.sh` "
            "to close intake gaps and regenerate portal handoff files."
        )

    rule2_pass = claim_status == "PASS" and claim_forbidden_hits == 0
    rule_results.append(
        (
            "Claim consistency must be PASS with forbidden hits 0",
            rule2_pass,
            f"status={claim_status}, forbidden_hits={claim_forbidden_hits}",
        )
    )
    if not rule2_pass:
        blockers.append(
            f"claim consistency not clean (`status={claim_status}`, forbidden_hits={claim_forbidden_hits})"
        )
        todo_items.append(
            "Fix claim-consistency findings in paper/rebuttal sources, then rerun "
            "`bash /Users/seoki/Desktop/research/examples/run_completion_scorecard_61day.sh`."
        )

    rule3_pass = packet_validation_status == "PASS"
    rule_results.append(
        (
            "Canonical packet validation must be PASS",
            rule3_pass,
            packet_validation_status,
        )
    )
    if not rule3_pass:
        blockers.append(f"canonical packet validation not PASS (`{packet_validation_status}`)")
        todo_items.append(
            "Repair missing packet assets in canonical blind packet and rerun "
            "`bash /Users/seoki/Desktop/research/examples/run_canonical_preflight_61day.sh`."
        )

    rule4_pass = packet_readiness_status == "READY"
    rule_results.append(
        (
            "Canonical packet readiness must be READY",
            rule4_pass,
            packet_readiness_status,
        )
    )
    if not rule4_pass:
        blockers.append(f"canonical packet readiness not READY (`{packet_readiness_status}`)")
        todo_items.append(
            "Resolve unresolved packet notes fields and rerun readiness checks for the canonical packet."
        )

    rule5_pass = publication_score >= 95
    rule_results.append(
        (
            "Publication readiness score must be at least 95%",
            rule5_pass,
            f"{publication_score}%",
        )
    )
    if not rule5_pass:
        blockers.append(f"publication readiness score below threshold (`{publication_score}% < 95%`)")
        todo_items.append(
            "Raise publication readiness to >=95 by resolving intake blockers and refreshing "
            "`submission_completion_scorecard_61day.md`."
        )

    if require_real_values:
        rule6_pass = real_value_status == "PASS" and real_value_blockers == 0
        observed = f"status={real_value_status}, blockers={real_value_blockers}, strict={require_real_values}"
    else:
        rule6_pass = True
        observed = f"status={real_value_status}, blockers={real_value_blockers}, strict={require_real_values}"
    rule_results.append(
        (
            "Real-value gate must be PASS with blocker count 0 when strict mode is enabled",
            rule6_pass,
            observed,
        )
    )
    if not rule6_pass:
        blockers.append(
            f"real-value gate is not clean (`status={real_value_status}`, blockers={real_value_blockers})"
        )
        todo_items.append(
            "Set actual venue values and run strict closure: "
            "`bash /Users/seoki/Desktop/research/examples/run_strict_real_value_closure_61day.sh "
            "<venue_name> <venue_round_or_deadline>`."
        )
        todo_items.append(
            "Confirm `submission_metadata_real_value_gate_61day.md` shows `Status: PASS` and `Blocker count: 0`."
        )

    if blockers:
        todo_items.append(
            "After fixes, rerun `bash /Users/seoki/Desktop/research/examples/run_submission_hard_gate_61day.sh` "
            "and confirm `submission_hard_gate_61day.md` final status is `PASS`."
        )

    date_str = dt.date.today().isoformat()
    report = build_report(
        output=output,
        date_str=date_str,
        intake_status=intake_status,
        intake_missing=intake_missing,
        claim_status=claim_status,
        claim_forbidden_hits=claim_forbidden_hits,
        packet_validation_status=packet_validation_status,
        packet_readiness_status=packet_readiness_status,
        paper_score=paper_score,
        intake_score=intake_score,
        publication_score=publication_score,
        real_value_status=real_value_status,
        real_value_blockers=real_value_blockers,
        require_real_values=require_real_values,
        intake_missing_by_section=intake_missing_by_section,
        rule_results=rule_results,
        blockers=blockers,
        todo_items=todo_items,
    )
    output.write_text(report, encoding="utf-8")

    final_status = "PASS" if not blockers else "BLOCKED"
    print(f"Final status: {final_status}")
    print(f"Blocker count: {len(blockers)}")
    print(f"Report: {output}")
    if blockers:
        for blocker in blockers:
            print(f"- {blocker}")


if __name__ == "__main__":
    main()
