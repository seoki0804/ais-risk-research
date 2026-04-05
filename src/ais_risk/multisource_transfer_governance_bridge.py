from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


DETAIL_FIELDS = [
    "source_region",
    "baseline_recommended_model",
    "baseline_combined_pass",
    "baseline_negative_pairs",
    "baseline_max_target_ece",
    "governance_mode",
    "governed_model",
    "governed_calibration_method",
    "governed_combined_pass",
    "governed_negative_pairs",
    "governed_max_target_ece",
    "notes",
]


def _parse_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    return int(round(float(numeric)))


def _to_bool(value: Any) -> bool:
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "t"}


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def run_multisource_transfer_governance_bridge(
    multisource_source_summary_csv_path: str | Path,
    transfer_policy_governance_lock_json_path: str | Path,
    output_prefix: str | Path,
) -> dict[str, Any]:
    baseline_rows = _parse_csv_rows(multisource_source_summary_csv_path)
    lock_payload = json.loads(Path(transfer_policy_governance_lock_json_path).read_text(encoding="utf-8"))

    lock_source = str(lock_payload.get("source_region_for_transfer_override", "")).strip().lower()
    lock_model = str(lock_payload.get("selected_transfer_model", "")).strip()
    lock_method = str(lock_payload.get("selected_transfer_method", "")).strip()
    lock_candidate = lock_payload.get("selected_candidate", {}) or {}
    lock_ready = bool(lock_payload.get("governance_ready_for_lock"))
    lock_transfer_pass = bool(lock_payload.get("transfer_policy_pass"))
    lock_oot_pass = bool(lock_payload.get("out_of_time_policy_pass"))
    lock_combined_pass = bool(lock_ready and lock_transfer_pass and lock_oot_pass)
    lock_projected_source_negatives = _safe_int(lock_payload.get("projected_negative_pairs_source"))
    lock_max_target_ece = _safe_float(lock_candidate.get("max_target_ece"))

    detail_rows: list[dict[str, Any]] = []
    for row in baseline_rows:
        source_region = str(row.get("source_region", "")).strip().lower()
        baseline_pass = _to_bool(row.get("recommended_combined_pass"))
        baseline_model = str(row.get("recommended_model", "")).strip()
        baseline_negatives = _safe_int(row.get("recommended_negative_pair_count"))
        baseline_max_ece = _safe_float(row.get("recommended_max_target_ece"))

        governed_mode = "baseline_recommended"
        governed_model = baseline_model
        governed_method = ""
        governed_pass = baseline_pass
        governed_negatives = baseline_negatives
        governed_max_ece = baseline_max_ece
        notes = ""

        if source_region == lock_source and lock_ready:
            governed_mode = "transfer_override_locked"
            governed_model = lock_model or baseline_model
            governed_method = lock_method
            governed_pass = lock_combined_pass
            governed_negatives = lock_projected_source_negatives
            governed_max_ece = lock_max_target_ece
            notes = (
                f"source override from policy lock "
                f"(baseline_neg={lock_payload.get('baseline_negative_pairs_source', 'n/a')} -> "
                f"projected_neg={lock_payload.get('projected_negative_pairs_source', 'n/a')})"
            )

        detail_rows.append(
            {
                "source_region": source_region,
                "baseline_recommended_model": baseline_model,
                "baseline_combined_pass": bool(baseline_pass),
                "baseline_negative_pairs": baseline_negatives,
                "baseline_max_target_ece": baseline_max_ece,
                "governance_mode": governed_mode,
                "governed_model": governed_model,
                "governed_calibration_method": governed_method,
                "governed_combined_pass": bool(governed_pass),
                "governed_negative_pairs": governed_negatives,
                "governed_max_target_ece": governed_max_ece,
                "notes": notes,
            }
        )

    detail_rows = sorted(detail_rows, key=lambda item: str(item.get("source_region", "")))
    source_count = len(detail_rows)
    baseline_pass_count = sum(1 for row in detail_rows if bool(row.get("baseline_combined_pass")))
    governed_pass_count = sum(1 for row in detail_rows if bool(row.get("governed_combined_pass")))
    improved_source_count = sum(
        1
        for row in detail_rows
        if (not bool(row.get("baseline_combined_pass"))) and bool(row.get("governed_combined_pass"))
    )

    prefix = Path(output_prefix)
    detail_csv_path = prefix.with_name(f"{prefix.name}_detail.csv")
    summary_md_path = prefix.with_suffix(".md")
    summary_json_path = prefix.with_suffix(".json")

    _write_csv(detail_csv_path, detail_rows, DETAIL_FIELDS)

    lines = [
        "# Multi-Source Transfer Governance Bridge",
        "",
        f"- source summary csv: `{Path(multisource_source_summary_csv_path).resolve()}`",
        f"- policy lock json: `{Path(transfer_policy_governance_lock_json_path).resolve()}`",
        f"- baseline_combined_pass_count: `{baseline_pass_count}/{source_count}`",
        f"- governed_combined_pass_count: `{governed_pass_count}/{source_count}`",
        f"- improved_source_count: `{improved_source_count}`",
        "",
        "| Source | Baseline Model | Baseline Pass | Baseline Neg Pairs | Baseline Max ECE | Mode | Governed Model | Governed Method | Governed Pass | Governed Neg Pairs | Governed Max ECE |",
        "|---|---|---:|---:|---:|---|---|---|---:|---:|---:|",
    ]
    for row in detail_rows:
        lines.append(
            "| "
            + f"{row.get('source_region', '')} | "
            + f"{row.get('baseline_recommended_model', 'n/a')} | "
            + f"{'yes' if row.get('baseline_combined_pass') else 'no'} | "
            + f"{row.get('baseline_negative_pairs', 'n/a')} | "
            + f"{_fmt(row.get('baseline_max_target_ece'))} | "
            + f"{row.get('governance_mode', '')} | "
            + f"{row.get('governed_model', 'n/a')} | "
            + f"{row.get('governed_calibration_method', '') or '-'} | "
            + f"{'yes' if row.get('governed_combined_pass') else 'no'} | "
            + f"{row.get('governed_negative_pairs', 'n/a')} | "
            + f"{_fmt(row.get('governed_max_target_ece'))} |"
        )
    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {
        "status": "completed",
        "multisource_source_summary_csv_path": str(Path(multisource_source_summary_csv_path).resolve()),
        "transfer_policy_governance_lock_json_path": str(Path(transfer_policy_governance_lock_json_path).resolve()),
        "lock_source_region": lock_source,
        "baseline_combined_pass_count": int(baseline_pass_count),
        "governed_combined_pass_count": int(governed_pass_count),
        "source_count": int(source_count),
        "improved_source_count": int(improved_source_count),
        "detail_csv_path": str(detail_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
    }
    summary_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

