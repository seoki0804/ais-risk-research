#!/usr/bin/env python3
"""Build a one-page control tower report for submission release readiness."""

from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path


DEFAULT_ROOT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13"
)
DEFAULT_OUTPUT = DEFAULT_ROOT / "submission_release_control_tower_61day.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--require-real-values",
        action="store_true",
        help="Treat real-value gate as a blocking condition.",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def pick(text: str, pattern: str, default: str = "MISSING") -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return default
    return match.group(1)


def yes_no(condition: bool) -> str:
    return "PASS" if condition else "HOLD"


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    output = Path(args.output)
    require_real_values = bool(args.require_real_values)

    intake_path = root / "submission_intake_validation_61day.md"
    hard_gate_path = root / "submission_hard_gate_61day.md"
    cert_path = root / "submission_readiness_certificate_61day.md"
    strict_path = root / "submission_metadata_strict_audit_61day.md"
    operator_path = root / "submission_release_operator_latest_61day.md"
    snapshot_path = root / "submission_release_snapshot_verify_latest_61day.md"
    regression_path = root / "submission_release_regression_suite_61day.md"
    real_value_path = root / "submission_metadata_real_value_gate_61day.md"

    intake_text = read_text(intake_path)
    hard_gate_text = read_text(hard_gate_path)
    cert_text = read_text(cert_path)
    strict_text = read_text(strict_path)
    operator_text = read_text(operator_path)
    snapshot_text = read_text(snapshot_path)
    regression_text = read_text(regression_path)
    real_value_text = read_text(real_value_path)

    intake_status = pick(intake_text, r"^- Status: `([^`]+)`")
    intake_missing = pick(intake_text, r"^- Missing field count: `([^`]+)`")
    hard_gate_status = pick(hard_gate_text, r"^- Final status: `([^`]+)`")
    hard_gate_checks = pick(hard_gate_text, r"^- Gate checks passed: `([^`]+)`")
    cert_status = pick(cert_text, r"^- Certificate status: `([^`]+)`")
    strict_status = pick(strict_text, r"^- Status: `([^`]+)`")

    operator_overall = pick(operator_text, r"^- Overall status: `([^`]+)`")
    operator_integrity = pick(operator_text, r"^- Snapshot integrity: `([^`]+)`")
    operator_drift = pick(operator_text, r"^- Source drift: `([^`]+)`")

    snapshot_overall = pick(snapshot_text, r"^- Overall status: `([^`]+)`")
    snapshot_integrity = pick(snapshot_text, r"^- Snapshot integrity: `([^`]+)`")
    snapshot_drift = pick(snapshot_text, r"^- Source drift check: `([^`]+)`")
    snapshot_dir = pick(snapshot_text, r"^- Snapshot directory: `([^`]+)`", default="MISSING")

    regression_overall = pick(regression_text, r"^- Overall status: `([^`]+)`")
    regression_refresh = pick(
        regression_text,
        r"\| refresh external handoff pack \| `([^`]+)` \|",
        default="MISSING",
    )
    regression_pack_local = pick(
        regression_text,
        r"\| pack-local verifier \| `([^`]+)` \|",
        default="MISSING",
    )
    regression_mode = pick(regression_text, r"^- Run mode: `([^`]+)`", default="UNKNOWN")
    real_value_status = pick(real_value_text, r"^- Status: `([^`]+)`", default="NOT_RUN")
    real_value_blockers = pick(
        real_value_text, r"^- Blocker count: `([^`]+)`", default="UNKNOWN"
    )

    checks = [
        ("intake", intake_status == "READY" and intake_missing == "0"),
        ("hard_gate", hard_gate_status == "PASS"),
        ("certificate", cert_status == "VALID"),
        ("strict_metadata", strict_status == "PASS"),
        (
            "operator",
            operator_overall == "PASS"
            and operator_integrity == "PASS"
            and operator_drift == "MATCH",
        ),
        (
            "snapshot_verify",
            snapshot_overall == "PASS"
            and snapshot_integrity == "PASS"
            and snapshot_drift == "MATCH",
        ),
        (
            "regression_suite",
            regression_overall == "PASS"
            and regression_refresh == "PASS"
            and regression_pack_local == "PASS",
        ),
        ("real_value_required", (not require_real_values) or real_value_status == "PASS"),
    ]
    overall = "PASS" if all(ok for _, ok in checks) else "HOLD"

    todos: list[str] = []
    if not (intake_status == "READY" and intake_missing == "0"):
        todos.append("Fix intake readiness to `READY` with missing `0`.")
    if hard_gate_status != "PASS":
        todos.append("Re-run hard gate until `Final status` becomes `PASS`.")
    if cert_status != "VALID":
        todos.append("Re-generate readiness certificate until `VALID`.")
    if strict_status != "PASS":
        todos.append("Resolve strict metadata findings until `PASS`.")
    if not (
        operator_overall == "PASS"
        and operator_integrity == "PASS"
        and operator_drift == "MATCH"
    ):
        todos.append("Re-run strict operator and resolve snapshot/source mismatches.")
    if not (
        snapshot_overall == "PASS"
        and snapshot_integrity == "PASS"
        and snapshot_drift == "MATCH"
    ):
        todos.append("Re-run snapshot verification and fix integrity/drift issues.")
    if regression_refresh != "PASS" or regression_pack_local != "PASS":
        todos.append("Re-run regression suite and resolve pack refresh/verifier failures.")
    elif regression_overall != "PASS":
        todos.append(
            "Regression suite is HOLD due to non-pack conditions; inspect strict-mode rows in the regression report."
        )
    if require_real_values and real_value_status != "PASS":
        todos.append(
            "Real-value gate is required in this run mode. Resolve all venue-value and TeX placeholder blockers."
        )
    elif real_value_status == "HOLD":
        todos.append(
            "Resolve real-value metadata blockers (venue values + TeX placeholders) before actual venue submission."
        )

    generated = dt.datetime.now().isoformat(timespec="seconds")
    lines = [
        "# Submission Release Control Tower 61day",
        "",
        f"- Generated: `{generated}`",
        f"- Run mode: `{'require-real-values' if require_real_values else 'default'}`",
        f"- Overall status: `{overall}`",
        f"- Snapshot directory: `{snapshot_dir}`",
        "",
        "## Status Board",
        "| Layer | Status | Detail |",
        "|---|---|---|",
        f"| Intake | `{intake_status}` | missing=`{intake_missing}` |",
        f"| Hard gate | `{hard_gate_status}` | checks=`{hard_gate_checks}` |",
        f"| Certificate | `{cert_status}` | `submission_readiness_certificate_61day.md` |",
        f"| Strict metadata | `{strict_status}` | `submission_metadata_strict_audit_61day.md` |",
        f"| Operator | `{operator_overall}` | integrity=`{operator_integrity}`, drift=`{operator_drift}` |",
        f"| Snapshot verify | `{snapshot_overall}` | integrity=`{snapshot_integrity}`, drift=`{snapshot_drift}` |",
        f"| Regression suite | `{regression_overall}` | mode=`{regression_mode}`, refresh=`{regression_refresh}`, pack_local=`{regression_pack_local}` |",
        f"| Real-value gate | `{real_value_status}` | blockers=`{real_value_blockers}`, required=`{yes_no(require_real_values)}` |",
        "",
        "## Artifact Paths",
        f"- Intake: `{intake_path}`",
        f"- Hard gate: `{hard_gate_path}`",
        f"- Certificate: `{cert_path}`",
        f"- Strict audit: `{strict_path}`",
        f"- Operator report: `{operator_path}`",
        f"- Snapshot verify: `{snapshot_path}`",
        f"- Regression report: `{regression_path}`",
        f"- Real-value gate report: `{real_value_path}`",
        "",
        "## Auto To Do",
    ]
    if todos:
        for item in todos:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Control tower report: {output}")
    print(f"Overall status: {overall}")
    if overall != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
