from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


POLICY_LOCK_FIELDS = [
    "region",
    "dataset",
    "in_time_model",
    "out_of_time_threshold_policy",
    "out_of_time_delta_f1",
    "out_of_time_ece",
    "out_of_time_combined_pass",
    "source_transfer_model",
    "source_transfer_calibration_method",
    "source_transfer_metric_mode",
    "source_transfer_negative_pairs",
    "source_transfer_pair_count",
    "source_transfer_max_target_ece",
    "governance_status",
    "governance_notes",
]


PROJECTED_TRANSFER_FIELDS = [
    "source_region",
    "target_region",
    "source_dataset",
    "target_dataset",
    "recommended_model",
    "status",
    "source_f1",
    "target_f1",
    "delta_f1",
    "source_auroc",
    "target_auroc",
    "delta_auroc",
    "target_ece",
    "target_brier",
    "threshold",
    "transfer_summary_json_path",
    "target_predictions_csv_path",
    "target_calibration_summary_json_path",
    "notes",
]


CANDIDATE_FIELDS = [
    "source_region",
    "model_name",
    "method",
    "pair_count",
    "negative_fixed_count",
    "negative_retuned_count",
    "mean_delta_f1_fixed",
    "mean_delta_f1_retuned",
    "max_target_ece",
    "ece_gate_pass_all_targets",
    "fixed_policy_pass",
    "retuned_policy_pass",
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


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def _region_from_dataset(dataset: str) -> str:
    return str(dataset).replace("_pooled_pairwise", "")


def _build_candidate_rows(
    detail_rows: list[dict[str, str]],
    source_region: str,
    max_target_ece: float,
    max_negative_pairs_allowed: int,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in detail_rows:
        if str(row.get("status", "")).strip() != "completed":
            continue
        if str(row.get("source_region", "")).strip() != source_region:
            continue
        key = (str(row.get("model_name", "")).strip(), str(row.get("method", "")).strip())
        if not key[0] or not key[1]:
            continue
        grouped[key].append(row)

    output: list[dict[str, Any]] = []
    for (model_name, method), rows in sorted(grouped.items()):
        fixed_values = [float(row["delta_f1_fixed"]) for row in rows if _safe_float(row.get("delta_f1_fixed")) is not None]
        retuned_values = [
            float(row["delta_f1_retuned"]) for row in rows if _safe_float(row.get("delta_f1_retuned")) is not None
        ]
        ece_values = [float(row["target_ece"]) for row in rows if _safe_float(row.get("target_ece")) is not None]
        negative_fixed_count = sum(1 for value in fixed_values if value < 0.0)
        negative_retuned_count = sum(1 for value in retuned_values if value < 0.0)
        ece_pass_all_targets = bool(ece_values) and all(value <= float(max_target_ece) for value in ece_values)
        output.append(
            {
                "source_region": source_region,
                "model_name": model_name,
                "method": method,
                "pair_count": len(rows),
                "negative_fixed_count": negative_fixed_count,
                "negative_retuned_count": negative_retuned_count,
                "mean_delta_f1_fixed": float(mean(fixed_values)) if fixed_values else None,
                "mean_delta_f1_retuned": float(mean(retuned_values)) if retuned_values else None,
                "max_target_ece": max(ece_values) if ece_values else None,
                "ece_gate_pass_all_targets": ece_pass_all_targets,
                "fixed_policy_pass": bool(
                    ece_pass_all_targets and negative_fixed_count <= int(max_negative_pairs_allowed)
                ),
                "retuned_policy_pass": bool(
                    ece_pass_all_targets and negative_retuned_count <= int(max_negative_pairs_allowed)
                ),
            }
        )
    return output


def _select_candidate(
    candidates: list[dict[str, Any]],
    metric_mode: str,
    override_model_name: str,
    override_method: str,
) -> dict[str, Any] | None:
    if not candidates:
        return None
    mode = str(metric_mode).strip().lower()
    if mode not in {"fixed", "retuned"}:
        raise ValueError("metric_mode must be one of: fixed, retuned")

    if override_model_name and override_method:
        selected = next(
            (
                row
                for row in candidates
                if str(row.get("model_name", "")) == override_model_name
                and str(row.get("method", "")) == override_method
            ),
            None,
        )
        return selected

    gate_key = "fixed_policy_pass" if mode == "fixed" else "retuned_policy_pass"
    score_key = "mean_delta_f1_fixed" if mode == "fixed" else "mean_delta_f1_retuned"
    selection_pool = [row for row in candidates if bool(row.get(gate_key))]
    if not selection_pool:
        return None
    selection_pool = sorted(
        selection_pool,
        key=lambda row: (
            -float(_safe_float(row.get(score_key)) or -999.0),
            float(_safe_float(row.get("max_target_ece")) or 999.0),
            str(row.get("model_name", "")),
            str(row.get("method", "")),
        ),
    )
    return selection_pool[0]


def run_transfer_policy_governance_lock(
    recommendation_csv_path: str | Path,
    transfer_check_csv_path: str | Path,
    out_of_time_threshold_policy_compare_json_path: str | Path,
    transfer_calibration_probe_detail_csv_path: str | Path,
    output_prefix: str | Path,
    source_region_for_transfer_override: str = "houston",
    metric_mode: str = "fixed",
    max_target_ece: float = 0.10,
    max_negative_pairs_allowed: int = 1,
    required_out_of_time_policy: str = "fixed_baseline_threshold",
    override_model_name: str = "",
    override_method: str = "",
) -> dict[str, Any]:
    source_region = str(source_region_for_transfer_override).strip().lower()
    if not source_region:
        raise ValueError("source_region_for_transfer_override is required")

    recommendation_rows = _parse_csv_rows(recommendation_csv_path)
    transfer_rows = _parse_csv_rows(transfer_check_csv_path)
    calibration_detail_rows = _parse_csv_rows(transfer_calibration_probe_detail_csv_path)
    out_of_time_policy_summary = json.loads(Path(out_of_time_threshold_policy_compare_json_path).read_text(encoding="utf-8"))

    candidates = _build_candidate_rows(
        detail_rows=calibration_detail_rows,
        source_region=source_region,
        max_target_ece=float(max_target_ece),
        max_negative_pairs_allowed=int(max_negative_pairs_allowed),
    )
    selected_candidate = _select_candidate(
        candidates=candidates,
        metric_mode=metric_mode,
        override_model_name=str(override_model_name).strip(),
        override_method=str(override_method).strip(),
    )
    if selected_candidate is None:
        raise ValueError("No transfer calibration candidate satisfies the governance gate.")

    selected_model = str(selected_candidate["model_name"])
    selected_method = str(selected_candidate["method"])
    mode = str(metric_mode).strip().lower()
    if mode == "fixed":
        selected_negative_pairs = int(_safe_float(selected_candidate.get("negative_fixed_count")) or 0)
    else:
        selected_negative_pairs = int(_safe_float(selected_candidate.get("negative_retuned_count")) or 0)

    selected_pair_rows = [
        row
        for row in calibration_detail_rows
        if str(row.get("source_region", "")).strip().lower() == source_region
        and str(row.get("model_name", "")).strip() == selected_model
        and str(row.get("method", "")).strip() == selected_method
        and str(row.get("status", "")).strip() == "completed"
    ]
    selected_pair_by_target = {str(row.get("target_region", "")).strip().lower(): row for row in selected_pair_rows}

    oot_rows = list(out_of_time_policy_summary.get("houston_rows", []))
    oot_policy_row = next(
        (
            row
            for row in oot_rows
            if str(row.get("policy", "")).strip() == str(required_out_of_time_policy).strip()
            and str(row.get("status", "")).strip() == "completed"
        ),
        None,
    )

    projected_rows: list[dict[str, Any]] = []
    for row in transfer_rows:
        payload = dict(row)
        if str(row.get("source_region", "")).strip().lower() == source_region:
            target_region = str(row.get("target_region", "")).strip().lower()
            detail = selected_pair_by_target.get(target_region)
            if detail is None:
                existing = str(payload.get("notes", "")).strip()
                payload["notes"] = (
                    f"{existing};missing_selected_transfer_pair_row".strip(";")
                    if existing
                    else "missing_selected_transfer_pair_row"
                )
            else:
                payload["recommended_model"] = f"{selected_model}/{selected_method}"
                payload["source_f1"] = detail.get("source_f1_fixed", "")
                if mode == "fixed":
                    payload["target_f1"] = detail.get("target_f1_fixed", "")
                    payload["delta_f1"] = detail.get("delta_f1_fixed", "")
                    payload["threshold"] = detail.get("threshold", "")
                else:
                    payload["target_f1"] = detail.get("target_best_f1", "")
                    payload["delta_f1"] = detail.get("delta_f1_retuned", "")
                    payload["threshold"] = detail.get("target_best_threshold", "")
                payload["target_ece"] = detail.get("target_ece", "")
                payload["target_brier"] = detail.get("target_brier", "")
                payload["transfer_summary_json_path"] = detail.get("transfer_summary_json_path", "")
                existing = str(payload.get("notes", "")).strip()
                lock_note = f"policy_override:{selected_model}/{selected_method}:{mode}"
                payload["notes"] = f"{existing};{lock_note}".strip(";") if existing else lock_note
        projected_rows.append(payload)

    baseline_negative_global = sum(
        1 for row in transfer_rows if _safe_float(row.get("delta_f1")) is not None and float(row["delta_f1"]) < 0.0
    )
    projected_negative_global = sum(
        1 for row in projected_rows if _safe_float(row.get("delta_f1")) is not None and float(row["delta_f1"]) < 0.0
    )
    baseline_negative_source = sum(
        1
        for row in transfer_rows
        if str(row.get("source_region", "")).strip().lower() == source_region
        and _safe_float(row.get("delta_f1")) is not None
        and float(row["delta_f1"]) < 0.0
    )
    projected_negative_source = sum(
        1
        for row in projected_rows
        if str(row.get("source_region", "")).strip().lower() == source_region
        and _safe_float(row.get("delta_f1")) is not None
        and float(row["delta_f1"]) < 0.0
    )

    oot_policy_pass = bool(oot_policy_row and bool(oot_policy_row.get("combined_pass")))
    transfer_policy_pass = bool(projected_negative_global <= int(max_negative_pairs_allowed))
    governance_ready = bool(oot_policy_pass and transfer_policy_pass)

    recommendation_map = {
        str(row.get("dataset", "")).strip(): str(row.get("model_name", "")).strip()
        for row in recommendation_rows
        if str(row.get("dataset", "")).strip() and str(row.get("model_name", "")).strip()
    }

    policy_lock_rows: list[dict[str, Any]] = []
    for dataset, model_name in sorted(recommendation_map.items()):
        region = _region_from_dataset(dataset)
        out_row = next(
            (
                row
                for row in out_of_time_policy_summary.get("houston_rows", [])
                if str(row.get("dataset", "")).strip() == dataset
                and str(row.get("policy", "")).strip() == str(required_out_of_time_policy).strip()
                and str(row.get("status", "")).strip() == "completed"
            ),
            None,
        )
        if region == source_region:
            source_transfer_model = selected_model
            source_transfer_method = selected_method
            source_transfer_negative = selected_negative_pairs
            source_transfer_pair_count = int(_safe_float(selected_candidate.get("pair_count")) or 0)
            source_transfer_max_ece = _safe_float(selected_candidate.get("max_target_ece"))
            governance_status = "locked_transfer_only_override"
            governance_notes = (
                "Use split governance: keep in-time recommendation path, "
                "apply calibrated transfer-only source policy."
            )
        else:
            source_transfer_model = model_name
            source_transfer_method = "none"
            source_transfer_negative = ""
            source_transfer_pair_count = ""
            source_transfer_max_ece = ""
            governance_status = "locked_default_recommendation"
            governance_notes = "No transfer override applied."

        policy_lock_rows.append(
            {
                "region": region,
                "dataset": dataset,
                "in_time_model": model_name,
                "out_of_time_threshold_policy": required_out_of_time_policy,
                "out_of_time_delta_f1": out_row.get("delta_f1") if out_row else "",
                "out_of_time_ece": out_row.get("out_of_time_ece") if out_row else "",
                "out_of_time_combined_pass": out_row.get("combined_pass") if out_row else "",
                "source_transfer_model": source_transfer_model,
                "source_transfer_calibration_method": source_transfer_method,
                "source_transfer_metric_mode": mode,
                "source_transfer_negative_pairs": source_transfer_negative,
                "source_transfer_pair_count": source_transfer_pair_count,
                "source_transfer_max_target_ece": source_transfer_max_ece,
                "governance_status": governance_status,
                "governance_notes": governance_notes,
            }
        )

    output_root = Path(output_prefix).resolve()
    policy_lock_csv_path = output_root.with_name(f"{output_root.name}_policy_lock.csv")
    projected_transfer_csv_path = output_root.with_name(f"{output_root.name}_projected_transfer_check.csv")
    candidate_summary_csv_path = output_root.with_name(f"{output_root.name}_candidate_summary.csv")
    summary_md_path = output_root.with_suffix(".md")
    summary_json_path = output_root.with_suffix(".json")
    _write_csv(policy_lock_csv_path, policy_lock_rows, POLICY_LOCK_FIELDS)
    _write_csv(projected_transfer_csv_path, projected_rows, PROJECTED_TRANSFER_FIELDS)
    _write_csv(candidate_summary_csv_path, candidates, CANDIDATE_FIELDS)

    lines = [
        "# Transfer Policy Governance Lock",
        "",
        "## Inputs",
        "",
        f"- recommendation_csv: `{Path(recommendation_csv_path).resolve()}`",
        f"- transfer_check_csv: `{Path(transfer_check_csv_path).resolve()}`",
        f"- out_of_time_threshold_policy_compare_json: `{Path(out_of_time_threshold_policy_compare_json_path).resolve()}`",
        f"- transfer_calibration_probe_detail_csv: `{Path(transfer_calibration_probe_detail_csv_path).resolve()}`",
        f"- source_region_for_transfer_override: `{source_region}`",
        f"- metric_mode: `{mode}`",
        f"- max_target_ece: `{_fmt(max_target_ece)}`",
        f"- max_negative_pairs_allowed: `{int(max_negative_pairs_allowed)}`",
        f"- required_out_of_time_policy: `{required_out_of_time_policy}`",
        "",
        "## Locked Decision",
        "",
        f"- selected transfer override candidate: `{selected_model}/{selected_method}`",
        f"- selected candidate pair count: `{selected_candidate.get('pair_count', 'n/a')}`",
        f"- selected candidate negative pairs (mode={mode}): `{selected_negative_pairs}`",
        f"- selected candidate max target ECE: `{_fmt(selected_candidate.get('max_target_ece'))}`",
        "",
        "## Transfer Gap Projection",
        "",
        f"- baseline negative pairs (global): `{baseline_negative_global}/{len(transfer_rows)}`",
        f"- projected negative pairs (global): `{projected_negative_global}/{len(projected_rows)}`",
        f"- baseline negative pairs (source={source_region}): `{baseline_negative_source}`",
        f"- projected negative pairs (source={source_region}): `{projected_negative_source}`",
        "",
        "## Governance Gate",
        "",
        f"- out-of-time policy pass (`{required_out_of_time_policy}`): `{oot_policy_pass}`",
        f"- transfer projection pass (negative pairs <= {int(max_negative_pairs_allowed)}): `{transfer_policy_pass}`",
        f"- governance_ready_for_lock: `{governance_ready}`",
        "",
        "## Outputs",
        "",
        f"- policy_lock_csv: `{policy_lock_csv_path}`",
        f"- projected_transfer_check_csv: `{projected_transfer_csv_path}`",
        f"- candidate_summary_csv: `{candidate_summary_csv_path}`",
        f"- summary_md: `{summary_md_path}`",
        f"- summary_json: `{summary_json_path}`",
        "",
    ]
    summary_md_path.write_text("\n".join(lines), encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "completed",
        "recommendation_csv_path": str(Path(recommendation_csv_path).resolve()),
        "transfer_check_csv_path": str(Path(transfer_check_csv_path).resolve()),
        "out_of_time_threshold_policy_compare_json_path": str(Path(out_of_time_threshold_policy_compare_json_path).resolve()),
        "transfer_calibration_probe_detail_csv_path": str(Path(transfer_calibration_probe_detail_csv_path).resolve()),
        "source_region_for_transfer_override": source_region,
        "metric_mode": mode,
        "max_target_ece": float(max_target_ece),
        "max_negative_pairs_allowed": int(max_negative_pairs_allowed),
        "required_out_of_time_policy": str(required_out_of_time_policy),
        "selected_transfer_model": selected_model,
        "selected_transfer_method": selected_method,
        "selected_candidate": selected_candidate,
        "baseline_negative_pairs_global": int(baseline_negative_global),
        "projected_negative_pairs_global": int(projected_negative_global),
        "baseline_negative_pairs_source": int(baseline_negative_source),
        "projected_negative_pairs_source": int(projected_negative_source),
        "out_of_time_policy_pass": bool(oot_policy_pass),
        "transfer_policy_pass": bool(transfer_policy_pass),
        "governance_ready_for_lock": bool(governance_ready),
        "policy_lock_csv_path": str(policy_lock_csv_path),
        "projected_transfer_check_csv_path": str(projected_transfer_csv_path),
        "candidate_summary_csv_path": str(candidate_summary_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


__all__ = ["run_transfer_policy_governance_lock"]
