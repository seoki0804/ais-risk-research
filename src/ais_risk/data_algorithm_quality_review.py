from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


DATASET_SCORECARD_FIELDS = [
    "region",
    "dataset",
    "recommended_model",
    "f1_mean",
    "f1_std",
    "ece_mean",
    "positive_support",
    "support_pass",
    "variance_pass",
    "calibration_pass",
    "baseline_out_of_time_delta_f1",
    "governed_out_of_time_delta_f1",
    "out_of_time_delta_f1",
    "temporal_policy",
    "temporal_pass",
    "transfer_pair_count",
    "baseline_negative_transfer_pairs",
    "baseline_max_target_ece",
    "baseline_transfer_negative_pass",
    "baseline_transfer_ece_pass",
    "governance_mode",
    "governed_negative_transfer_pairs",
    "governed_max_target_ece",
    "governed_transfer_negative_pass",
    "governed_transfer_ece_pass",
    "baseline_combined_pass",
    "final_combined_pass",
    "risk_level",
    "notes",
]


HIGH_RISK_MODEL_FIELDS = [
    "dataset",
    "model_name",
    "model_family",
    "f1_mean",
    "f1_std",
    "ece_mean",
    "risk_flags",
]


TODO_FIELDS = [
    "id",
    "priority",
    "title",
    "rationale",
    "action",
    "acceptance_criteria",
    "evidence",
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


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def _region_from_dataset(dataset: str) -> str:
    return str(dataset).replace("_pooled_pairwise", "")


def _risk_level(fail_count: int) -> str:
    if fail_count >= 3:
        return "high"
    if fail_count == 2:
        return "medium"
    if fail_count == 1:
        return "low"
    return "minimal"


def _dq5_acceptance_met(manuscript_freeze_packet: dict[str, Any] | None) -> bool:
    if not manuscript_freeze_packet:
        return False
    return bool(
        _to_bool(manuscript_freeze_packet.get("recommended_claim_hygiene_ready"))
        and str(manuscript_freeze_packet.get("model_claim_caveat_text", "")).strip()
    )


def _build_todo_items(
    scorecard_rows: list[dict[str, Any]],
    high_risk_rows: list[dict[str, Any]],
    min_positive_support: int,
    max_ece: float,
    max_f1_std: float,
    min_out_of_time_delta_f1: float,
    max_negative_transfer_pairs: int,
    transfer_override_seed_stress_test: dict[str, Any] | None = None,
    manuscript_freeze_packet: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    todo_rows: list[dict[str, Any]] = []

    temporal_fail_rows = [row for row in scorecard_rows if not _to_bool(row.get("temporal_pass"))]
    if temporal_fail_rows:
        regions = ", ".join(sorted({str(row.get("region", "")) for row in temporal_fail_rows}))
        worst_delta = min(
            [
                float(_safe_float(row.get("out_of_time_delta_f1")) or 0.0)
                for row in temporal_fail_rows
                if _safe_float(row.get("out_of_time_delta_f1")) is not None
            ],
            default=0.0,
        )
        todo_rows.append(
            {
                "id": "DQ-1",
                "priority": "P1",
                "title": "Close out-of-time drift on remaining failing regions",
                "rationale": (
                    f"Temporal gate failed in region(s): {regions}. "
                    f"Worst observed out-of-time ΔF1={worst_delta:.4f} "
                    f"(target >= {min_out_of_time_delta_f1:.4f})."
                ),
                "action": (
                    "Run region-specific temporal threshold policy retune and compare fixed-baseline vs "
                    "val-tuned threshold under unchanged calibration gate. Keep recommendation rule fixed and "
                    "document pre/post delta with CI95."
                ),
                "acceptance_criteria": (
                    f"Every failing region reaches out-of-time ΔF1 >= {min_out_of_time_delta_f1:.4f} "
                    f"while recommended-model ECE <= {max_ece:.2f} and in-time F1 regression <= 0.02."
                ),
                "evidence": "dataset_scorecard: temporal_pass / out_of_time_delta_f1",
            }
        )

    transfer_fail_rows = [
        row
        for row in scorecard_rows
        if (not _to_bool(row.get("governed_transfer_negative_pass")))
        or (not _to_bool(row.get("governed_transfer_ece_pass")))
    ]
    if transfer_fail_rows:
        regions = ", ".join(sorted({str(row.get("region", "")) for row in transfer_fail_rows}))
        todo_rows.append(
            {
                "id": "DQ-2",
                "priority": "P1",
                "title": "Resolve remaining source-transfer governance failures",
                "rationale": (
                    f"Governed transfer gate is still failing for source region(s): {regions}. "
                    f"Required limits are negative pairs <= {int(max_negative_transfer_pairs)} "
                    f"and max target ECE <= {max_ece:.2f}."
                ),
                "action": (
                    "Expand source-model calibration probe (`none/platt/isotonic`) and apply split-governance "
                    "only where transfer-only policy improves negatives without violating target ECE gate."
                ),
                "acceptance_criteria": (
                    f"All failing source regions satisfy governed negative pairs <= {int(max_negative_transfer_pairs)} "
                    f"and governed max target ECE <= {max_ece:.2f}."
                ),
                "evidence": "dataset_scorecard: governed_negative_transfer_pairs / governed_max_target_ece",
            }
        )

    governance_override_rows = [
        row for row in scorecard_rows if str(row.get("governance_mode", "")) == "transfer_override_locked"
    ]
    dq3_acceptance_met = bool(
        transfer_override_seed_stress_test
        and _to_bool(transfer_override_seed_stress_test.get("dq3_acceptance_met"))
    )
    if governance_override_rows and not dq3_acceptance_met:
        regions = ", ".join(sorted({str(row.get("region", "")) for row in governance_override_rows}))
        todo_rows.append(
            {
                "id": "DQ-3",
                "priority": "P2",
                "title": "Stress-test transfer-only override path before freeze",
                "rationale": (
                    f"Transfer override lock is active for: {regions}. "
                    "This mitigates transfer negatives but needs an explicit independent holdout check."
                ),
                "action": (
                    "Run an independent holdout replay for override source regions using locked override "
                    "model/method, and report source-side utility loss and target-side calibration drift "
                    "in one governance appendix table."
                ),
                "acceptance_criteria": (
                    "Override path is retained only if target-side transfer gate remains satisfied and "
                    "source-side utility loss is explicitly disclosed with quantitative bounds."
                ),
                "evidence": "dataset_scorecard: governance_mode=transfer_override_locked",
            }
        )

    low_support_rows = [row for row in scorecard_rows if not _to_bool(row.get("support_pass"))]
    if low_support_rows:
        regions = ", ".join(sorted({str(row.get("region", "")) for row in low_support_rows}))
        todo_rows.append(
            {
                "id": "DQ-4",
                "priority": "P2",
                "title": "Raise positive support for low-support evaluation regions",
                "rationale": (
                    f"Positive support below minimum policy ({int(min_positive_support)}) in region(s): {regions}."
                ),
                "action": (
                    "Prioritize additional labeled positives for low-support regions and re-run only "
                    "the affected evaluation bundles with the same model-selection policy."
                ),
                "acceptance_criteria": (
                    f"All recommendation rows satisfy positive_support >= {int(min_positive_support)}."
                ),
                "evidence": "dataset_scorecard: positive_support / support_pass",
            }
        )

    variance_or_calibration_risk = [
        row
        for row in high_risk_rows
        if ("seed_variance_high" in str(row.get("risk_flags", ""))) or ("ece_high" in str(row.get("risk_flags", "")))
    ]
    dq5_acceptance_met = _dq5_acceptance_met(manuscript_freeze_packet)
    if variance_or_calibration_risk and not dq5_acceptance_met:
        dataset_count = len({str(row.get("dataset", "")) for row in variance_or_calibration_risk})
        todo_rows.append(
            {
                "id": "DQ-5",
                "priority": "P3",
                "title": "Trim unstable high-capacity candidates from narrative claims",
                "rationale": (
                    f"{len(variance_or_calibration_risk)} model rows across {dataset_count} dataset(s) "
                    f"show high ECE (>{max_ece:.2f}) and/or high seed variance (>{max_f1_std:.2f})."
                ),
                "action": (
                    "Keep unstable models in ablation appendix only, and keep main claim centered on "
                    "calibration-gated stable candidates. Add one explicit reviewer-facing caveat sentence."
                ),
                "acceptance_criteria": (
                    "Main-text model claims reference only candidates that pass both ECE and seed-variance gates."
                ),
                "evidence": "high_risk_models_csv: risk_flags",
            }
        )

    return todo_rows


def run_data_algorithm_quality_review(
    recommendation_csv_path: str | Path,
    aggregate_csv_path: str | Path,
    out_of_time_csv_path: str | Path,
    transfer_csv_path: str | Path,
    output_prefix: str | Path,
    multisource_transfer_governance_bridge_json_path: str | Path | None = None,
    out_of_time_threshold_policy_compare_json_path: str | Path | None = None,
    transfer_override_seed_stress_test_json_path: str | Path | None = None,
    manuscript_freeze_packet_json_path: str | Path | None = None,
    min_positive_support: int = 30,
    max_ece: float = 0.10,
    max_f1_std: float = 0.03,
    min_out_of_time_delta_f1: float = -0.05,
    max_negative_transfer_pairs: int = 1,
) -> dict[str, Any]:
    recommendation_rows = _parse_csv_rows(recommendation_csv_path)
    aggregate_rows = _parse_csv_rows(aggregate_csv_path)
    out_of_time_rows = _parse_csv_rows(out_of_time_csv_path)
    transfer_rows = _parse_csv_rows(transfer_csv_path)

    aggregate_map: dict[tuple[str, str], dict[str, str]] = {}
    for row in aggregate_rows:
        dataset = str(row.get("dataset", "")).strip()
        model_name = str(row.get("model_name", "")).strip()
        if dataset and model_name:
            aggregate_map[(dataset, model_name)] = row

    out_of_time_by_dataset: dict[str, dict[str, str]] = {}
    for row in out_of_time_rows:
        dataset = str(row.get("dataset", "")).strip()
        if dataset:
            out_of_time_by_dataset[dataset] = row

    transfer_by_source: dict[str, list[dict[str, str]]] = {}
    for row in transfer_rows:
        source = str(row.get("source_region", "")).strip()
        if not source:
            continue
        transfer_by_source.setdefault(source, []).append(row)

    governance_bridge_payload: dict[str, Any] = {}
    governance_bridge_detail_by_source: dict[str, dict[str, str]] = {}
    governance_bridge_path_resolved = (
        Path(multisource_transfer_governance_bridge_json_path).resolve()
        if multisource_transfer_governance_bridge_json_path
        else None
    )
    if governance_bridge_path_resolved and governance_bridge_path_resolved.exists():
        governance_bridge_payload = json.loads(governance_bridge_path_resolved.read_text(encoding="utf-8"))
        detail_csv_path = Path(str(governance_bridge_payload.get("detail_csv_path", "")).strip())
        if detail_csv_path.exists():
            for row in _parse_csv_rows(detail_csv_path):
                region = str(row.get("source_region", "")).strip()
                if region:
                    governance_bridge_detail_by_source[region] = row

    transfer_override_seed_stress_test: dict[str, Any] = {}
    transfer_override_seed_stress_test_path_resolved = (
        Path(transfer_override_seed_stress_test_json_path).resolve()
        if transfer_override_seed_stress_test_json_path
        else None
    )
    if transfer_override_seed_stress_test_path_resolved and transfer_override_seed_stress_test_path_resolved.exists():
        transfer_override_seed_stress_test = json.loads(
            transfer_override_seed_stress_test_path_resolved.read_text(encoding="utf-8")
        )

    manuscript_freeze_packet: dict[str, Any] = {}
    manuscript_freeze_packet_path_resolved = (
        Path(manuscript_freeze_packet_json_path).resolve()
        if manuscript_freeze_packet_json_path
        else None
    )
    if manuscript_freeze_packet_path_resolved and manuscript_freeze_packet_path_resolved.exists():
        manuscript_freeze_packet = json.loads(manuscript_freeze_packet_path_resolved.read_text(encoding="utf-8"))

    out_of_time_policy_compare_payload: dict[str, Any] = {}
    out_of_time_policy_compare_rows: dict[tuple[str, str], dict[str, str]] = {}
    out_of_time_policy_compare_path_resolved = (
        Path(out_of_time_threshold_policy_compare_json_path).resolve()
        if out_of_time_threshold_policy_compare_json_path
        else None
    )
    if out_of_time_policy_compare_path_resolved and out_of_time_policy_compare_path_resolved.exists():
        out_of_time_policy_compare_payload = json.loads(
            out_of_time_policy_compare_path_resolved.read_text(encoding="utf-8")
        )
        recommended_policy = str(
            out_of_time_policy_compare_payload.get("recommended_policy_excluding_oracle", "")
        ).strip()
        detail_csv_path = Path(str(out_of_time_policy_compare_payload.get("detail_csv_path", "")).strip())
        if recommended_policy and detail_csv_path.exists():
            for row in _parse_csv_rows(detail_csv_path):
                if str(row.get("policy", "")).strip() != recommended_policy:
                    continue
                if str(row.get("status", "")).strip() != "completed":
                    continue
                dataset = str(row.get("dataset", "")).strip()
                model_name = str(row.get("model_name", "")).strip()
                if dataset and model_name:
                    out_of_time_policy_compare_rows[(dataset, model_name)] = row

    scorecard_rows: list[dict[str, Any]] = []
    for rec_row in recommendation_rows:
        dataset = str(rec_row.get("dataset", "")).strip()
        model_name = str(rec_row.get("model_name", "")).strip()
        if not dataset or not model_name:
            continue
        region = _region_from_dataset(dataset)

        aggregate_row = aggregate_map.get((dataset, model_name), {})
        f1_mean = _safe_float(aggregate_row.get("f1_mean"))
        if f1_mean is None:
            f1_mean = _safe_float(rec_row.get("f1_mean"))
        f1_std = _safe_float(aggregate_row.get("f1_std"))
        if f1_std is None:
            f1_std = _safe_float(rec_row.get("f1_std"))
        ece_mean = _safe_float(aggregate_row.get("ece_mean"))
        if ece_mean is None:
            ece_mean = _safe_float(rec_row.get("ece_mean"))
        positive_support = _safe_float(aggregate_row.get("positive_count_mean"))
        if positive_support is None:
            oot_row_fallback = out_of_time_by_dataset.get(dataset, {})
            positive_support = _safe_float(oot_row_fallback.get("baseline_positive_count"))

        support_pass = positive_support is not None and positive_support >= float(min_positive_support)
        variance_pass = f1_std is not None and f1_std <= float(max_f1_std)
        calibration_pass = ece_mean is not None and ece_mean <= float(max_ece)

        oot_row = out_of_time_by_dataset.get(dataset, {})
        baseline_out_of_time_delta_f1 = _safe_float(oot_row.get("delta_f1"))
        governed_out_of_time_delta_f1 = baseline_out_of_time_delta_f1
        temporal_policy = "oot_val_tuned"
        oot_policy_row = out_of_time_policy_compare_rows.get((dataset, model_name))
        if oot_policy_row:
            policy_delta = _safe_float(oot_policy_row.get("delta_f1"))
            if policy_delta is not None:
                governed_out_of_time_delta_f1 = policy_delta
                temporal_policy = str(oot_policy_row.get("policy", "")).strip() or temporal_policy
        out_of_time_delta_f1 = governed_out_of_time_delta_f1
        temporal_pass = out_of_time_delta_f1 is not None and out_of_time_delta_f1 >= float(min_out_of_time_delta_f1)

        source_transfer_rows = transfer_by_source.get(region, [])
        baseline_negative_transfer_pairs = sum(
            1 for row in source_transfer_rows if (_safe_float(row.get("delta_f1")) or 0.0) < 0.0
        )
        target_ece_values = [_safe_float(row.get("target_ece")) for row in source_transfer_rows]
        baseline_max_target_ece = max([value for value in target_ece_values if value is not None], default=None)
        baseline_transfer_negative_pass = bool(
            source_transfer_rows
            and baseline_negative_transfer_pairs <= int(max_negative_transfer_pairs)
        )
        baseline_transfer_ece_pass = bool(
            source_transfer_rows
            and baseline_max_target_ece is not None
            and baseline_max_target_ece <= float(max_ece)
        )

        governance_mode = "baseline_recommended"
        governed_negative_transfer_pairs = int(baseline_negative_transfer_pairs)
        governed_max_target_ece = baseline_max_target_ece
        bridge_row = governance_bridge_detail_by_source.get(region)
        if bridge_row:
            governance_mode = str(bridge_row.get("governance_mode", "")).strip() or "baseline_recommended"
            governed_negative_from_bridge = _safe_float(bridge_row.get("governed_negative_pairs"))
            if governed_negative_from_bridge is not None:
                governed_negative_transfer_pairs = int(governed_negative_from_bridge)
            governed_max_target_ece = _safe_float(bridge_row.get("governed_max_target_ece"))
            if governed_max_target_ece is None:
                governed_max_target_ece = baseline_max_target_ece

        governed_transfer_negative_pass = bool(
            source_transfer_rows
            and governed_negative_transfer_pairs <= int(max_negative_transfer_pairs)
        )
        governed_transfer_ece_pass = bool(
            source_transfer_rows
            and governed_max_target_ece is not None
            and governed_max_target_ece <= float(max_ece)
        )

        baseline_combined_pass = all(
            [
                support_pass,
                variance_pass,
                calibration_pass,
                temporal_pass,
                baseline_transfer_negative_pass,
                baseline_transfer_ece_pass,
            ]
        )
        final_combined_pass = all(
            [
                support_pass,
                variance_pass,
                calibration_pass,
                temporal_pass,
                governed_transfer_negative_pass,
                governed_transfer_ece_pass,
            ]
        )
        fail_count = sum(
            1
            for flag in [
                support_pass,
                variance_pass,
                calibration_pass,
                temporal_pass,
                governed_transfer_negative_pass,
                governed_transfer_ece_pass,
            ]
            if not bool(flag)
        )
        notes = ""
        if (not baseline_combined_pass) and final_combined_pass and governance_mode != "baseline_recommended":
            notes = "final_pass_recovered_by_governance_bridge"
        elif not final_combined_pass:
            notes = "remaining_governance_gap"

        scorecard_rows.append(
            {
                "region": region,
                "dataset": dataset,
                "recommended_model": model_name,
                "f1_mean": f1_mean,
                "f1_std": f1_std,
                "ece_mean": ece_mean,
                "positive_support": int(round(float(positive_support))) if positive_support is not None else None,
                "support_pass": bool(support_pass),
                "variance_pass": bool(variance_pass),
                "calibration_pass": bool(calibration_pass),
                "baseline_out_of_time_delta_f1": baseline_out_of_time_delta_f1,
                "governed_out_of_time_delta_f1": governed_out_of_time_delta_f1,
                "out_of_time_delta_f1": out_of_time_delta_f1,
                "temporal_policy": temporal_policy,
                "temporal_pass": bool(temporal_pass),
                "transfer_pair_count": len(source_transfer_rows),
                "baseline_negative_transfer_pairs": int(baseline_negative_transfer_pairs),
                "baseline_max_target_ece": baseline_max_target_ece,
                "baseline_transfer_negative_pass": bool(baseline_transfer_negative_pass),
                "baseline_transfer_ece_pass": bool(baseline_transfer_ece_pass),
                "governance_mode": governance_mode,
                "governed_negative_transfer_pairs": int(governed_negative_transfer_pairs),
                "governed_max_target_ece": governed_max_target_ece,
                "governed_transfer_negative_pass": bool(governed_transfer_negative_pass),
                "governed_transfer_ece_pass": bool(governed_transfer_ece_pass),
                "baseline_combined_pass": bool(baseline_combined_pass),
                "final_combined_pass": bool(final_combined_pass),
                "risk_level": _risk_level(fail_count),
                "notes": notes,
            }
        )

    high_risk_rows: list[dict[str, Any]] = []
    for row in aggregate_rows:
        ece_mean = _safe_float(row.get("ece_mean"))
        f1_std = _safe_float(row.get("f1_std"))
        f1_mean = _safe_float(row.get("f1_mean"))
        flags: list[str] = []
        if ece_mean is not None and ece_mean > float(max_ece):
            flags.append("ece_high")
        if f1_std is not None and f1_std > float(max_f1_std):
            flags.append("seed_variance_high")
        if f1_mean is not None and f1_mean < 0.50:
            flags.append("f1_low")
        if not flags:
            continue
        high_risk_rows.append(
            {
                "dataset": str(row.get("dataset", "")),
                "model_name": str(row.get("model_name", "")),
                "model_family": str(row.get("model_family", "")),
                "f1_mean": f1_mean,
                "f1_std": f1_std,
                "ece_mean": ece_mean,
                "risk_flags": ",".join(flags),
            }
        )
    high_risk_rows.sort(
        key=lambda row: (
            -len(str(row.get("risk_flags", "")).split(",")),
            -float(_safe_float(row.get("ece_mean")) or 0.0),
            -float(_safe_float(row.get("f1_std")) or 0.0),
            str(row.get("dataset", "")),
            str(row.get("model_name", "")),
        )
    )

    todo_rows = _build_todo_items(
        scorecard_rows=scorecard_rows,
        high_risk_rows=high_risk_rows,
        min_positive_support=int(min_positive_support),
        max_ece=float(max_ece),
        max_f1_std=float(max_f1_std),
        min_out_of_time_delta_f1=float(min_out_of_time_delta_f1),
        max_negative_transfer_pairs=int(max_negative_transfer_pairs),
        transfer_override_seed_stress_test=transfer_override_seed_stress_test,
        manuscript_freeze_packet=manuscript_freeze_packet,
    )

    output_root = Path(output_prefix).resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    summary_md_path = output_root.with_suffix(".md")
    summary_json_path = output_root.with_suffix(".json")
    dataset_scorecard_csv_path = output_root.parent / f"{output_root.name}_dataset_scorecard.csv"
    high_risk_models_csv_path = output_root.parent / f"{output_root.name}_high_risk_models.csv"
    todo_csv_path = output_root.parent / f"{output_root.name}_todo.csv"

    _write_csv(dataset_scorecard_csv_path, scorecard_rows, DATASET_SCORECARD_FIELDS)
    _write_csv(high_risk_models_csv_path, high_risk_rows, HIGH_RISK_MODEL_FIELDS)
    _write_csv(todo_csv_path, todo_rows, TODO_FIELDS)

    baseline_combined_pass_count = sum(1 for row in scorecard_rows if _to_bool(row.get("baseline_combined_pass")))
    final_combined_pass_count = sum(1 for row in scorecard_rows if _to_bool(row.get("final_combined_pass")))
    governance_improved_dataset_count = sum(
        1
        for row in scorecard_rows
        if (not _to_bool(row.get("baseline_combined_pass"))) and _to_bool(row.get("final_combined_pass"))
    )

    high_ece_model_count = sum(
        1 for row in high_risk_rows if "ece_high" in str(row.get("risk_flags", "")).split(",")
    )
    high_variance_model_count = sum(
        1 for row in high_risk_rows if "seed_variance_high" in str(row.get("risk_flags", "")).split(",")
    )

    summary: dict[str, Any] = {
        "status": "completed",
        "recommendation_csv_path": str(Path(recommendation_csv_path).resolve()),
        "aggregate_csv_path": str(Path(aggregate_csv_path).resolve()),
        "out_of_time_csv_path": str(Path(out_of_time_csv_path).resolve()),
        "transfer_csv_path": str(Path(transfer_csv_path).resolve()),
        "multisource_transfer_governance_bridge_json_path": str(governance_bridge_path_resolved)
        if governance_bridge_path_resolved
        else "",
        "transfer_override_seed_stress_test_json_path": str(transfer_override_seed_stress_test_path_resolved)
        if transfer_override_seed_stress_test_path_resolved
        else "",
        "manuscript_freeze_packet_json_path": str(manuscript_freeze_packet_path_resolved)
        if manuscript_freeze_packet_path_resolved
        else "",
        "out_of_time_threshold_policy_compare_json_path": str(out_of_time_policy_compare_path_resolved)
        if out_of_time_policy_compare_path_resolved
        else "",
        "governance_bridge_used": bool(governance_bridge_detail_by_source),
        "transfer_override_seed_stress_test_present": bool(transfer_override_seed_stress_test),
        "manuscript_freeze_packet_present": bool(manuscript_freeze_packet),
        "manuscript_freeze_packet": (
            {
                "status": str(manuscript_freeze_packet.get("status", "")),
                "recommended_model_count": int(
                    _safe_float(manuscript_freeze_packet.get("recommended_model_count")) or 0
                ),
                "recommended_stable_count": int(
                    _safe_float(manuscript_freeze_packet.get("recommended_stable_count")) or 0
                ),
                "appendix_only_count": int(_safe_float(manuscript_freeze_packet.get("appendix_only_count")) or 0),
                "recommended_claim_hygiene_ready": bool(
                    _to_bool(manuscript_freeze_packet.get("recommended_claim_hygiene_ready"))
                ),
                "model_claim_caveat_text": str(manuscript_freeze_packet.get("model_claim_caveat_text", "")),
                "model_claim_scope_csv_path": str(manuscript_freeze_packet.get("model_claim_scope_csv_path", "")),
            }
            if manuscript_freeze_packet
            else {}
        ),
        "dq5_acceptance_met": bool(_dq5_acceptance_met(manuscript_freeze_packet)),
        "transfer_override_seed_stress_test": (
            {
                "status": str(transfer_override_seed_stress_test.get("status", "")),
                "seed_count": int(_safe_float(transfer_override_seed_stress_test.get("seed_count")) or 0),
                "completed_seed_count": int(
                    _safe_float(transfer_override_seed_stress_test.get("completed_seed_count")) or 0
                ),
                "baseline_combined_pass_fixed_count": int(
                    _safe_float(transfer_override_seed_stress_test.get("baseline_combined_pass_fixed_count")) or 0
                ),
                "override_combined_pass_fixed_count": int(
                    _safe_float(transfer_override_seed_stress_test.get("override_combined_pass_fixed_count")) or 0
                ),
                "override_better_transfer_gate_count": int(
                    _safe_float(transfer_override_seed_stress_test.get("override_better_transfer_gate_count")) or 0
                ),
                "dq3_acceptance_met": bool(_to_bool(transfer_override_seed_stress_test.get("dq3_acceptance_met"))),
                "per_seed_csv_path": str(transfer_override_seed_stress_test.get("per_seed_csv_path", "")),
            }
            if transfer_override_seed_stress_test
            else {}
        ),
        "dataset_count": len(scorecard_rows),
        "baseline_combined_pass_count": int(baseline_combined_pass_count),
        "final_combined_pass_count": int(final_combined_pass_count),
        "governance_improved_dataset_count": int(governance_improved_dataset_count),
        "high_risk_model_count": len(high_risk_rows),
        "high_ece_model_count": int(high_ece_model_count),
        "high_variance_model_count": int(high_variance_model_count),
        "todo_count": len(todo_rows),
        "dataset_scorecard_csv_path": str(dataset_scorecard_csv_path),
        "high_risk_models_csv_path": str(high_risk_models_csv_path),
        "todo_csv_path": str(todo_csv_path),
        "dataset_scorecard": scorecard_rows,
        "todo_items": todo_rows,
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
        "config": {
            "min_positive_support": int(min_positive_support),
            "max_ece": float(max_ece),
            "max_f1_std": float(max_f1_std),
            "min_out_of_time_delta_f1": float(min_out_of_time_delta_f1),
            "max_negative_transfer_pairs": int(max_negative_transfer_pairs),
        },
    }

    lines: list[str] = [
        "# Data & Algorithm Quality Review (10-Seed)",
        "",
        "## Configuration",
        "",
        f"- recommendation_csv: `{summary['recommendation_csv_path']}`",
        f"- aggregate_csv: `{summary['aggregate_csv_path']}`",
        f"- out_of_time_csv: `{summary['out_of_time_csv_path']}`",
        f"- transfer_csv: `{summary['transfer_csv_path']}`",
        (
            f"- out_of_time_threshold_policy_compare_json: "
            f"`{summary['out_of_time_threshold_policy_compare_json_path']}`"
            if summary.get("out_of_time_threshold_policy_compare_json_path")
            else "- out_of_time_threshold_policy_compare_json: `(not provided)`"
        ),
        (
            f"- multisource_transfer_governance_bridge_json: "
            f"`{summary['multisource_transfer_governance_bridge_json_path']}`"
            if summary.get("multisource_transfer_governance_bridge_json_path")
            else "- multisource_transfer_governance_bridge_json: `(not provided)`"
        ),
        (
            f"- transfer_override_seed_stress_test_json: "
            f"`{summary['transfer_override_seed_stress_test_json_path']}`"
            if summary.get("transfer_override_seed_stress_test_json_path")
            else "- transfer_override_seed_stress_test_json: `(not provided)`"
        ),
        (
            f"- manuscript_freeze_packet_json: "
            f"`{summary['manuscript_freeze_packet_json_path']}`"
            if summary.get("manuscript_freeze_packet_json_path")
            else "- manuscript_freeze_packet_json: `(not provided)`"
        ),
        "",
        "## Headline Status",
        "",
        f"- baseline combined-pass datasets: `{baseline_combined_pass_count}/{len(scorecard_rows)}`",
        f"- final combined-pass datasets (after governance bridge): `{final_combined_pass_count}/{len(scorecard_rows)}`",
        f"- governance-improved datasets: `{governance_improved_dataset_count}`",
        f"- high-risk model rows: `{len(high_risk_rows)}`",
        f"- DQ-5 acceptance met (claim hygiene): `{summary['dq5_acceptance_met']}`",
        f"- TODO items: `{len(todo_rows)}`",
    ]
    if transfer_override_seed_stress_test:
        lines.extend(
            [
                "",
                "## Transfer Override Seed-Stress Evidence",
                "",
                (
                    f"- completed seeds: "
                    f"`{transfer_override_seed_stress_test.get('completed_seed_count', 'n/a')}/"
                    f"{transfer_override_seed_stress_test.get('seed_count', 'n/a')}`"
                ),
                (
                    f"- baseline fixed combined-pass: "
                    f"`{transfer_override_seed_stress_test.get('baseline_combined_pass_fixed_count', 'n/a')}`"
                ),
                (
                    f"- override fixed combined-pass: "
                    f"`{transfer_override_seed_stress_test.get('override_combined_pass_fixed_count', 'n/a')}`"
                ),
                (
                    f"- override better transfer-gate count: "
                    f"`{transfer_override_seed_stress_test.get('override_better_transfer_gate_count', 'n/a')}`"
                ),
                (
                    f"- DQ-3 acceptance met: "
                    f"`{_to_bool(transfer_override_seed_stress_test.get('dq3_acceptance_met'))}`"
                ),
                (
                    f"- per-seed csv: "
                    f"`{transfer_override_seed_stress_test.get('per_seed_csv_path', '')}`"
                ),
            ]
        )
    if manuscript_freeze_packet:
        freeze = summary.get("manuscript_freeze_packet", {})
        lines.extend(
            [
                "",
                "## Model-Claim Hygiene Freeze Evidence",
                "",
                (
                    f"- recommended stable claims: "
                    f"`{freeze.get('recommended_stable_count', 'n/a')}/"
                    f"{freeze.get('recommended_model_count', 'n/a')}`"
                ),
                f"- appendix-only model rows: `{freeze.get('appendix_only_count', 'n/a')}`",
                f"- recommended_claim_hygiene_ready: `{freeze.get('recommended_claim_hygiene_ready', False)}`",
                f"- DQ-5 acceptance met: `{summary.get('dq5_acceptance_met', False)}`",
                f"- model_claim_scope_csv: `{freeze.get('model_claim_scope_csv_path', '')}`",
                f"- caveat sentence: {freeze.get('model_claim_caveat_text', '')}",
            ]
        )

    lines.extend(
        [
            "",
            "## Dataset Scorecard",
            "",
            "| Region | Recommended | F1±std | ECE | OOT ΔF1 | Transfer neg (base->gov) | Combined pass (base->final) | Risk |",
            "|---|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in scorecard_rows:
        lines.append(
            (
                "| {region} | {model} | {f1}±{std} | {ece} | {delta} | "
                "{base_neg}->{gov_neg} | {base_pass}->{final_pass} | {risk} |"
            ).format(
                region=row.get("region", ""),
                model=row.get("recommended_model", ""),
                f1=_fmt(row.get("f1_mean")),
                std=_fmt(row.get("f1_std")),
                ece=_fmt(row.get("ece_mean")),
                delta=_fmt(row.get("out_of_time_delta_f1")),
                base_neg=row.get("baseline_negative_transfer_pairs", "n/a"),
                gov_neg=row.get("governed_negative_transfer_pairs", "n/a"),
                base_pass="pass" if _to_bool(row.get("baseline_combined_pass")) else "fail",
                final_pass="pass" if _to_bool(row.get("final_combined_pass")) else "fail",
                risk=row.get("risk_level", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Detailed To-Do",
            "",
        ]
    )
    if todo_rows:
        for idx, item in enumerate(todo_rows, start=1):
            lines.extend(
                [
                    f"{idx}. [{item.get('priority', '')}] {item.get('title', '')}",
                    f"   - rationale: {item.get('rationale', '')}",
                    f"   - action: {item.get('action', '')}",
                    f"   - acceptance: {item.get('acceptance_criteria', '')}",
                    f"   - evidence: {item.get('evidence', '')}",
                ]
            )
    else:
        lines.append("1. [P3] No blocking quality issues detected in current configured gates.")

    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- summary_md: `{summary_md_path}`",
            f"- summary_json: `{summary_json_path}`",
            f"- dataset_scorecard_csv: `{dataset_scorecard_csv_path}`",
            f"- high_risk_models_csv: `{high_risk_models_csv_path}`",
            f"- todo_csv: `{todo_csv_path}`",
        ]
    )

    summary_md_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


__all__ = ["run_data_algorithm_quality_review"]
