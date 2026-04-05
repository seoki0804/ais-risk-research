#!/usr/bin/env python3
"""Build an objective completion scorecard for the 61day paper package."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


DEFAULT_ROOT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13"
)
DEFAULT_OUTPUT = DEFAULT_ROOT / "submission_completion_scorecard_61day.md"
DEFAULT_VALIDATION = DEFAULT_ROOT / "submission_intake_validation_61day.md"
DEFAULT_BLOCKER = DEFAULT_ROOT / "submission_blocker_sheet_61day.md"
DEFAULT_CONSISTENCY_AUDIT = DEFAULT_ROOT / "claim_consistency_audit_61day.md"
DEFAULT_REAL_VALUE_GATE = DEFAULT_ROOT / "submission_metadata_real_value_gate_61day.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--validation", default=str(DEFAULT_VALIDATION))
    parser.add_argument("--blocker", default=str(DEFAULT_BLOCKER))
    parser.add_argument("--consistency-audit", default=str(DEFAULT_CONSISTENCY_AUDIT))
    parser.add_argument("--real-value-gate", default=str(DEFAULT_REAL_VALUE_GATE))
    return parser.parse_args()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def parse_validation(path: Path) -> tuple[str, int]:
    text = read_text(path)
    status_match = re.search(r"- Status:\s*`([^`]+)`", text)
    missing_match = re.search(r"- Missing field count:\s*`(\d+)`", text)
    status = status_match.group(1).strip() if status_match else "UNKNOWN"
    missing = int(missing_match.group(1)) if missing_match else 999
    return status, missing


def contains_closure_signal(path: Path) -> bool:
    text = read_text(path)
    has_compile_closure = (
        "연구 내용, rebuttal, manuscript markdown, blind/source-kit/camera-ready generic TeX, PDF compile line은 모두 닫혔다."
        in text
    )
    has_blocker_closure = any(
        token in text
        for token in (
            "현재 남은 blocker는 연구가 아니라",
            "현재 hard blocker는 닫혔고",
            "현재 hard blocker는 없다",
        )
    )
    return has_compile_closure and has_blocker_closure


def exists_ratio(paths: list[Path]) -> tuple[int, int, float]:
    if not paths:
        return 0, 0, 0.0
    present = sum(1 for p in paths if p.exists())
    total = len(paths)
    ratio = present / total
    return present, total, ratio


def compile_clean_ratio(log_paths: list[Path]) -> tuple[int, int, float, list[str]]:
    present_logs = [p for p in log_paths if p.exists()]
    if not present_logs:
        return 0, 0, 0.0, ["No canonical log file found."]

    bad_tokens = ("warning:", "Underfull", "Overfull", "error:")
    clean = 0
    notes: list[str] = []
    for log_path in present_logs:
        text = read_text(log_path)
        bad = any(token in text for token in bad_tokens)
        if bad:
            notes.append(f"{log_path.name}: warnings/errors found")
        else:
            notes.append(f"{log_path.name}: clean")
            clean += 1
    ratio = clean / len(present_logs)
    return clean, len(present_logs), ratio, notes


def clamp(score: float) -> int:
    return int(round(max(0.0, min(100.0, score))))


def parse_consistency_audit(path: Path) -> tuple[str, int, int, int]:
    text = read_text(path)
    status_match = re.search(r"- Status:\s*`([^`]+)`", text)
    passed_match = re.search(r"- Required checks passed:\s*`(\d+)/(\d+)`", text)
    forbidden_match = re.search(r"- Forbidden hits:\s*`(\d+)`", text)

    status = status_match.group(1).strip() if status_match else "UNKNOWN"
    required_passed = int(passed_match.group(1)) if passed_match else 0
    required_total = int(passed_match.group(2)) if passed_match else 0
    forbidden_hits = int(forbidden_match.group(1)) if forbidden_match else 999
    return status, required_passed, required_total, forbidden_hits


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


def build_markdown(
    date_str: str,
    paper_score: int,
    intake_score: int,
    publication_score: int,
    validation_status: str,
    missing_fields: int,
    closure_signal: bool,
    doc_present: int,
    doc_total: int,
    artifact_present: int,
    artifact_total: int,
    clean_logs: int,
    total_logs: int,
    log_notes: list[str],
    consistency_status: str,
    consistency_passed: int,
    consistency_total: int,
    forbidden_hits: int,
    real_value_status: str,
    real_value_blockers: int,
    output_path: Path,
) -> str:
    lines = [
        "# Submission Completion Scorecard 61day",
        "",
        f"- Generated: `{date_str}`",
        f"- Output: `{output_path}`",
        "",
        "## Scores",
        f"- Paper completeness score: `{paper_score}%`",
        f"- Submission intake readiness score: `{intake_score}%`",
        f"- Publication readiness score: `{publication_score}%`",
        "",
        "## Evidence Summary",
        f"- Intake validation status: `{validation_status}`",
        f"- Missing intake fields: `{missing_fields}`",
        f"- Closure signal in blocker sheet: `{closure_signal}`",
        f"- Core document presence: `{doc_present}/{doc_total}`",
        f"- Core artifact presence: `{artifact_present}/{artifact_total}`",
        f"- Canonical compile-clean logs: `{clean_logs}/{total_logs}`",
        f"- Claim consistency status: `{consistency_status}`",
        f"- Claim required checks: `{consistency_passed}/{consistency_total}`",
        f"- Claim forbidden hits: `{forbidden_hits}`",
        f"- Real-value gate status: `{real_value_status}`",
        f"- Real-value gate blockers: `{real_value_blockers}`",
        "",
        "## Compile Log Detail",
    ]
    for note in log_notes:
        lines.append(f"- {note}")

    lines.extend(
        [
            "",
            "## Interpretation",
            "- Paper completeness focuses on manuscript/story/packet/compile evidence and is intentionally separated from portal metadata.",
            "- Submission intake readiness tracks venue/author/release input completion from `submission_intake_validation_61day.md`.",
        ]
    )
    if (
        validation_status == "READY"
        and missing_fields == 0
        and real_value_status == "PASS"
        and real_value_blockers == 0
    ):
        lines.append(
            "- Publication readiness is now aligned with paper completeness because intake blockers are closed."
        )
    else:
        lines.append(
            "- Publication readiness combines both, so it stays below paper completeness while intake is still blocked."
        )
    if real_value_status != "PASS" or real_value_blockers > 0:
        lines.append(
            "- Real-value gate is not clean, so intake readiness is penalty-adjusted even if required fields are filled."
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    output_path = Path(args.output)
    validation_path = Path(args.validation)
    blocker_path = Path(args.blocker)
    consistency_audit_path = Path(args.consistency_audit)
    real_value_gate_path = Path(args.real_value_gate)

    core_docs = [
        root / "paper_conference_8page_final_pass_61day_en.md",
        root / "table_final_bundle_61day.md",
        root / "reviewer_rebuttal_short_pack_61day_ko_en.md",
        root / "submission_blocker_sheet_61day.md",
        root / "submission_final_qc_checklist_61day.md",
        root / "submission_run_me_first_61day.md",
    ]
    core_artifacts = [
        root / "paper_source_kit_61day" / "paper_conference_8page_asset_locked_61day.tex",
        root / "paper_source_kit_61day" / "paper_conference_8page_asset_locked_61day.pdf",
        root
        / "venue_packets"
        / "applied_conf_default_blind_61day"
        / "manuscript_bundle_61day"
        / "paper_blind_bound_61day.tex",
        root
        / "venue_packets"
        / "applied_conf_default_blind_61day"
        / "manuscript_bundle_61day"
        / "paper_blind_bound_61day.pdf",
        root
        / "venue_packets"
        / "applied_conf_default_camera-ready_61day"
        / "manuscript_bundle_61day"
        / "paper_camera-ready_bound_61day.tex",
        root
        / "venue_packets"
        / "applied_conf_default_camera-ready_61day"
        / "manuscript_bundle_61day"
        / "paper_camera-ready_bound_61day.pdf",
    ]
    canonical_logs = [
        root / "paper_source_kit_61day" / "paper_conference_8page_asset_locked_61day.log",
        root
        / "venue_packets"
        / "applied_conf_default_blind_61day"
        / "manuscript_bundle_61day"
        / "paper_blind_bound_61day.log",
        root
        / "venue_packets"
        / "applied_conf_default_camera-ready_61day"
        / "manuscript_bundle_61day"
        / "paper_camera-ready_bound_61day.log",
    ]

    validation_status, missing_fields = parse_validation(validation_path)
    closure_signal = contains_closure_signal(blocker_path)
    doc_present, doc_total, doc_ratio = exists_ratio(core_docs)
    artifact_present, artifact_total, artifact_ratio = exists_ratio(core_artifacts)
    clean_logs, total_logs, clean_ratio, log_notes = compile_clean_ratio(canonical_logs)
    consistency_status, consistency_passed, consistency_total, forbidden_hits = parse_consistency_audit(
        consistency_audit_path
    )
    real_value_status, real_value_blockers = parse_real_value_gate(real_value_gate_path)
    consistency_ratio = (
        (consistency_passed / consistency_total)
        if consistency_total > 0 and consistency_status != "UNKNOWN"
        else 0.0
    )
    if forbidden_hits > 0:
        consistency_ratio = max(0.0, consistency_ratio - min(1.0, forbidden_hits * 0.2))

    # Paper completeness: closure signal + docs + artifacts + compile + claim consistency.
    paper_raw = (
        (15.0 if closure_signal else 0.0)
        + (doc_ratio * 25.0)
        + (artifact_ratio * 20.0)
        + (clean_ratio * 20.0)
        + (consistency_ratio * 20.0)
    )
    paper_score = clamp(paper_raw)

    # Intake readiness: minimum required fields are 16 in the current template.
    intake_raw = (1.0 - (missing_fields / 16.0)) * 100.0
    if real_value_status != "PASS" or real_value_blockers > 0:
        real_value_penalty = 20.0 + (10.0 * max(real_value_blockers, 1))
        intake_raw = max(0.0, intake_raw - real_value_penalty)
    intake_score = clamp(intake_raw)

    # Publication readiness: emphasize paper quality while still reflecting submission blockers.
    publication_raw = (paper_score * 0.9) + (intake_score * 0.1)
    publication_score = clamp(publication_raw)

    date_str = dt.date.today().isoformat()
    report = build_markdown(
        date_str=date_str,
        paper_score=paper_score,
        intake_score=intake_score,
        publication_score=publication_score,
        validation_status=validation_status,
        missing_fields=missing_fields,
        closure_signal=closure_signal,
        doc_present=doc_present,
        doc_total=doc_total,
        artifact_present=artifact_present,
        artifact_total=artifact_total,
        clean_logs=clean_logs,
        total_logs=total_logs,
        log_notes=log_notes,
        consistency_status=consistency_status,
        consistency_passed=consistency_passed,
        consistency_total=consistency_total,
        forbidden_hits=forbidden_hits,
        real_value_status=real_value_status,
        real_value_blockers=real_value_blockers,
        output_path=output_path,
    )
    output_path.write_text(report, encoding="utf-8")

    print(f"Paper completeness score: {paper_score}%")
    print(f"Submission intake readiness score: {intake_score}%")
    print(f"Publication readiness score: {publication_score}%")
    print(f"Validation status: {validation_status}")
    print(f"Missing fields: {missing_fields}")
    print(f"Real-value gate: {real_value_status} (blockers={real_value_blockers})")
    print(f"Report: {output_path}")


if __name__ == "__main__":
    main()
