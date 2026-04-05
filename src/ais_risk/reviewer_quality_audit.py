from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _parse_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


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


def _choose_top_models(aggregate_rows: list[dict[str, str]], top_k: int = 3) -> dict[str, list[dict[str, str]]]:
    by_dataset: dict[str, list[dict[str, str]]] = {}
    for row in aggregate_rows:
        dataset = str(row.get("dataset", ""))
        if not dataset:
            continue
        by_dataset.setdefault(dataset, []).append(row)

    output: dict[str, list[dict[str, str]]] = {}
    for dataset, rows in by_dataset.items():
        rows_sorted = sorted(
            rows,
            key=lambda item: (
                -(_safe_float(item.get("f1_mean")) or -1.0),
                (_safe_float(item.get("ece_mean")) or 999.0),
                str(item.get("model_name", "")),
            ),
        )
        output[dataset] = rows_sorted[:top_k]
    return output


def _region_from_dataset(dataset: str) -> str:
    return dataset.replace("_pooled_pairwise", "")


def run_reviewer_quality_audit(
    recommendation_csv_path: str | Path,
    aggregate_csv_path: str | Path,
    winner_summary_csv_path: str | Path,
    out_of_time_csv_path: str | Path,
    transfer_csv_path: str | Path,
    reliability_region_summary_csv_path: str | Path,
    taxonomy_region_summary_csv_path: str | Path,
    output_prefix: str | Path,
    significance_csv_path: str | Path | None = None,
    threshold_robustness_summary_csv_path: str | Path | None = None,
    unseen_area_summary_csv_path: str | Path | None = None,
    manuscript_freeze_packet_json_path: str | Path | None = None,
    transfer_model_scan_json_path: str | Path | None = None,
    transfer_gap_summary_csv_path: str | Path | None = None,
    temporal_robust_summary_json_path: str | Path | None = None,
    out_of_time_threshold_policy_compare_json_path: str | Path | None = None,
    transfer_policy_governance_lock_json_path: str | Path | None = None,
    transfer_policy_compare_json_path: str | Path | None = None,
    transfer_policy_compare_all_models_json_path: str | Path | None = None,
    transfer_calibration_probe_json_path: str | Path | None = None,
    external_validity_manuscript_assets_json_path: str | Path | None = None,
    multisource_transfer_model_scan_summary_json_path: str | Path | None = None,
    multisource_transfer_governance_bridge_json_path: str | Path | None = None,
    data_algorithm_quality_review_json_path: str | Path | None = None,
) -> dict[str, Any]:
    recommendation_rows = _parse_csv_rows(recommendation_csv_path)
    aggregate_rows = _parse_csv_rows(aggregate_csv_path)
    winner_rows = _parse_csv_rows(winner_summary_csv_path)
    oot_rows = _parse_csv_rows(out_of_time_csv_path)
    transfer_rows = _parse_csv_rows(transfer_csv_path)
    reliability_rows = _parse_csv_rows(reliability_region_summary_csv_path)
    taxonomy_rows = _parse_csv_rows(taxonomy_region_summary_csv_path)
    significance_rows: list[dict[str, str]] = []
    threshold_robustness_rows: list[dict[str, str]] = []
    unseen_area_summary_rows: list[dict[str, str]] = []
    manuscript_freeze_packet: dict[str, Any] = {}
    transfer_model_scan: dict[str, Any] = {}
    transfer_model_scan_rows: list[dict[str, str]] = []
    transfer_gap_summary_rows: list[dict[str, str]] = []
    temporal_robust_summary: dict[str, Any] = {}
    out_of_time_threshold_policy_compare: dict[str, Any] = {}
    transfer_policy_governance_lock: dict[str, Any] = {}
    transfer_policy_compare: dict[str, Any] = {}
    transfer_policy_compare_all_models: dict[str, Any] = {}
    transfer_calibration_probe: dict[str, Any] = {}
    external_validity_manuscript_assets: dict[str, Any] = {}
    multisource_transfer_model_scan_summary: dict[str, Any] = {}
    multisource_transfer_governance_bridge: dict[str, Any] = {}
    data_algorithm_quality_review: dict[str, Any] = {}
    significance_path_resolved = Path(significance_csv_path).resolve() if significance_csv_path else None
    threshold_robustness_path_resolved = (
        Path(threshold_robustness_summary_csv_path).resolve() if threshold_robustness_summary_csv_path else None
    )
    unseen_area_summary_path_resolved = Path(unseen_area_summary_csv_path).resolve() if unseen_area_summary_csv_path else None
    manuscript_freeze_packet_path_resolved = (
        Path(manuscript_freeze_packet_json_path).resolve() if manuscript_freeze_packet_json_path else None
    )
    transfer_model_scan_path_resolved = Path(transfer_model_scan_json_path).resolve() if transfer_model_scan_json_path else None
    transfer_gap_summary_path_resolved = Path(transfer_gap_summary_csv_path).resolve() if transfer_gap_summary_csv_path else None
    temporal_robust_summary_path_resolved = (
        Path(temporal_robust_summary_json_path).resolve() if temporal_robust_summary_json_path else None
    )
    out_of_time_threshold_policy_compare_path_resolved = (
        Path(out_of_time_threshold_policy_compare_json_path).resolve()
        if out_of_time_threshold_policy_compare_json_path
        else None
    )
    transfer_policy_governance_lock_path_resolved = (
        Path(transfer_policy_governance_lock_json_path).resolve() if transfer_policy_governance_lock_json_path else None
    )
    transfer_policy_compare_path_resolved = (
        Path(transfer_policy_compare_json_path).resolve() if transfer_policy_compare_json_path else None
    )
    transfer_policy_compare_all_models_path_resolved = (
        Path(transfer_policy_compare_all_models_json_path).resolve()
        if transfer_policy_compare_all_models_json_path
        else None
    )
    transfer_calibration_probe_path_resolved = (
        Path(transfer_calibration_probe_json_path).resolve() if transfer_calibration_probe_json_path else None
    )
    external_validity_manuscript_assets_path_resolved = (
        Path(external_validity_manuscript_assets_json_path).resolve()
        if external_validity_manuscript_assets_json_path
        else None
    )
    multisource_transfer_model_scan_summary_path_resolved = (
        Path(multisource_transfer_model_scan_summary_json_path).resolve()
        if multisource_transfer_model_scan_summary_json_path
        else None
    )
    multisource_transfer_governance_bridge_path_resolved = (
        Path(multisource_transfer_governance_bridge_json_path).resolve()
        if multisource_transfer_governance_bridge_json_path
        else None
    )
    data_algorithm_quality_review_path_resolved = (
        Path(data_algorithm_quality_review_json_path).resolve()
        if data_algorithm_quality_review_json_path
        else None
    )
    if significance_path_resolved and significance_path_resolved.exists():
        significance_rows = _parse_csv_rows(significance_path_resolved)
    if threshold_robustness_path_resolved and threshold_robustness_path_resolved.exists():
        threshold_robustness_rows = _parse_csv_rows(threshold_robustness_path_resolved)
    if unseen_area_summary_path_resolved and unseen_area_summary_path_resolved.exists():
        unseen_area_summary_rows = _parse_csv_rows(unseen_area_summary_path_resolved)
    if manuscript_freeze_packet_path_resolved and manuscript_freeze_packet_path_resolved.exists():
        manuscript_freeze_packet = json.loads(manuscript_freeze_packet_path_resolved.read_text(encoding="utf-8"))
    if transfer_model_scan_path_resolved and transfer_model_scan_path_resolved.exists():
        transfer_model_scan = json.loads(transfer_model_scan_path_resolved.read_text(encoding="utf-8"))
        model_summary_csv_path = transfer_model_scan.get("model_summary_csv_path")
        if model_summary_csv_path and Path(model_summary_csv_path).exists():
            transfer_model_scan_rows = _parse_csv_rows(Path(model_summary_csv_path))
    if transfer_gap_summary_path_resolved and transfer_gap_summary_path_resolved.exists():
        transfer_gap_summary_rows = _parse_csv_rows(transfer_gap_summary_path_resolved)
    if temporal_robust_summary_path_resolved and temporal_robust_summary_path_resolved.exists():
        temporal_robust_summary = json.loads(temporal_robust_summary_path_resolved.read_text(encoding="utf-8"))
    if (
        out_of_time_threshold_policy_compare_path_resolved
        and out_of_time_threshold_policy_compare_path_resolved.exists()
    ):
        out_of_time_threshold_policy_compare = json.loads(
            out_of_time_threshold_policy_compare_path_resolved.read_text(encoding="utf-8")
        )
    if transfer_policy_governance_lock_path_resolved and transfer_policy_governance_lock_path_resolved.exists():
        transfer_policy_governance_lock = json.loads(
            transfer_policy_governance_lock_path_resolved.read_text(encoding="utf-8")
        )
    if transfer_policy_compare_path_resolved and transfer_policy_compare_path_resolved.exists():
        transfer_policy_compare = json.loads(transfer_policy_compare_path_resolved.read_text(encoding="utf-8"))
    if transfer_policy_compare_all_models_path_resolved and transfer_policy_compare_all_models_path_resolved.exists():
        transfer_policy_compare_all_models = json.loads(
            transfer_policy_compare_all_models_path_resolved.read_text(encoding="utf-8")
        )
    if transfer_calibration_probe_path_resolved and transfer_calibration_probe_path_resolved.exists():
        transfer_calibration_probe = json.loads(transfer_calibration_probe_path_resolved.read_text(encoding="utf-8"))
    if external_validity_manuscript_assets_path_resolved and external_validity_manuscript_assets_path_resolved.exists():
        external_validity_manuscript_assets = json.loads(
            external_validity_manuscript_assets_path_resolved.read_text(encoding="utf-8")
        )
    if (
        multisource_transfer_model_scan_summary_path_resolved
        and multisource_transfer_model_scan_summary_path_resolved.exists()
    ):
        multisource_transfer_model_scan_summary = json.loads(
            multisource_transfer_model_scan_summary_path_resolved.read_text(encoding="utf-8")
        )
    if (
        multisource_transfer_governance_bridge_path_resolved
        and multisource_transfer_governance_bridge_path_resolved.exists()
    ):
        multisource_transfer_governance_bridge = json.loads(
            multisource_transfer_governance_bridge_path_resolved.read_text(encoding="utf-8")
        )
    if data_algorithm_quality_review_path_resolved and data_algorithm_quality_review_path_resolved.exists():
        data_algorithm_quality_review = json.loads(
            data_algorithm_quality_review_path_resolved.read_text(encoding="utf-8")
        )

    top_models = _choose_top_models(aggregate_rows, top_k=3)

    gate_all_enabled = all(str(row.get("ece_gate_enabled", "")).lower() == "true" for row in recommendation_rows)
    gate_values = [_safe_float(row.get("ece_gate_max")) for row in recommendation_rows]
    gate_threshold = min([value for value in gate_values if value is not None], default=None)

    oot_negative_regions = []
    for row in oot_rows:
        delta_f1 = _safe_float(row.get("delta_f1"))
        if delta_f1 is not None and delta_f1 < 0:
            oot_negative_regions.append(
                {
                    "region": str(row.get("region", "")),
                    "model_name": str(row.get("model_name", "") or row.get("recommended_model", "")),
                    "delta_f1": float(delta_f1),
                    "delta_ece": float(_safe_float(row.get("delta_ece")) or 0.0),
                }
            )

    transfer_negative_pairs = []
    for row in transfer_rows:
        delta_f1 = _safe_float(row.get("delta_f1"))
        if delta_f1 is not None and delta_f1 < 0:
            transfer_negative_pairs.append(
                {
                    "source_region": str(row.get("source_region", "")),
                    "target_region": str(row.get("target_region", "")),
                    "model_name": str(row.get("model_name", "") or row.get("recommended_model", "")),
                    "delta_f1": float(delta_f1),
                }
            )

    high_variance_candidates = []
    for row in aggregate_rows:
        f1_std = _safe_float(row.get("f1_std"))
        if f1_std is None:
            continue
        if f1_std >= 0.03:
            high_variance_candidates.append(
                {
                    "dataset": str(row.get("dataset", "")),
                    "model_name": str(row.get("model_name", "")),
                    "f1_std": float(f1_std),
                    "ece_mean": float(_safe_float(row.get("ece_mean")) or 0.0),
                }
            )

    positive_support_by_region: dict[str, int] = {}
    for row in reliability_rows:
        region = str(row.get("region", ""))
        sample_count = int(_safe_float(row.get("sample_count")) or 0)
        positive_rate = float(_safe_float(row.get("positive_rate")) or 0.0)
        positive_support_by_region[region] = int(round(sample_count * positive_rate))

    fp_fn_by_region: dict[str, dict[str, int]] = {}
    for row in taxonomy_rows:
        region = str(row.get("region", ""))
        fp_fn_by_region[region] = {
            "fp": int(_safe_float(row.get("fp")) or 0),
            "fn": int(_safe_float(row.get("fn")) or 0),
        }

    output_root = Path(output_prefix).resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = output_root.with_suffix(".json")
    summary_md_path = output_root.with_suffix(".md")

    summary: dict[str, Any] = {
        "status": "completed",
        "recommendation_csv_path": str(Path(recommendation_csv_path).resolve()),
        "aggregate_csv_path": str(Path(aggregate_csv_path).resolve()),
        "winner_summary_csv_path": str(Path(winner_summary_csv_path).resolve()),
        "out_of_time_csv_path": str(Path(out_of_time_csv_path).resolve()),
        "transfer_csv_path": str(Path(transfer_csv_path).resolve()),
        "reliability_region_summary_csv_path": str(Path(reliability_region_summary_csv_path).resolve()),
        "taxonomy_region_summary_csv_path": str(Path(taxonomy_region_summary_csv_path).resolve()),
        "recommendation_count": len(recommendation_rows),
        "calibration_gate_enabled_for_all": gate_all_enabled,
        "calibration_gate_threshold": gate_threshold,
        "oot_negative_regions": oot_negative_regions,
        "transfer_negative_pairs": transfer_negative_pairs,
        "high_variance_candidates": high_variance_candidates,
        "positive_support_by_region": positive_support_by_region,
        "fp_fn_by_region": fp_fn_by_region,
        "significance_csv_path": str(significance_path_resolved) if significance_path_resolved else "",
        "significance_rows": len(significance_rows),
        "threshold_robustness_summary_csv_path": str(threshold_robustness_path_resolved) if threshold_robustness_path_resolved else "",
        "threshold_robustness_rows": len(threshold_robustness_rows),
        "unseen_area_summary_csv_path": str(unseen_area_summary_path_resolved) if unseen_area_summary_path_resolved else "",
        "unseen_area_summary_rows": len(unseen_area_summary_rows),
        "manuscript_freeze_packet_json_path": str(manuscript_freeze_packet_path_resolved)
        if manuscript_freeze_packet_path_resolved
        else "",
        "manuscript_freeze_packet_present": bool(manuscript_freeze_packet),
        "transfer_model_scan_json_path": str(transfer_model_scan_path_resolved) if transfer_model_scan_path_resolved else "",
        "transfer_model_scan_present": bool(transfer_model_scan),
        "transfer_gap_summary_csv_path": str(transfer_gap_summary_path_resolved) if transfer_gap_summary_path_resolved else "",
        "transfer_gap_summary_present": bool(transfer_gap_summary_rows),
        "temporal_robust_summary_json_path": str(temporal_robust_summary_path_resolved)
        if temporal_robust_summary_path_resolved
        else "",
        "temporal_robust_summary_present": bool(temporal_robust_summary),
        "out_of_time_threshold_policy_compare_json_path": str(out_of_time_threshold_policy_compare_path_resolved)
        if out_of_time_threshold_policy_compare_path_resolved
        else "",
        "out_of_time_threshold_policy_compare_present": bool(out_of_time_threshold_policy_compare),
        "transfer_policy_governance_lock_json_path": str(transfer_policy_governance_lock_path_resolved)
        if transfer_policy_governance_lock_path_resolved
        else "",
        "transfer_policy_governance_lock_present": bool(transfer_policy_governance_lock),
        "transfer_policy_compare_json_path": str(transfer_policy_compare_path_resolved)
        if transfer_policy_compare_path_resolved
        else "",
        "transfer_policy_compare_present": bool(transfer_policy_compare),
        "transfer_policy_compare_all_models_json_path": str(transfer_policy_compare_all_models_path_resolved)
        if transfer_policy_compare_all_models_path_resolved
        else "",
        "transfer_policy_compare_all_models_present": bool(transfer_policy_compare_all_models),
        "transfer_calibration_probe_json_path": str(transfer_calibration_probe_path_resolved)
        if transfer_calibration_probe_path_resolved
        else "",
        "transfer_calibration_probe_present": bool(transfer_calibration_probe),
        "external_validity_manuscript_assets_json_path": str(external_validity_manuscript_assets_path_resolved)
        if external_validity_manuscript_assets_path_resolved
        else "",
        "external_validity_manuscript_assets_present": bool(external_validity_manuscript_assets),
        "external_validity_manuscript_assets": (
            {
                "status": str(external_validity_manuscript_assets.get("status", "")),
                "transfer_direction_count": int(
                    _safe_float(external_validity_manuscript_assets.get("transfer_direction_count")) or 0
                ),
                "scenario_panel_count": int(
                    _safe_float(external_validity_manuscript_assets.get("scenario_panel_count")) or 0
                ),
                "transfer_uncertainty_table_md_path": str(
                    external_validity_manuscript_assets.get("transfer_uncertainty_table_md_path", "")
                ),
                "scenario_panels_md_path": str(external_validity_manuscript_assets.get("scenario_panels_md_path", "")),
                "integration_note_md_path": str(
                    external_validity_manuscript_assets.get("integration_note_md_path", "")
                ),
            }
            if external_validity_manuscript_assets
            else {}
        ),
        "multisource_transfer_model_scan_summary_json_path": str(multisource_transfer_model_scan_summary_path_resolved)
        if multisource_transfer_model_scan_summary_path_resolved
        else "",
        "multisource_transfer_model_scan_summary_present": bool(multisource_transfer_model_scan_summary),
        "multisource_transfer_model_scan_summary": (
            {
                "status": str(multisource_transfer_model_scan_summary.get("status", "")),
                "source_count": int(_safe_float(multisource_transfer_model_scan_summary.get("source_count")) or 0),
                "recommended_combined_pass_count": int(
                    _safe_float(multisource_transfer_model_scan_summary.get("recommended_combined_pass_count")) or 0
                ),
                "best_combined_pass_count": int(
                    _safe_float(multisource_transfer_model_scan_summary.get("best_combined_pass_count")) or 0
                ),
                "recommendation_mismatch_count": int(
                    _safe_float(multisource_transfer_model_scan_summary.get("recommendation_mismatch_count")) or 0
                ),
                "source_summary_csv_path": str(
                    multisource_transfer_model_scan_summary.get("source_summary_csv_path", "")
                ),
                "detail_csv_path": str(multisource_transfer_model_scan_summary.get("detail_csv_path", "")),
            }
            if multisource_transfer_model_scan_summary
            else {}
        ),
        "multisource_transfer_governance_bridge_json_path": str(
            multisource_transfer_governance_bridge_path_resolved
        )
        if multisource_transfer_governance_bridge_path_resolved
        else "",
        "multisource_transfer_governance_bridge_present": bool(multisource_transfer_governance_bridge),
        "multisource_transfer_governance_bridge": (
            {
                "status": str(multisource_transfer_governance_bridge.get("status", "")),
                "source_count": int(_safe_float(multisource_transfer_governance_bridge.get("source_count")) or 0),
                "baseline_combined_pass_count": int(
                    _safe_float(multisource_transfer_governance_bridge.get("baseline_combined_pass_count")) or 0
                ),
                "governed_combined_pass_count": int(
                    _safe_float(multisource_transfer_governance_bridge.get("governed_combined_pass_count")) or 0
                ),
                "improved_source_count": int(
                    _safe_float(multisource_transfer_governance_bridge.get("improved_source_count")) or 0
                ),
                "detail_csv_path": str(multisource_transfer_governance_bridge.get("detail_csv_path", "")),
            }
            if multisource_transfer_governance_bridge
            else {}
        ),
        "data_algorithm_quality_review_json_path": str(data_algorithm_quality_review_path_resolved)
        if data_algorithm_quality_review_path_resolved
        else "",
        "data_algorithm_quality_review_present": bool(data_algorithm_quality_review),
        "data_algorithm_quality_review": (
            {
                "status": str(data_algorithm_quality_review.get("status", "")),
                "dataset_count": int(_safe_float(data_algorithm_quality_review.get("dataset_count")) or 0),
                "baseline_combined_pass_count": int(
                    _safe_float(data_algorithm_quality_review.get("baseline_combined_pass_count")) or 0
                ),
                "final_combined_pass_count": int(
                    _safe_float(data_algorithm_quality_review.get("final_combined_pass_count")) or 0
                ),
                "governance_improved_dataset_count": int(
                    _safe_float(data_algorithm_quality_review.get("governance_improved_dataset_count")) or 0
                ),
                "high_risk_model_count": int(
                    _safe_float(data_algorithm_quality_review.get("high_risk_model_count")) or 0
                ),
                "todo_count": int(_safe_float(data_algorithm_quality_review.get("todo_count")) or 0),
                "dq5_acceptance_met": bool(_to_bool(data_algorithm_quality_review.get("dq5_acceptance_met"))),
                "dataset_scorecard_csv_path": str(data_algorithm_quality_review.get("dataset_scorecard_csv_path", "")),
                "high_risk_models_csv_path": str(data_algorithm_quality_review.get("high_risk_models_csv_path", "")),
                "todo_csv_path": str(data_algorithm_quality_review.get("todo_csv_path", "")),
                "transfer_override_seed_stress_test_present": bool(
                    data_algorithm_quality_review.get("transfer_override_seed_stress_test_present")
                ),
                "transfer_override_seed_stress_test_json_path": str(
                    data_algorithm_quality_review.get("transfer_override_seed_stress_test_json_path", "")
                ),
                "manuscript_freeze_packet_present": bool(
                    data_algorithm_quality_review.get("manuscript_freeze_packet_present")
                ),
                "manuscript_freeze_packet_json_path": str(
                    data_algorithm_quality_review.get("manuscript_freeze_packet_json_path", "")
                ),
                "manuscript_freeze_packet": (
                    {
                        "status": str(
                            data_algorithm_quality_review.get("manuscript_freeze_packet", {}).get("status", "")
                        ),
                        "recommended_model_count": int(
                            _safe_float(
                                data_algorithm_quality_review.get("manuscript_freeze_packet", {}).get(
                                    "recommended_model_count"
                                )
                            )
                            or 0
                        ),
                        "recommended_stable_count": int(
                            _safe_float(
                                data_algorithm_quality_review.get("manuscript_freeze_packet", {}).get(
                                    "recommended_stable_count"
                                )
                            )
                            or 0
                        ),
                        "appendix_only_count": int(
                            _safe_float(
                                data_algorithm_quality_review.get("manuscript_freeze_packet", {}).get(
                                    "appendix_only_count"
                                )
                            )
                            or 0
                        ),
                        "recommended_claim_hygiene_ready": bool(
                            _to_bool(
                                data_algorithm_quality_review.get("manuscript_freeze_packet", {}).get(
                                    "recommended_claim_hygiene_ready"
                                )
                            )
                        ),
                        "model_claim_scope_csv_path": str(
                            data_algorithm_quality_review.get("manuscript_freeze_packet", {}).get(
                                "model_claim_scope_csv_path", ""
                            )
                        ),
                        "model_claim_caveat_text": str(
                            data_algorithm_quality_review.get("manuscript_freeze_packet", {}).get(
                                "model_claim_caveat_text", ""
                            )
                        ),
                    }
                    if isinstance(data_algorithm_quality_review.get("manuscript_freeze_packet"), dict)
                    else {}
                ),
                "transfer_override_seed_stress_test": (
                    {
                        "status": str(
                            data_algorithm_quality_review.get("transfer_override_seed_stress_test", {}).get(
                                "status", ""
                            )
                        ),
                        "seed_count": int(
                            _safe_float(
                                data_algorithm_quality_review.get("transfer_override_seed_stress_test", {}).get(
                                    "seed_count"
                                )
                            )
                            or 0
                        ),
                        "completed_seed_count": int(
                            _safe_float(
                                data_algorithm_quality_review.get("transfer_override_seed_stress_test", {}).get(
                                    "completed_seed_count"
                                )
                            )
                            or 0
                        ),
                        "override_better_transfer_gate_count": int(
                            _safe_float(
                                data_algorithm_quality_review.get("transfer_override_seed_stress_test", {}).get(
                                    "override_better_transfer_gate_count"
                                )
                            )
                            or 0
                        ),
                        "dq3_acceptance_met": bool(
                            _to_bool(
                                data_algorithm_quality_review.get("transfer_override_seed_stress_test", {}).get(
                                    "dq3_acceptance_met"
                                )
                            )
                        ),
                        "per_seed_csv_path": str(
                            data_algorithm_quality_review.get("transfer_override_seed_stress_test", {}).get(
                                "per_seed_csv_path", ""
                            )
                        ),
                    }
                    if isinstance(data_algorithm_quality_review.get("transfer_override_seed_stress_test"), dict)
                    else {}
                ),
            }
            if data_algorithm_quality_review
            else {}
        ),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }

    lines = [
        "# Reviewer Quality Audit (10-Seed Expanded Models)",
        "",
        "## Scope",
        "",
        f"- recommendation_csv: `{summary['recommendation_csv_path']}`",
        f"- aggregate_csv: `{summary['aggregate_csv_path']}`",
        f"- winner_summary_csv: `{summary['winner_summary_csv_path']}`",
        f"- out_of_time_csv: `{summary['out_of_time_csv_path']}`",
        f"- transfer_csv: `{summary['transfer_csv_path']}`",
        f"- reliability_csv: `{summary['reliability_region_summary_csv_path']}`",
        f"- taxonomy_csv: `{summary['taxonomy_region_summary_csv_path']}`",
        (
            f"- unseen_area_summary_csv: `{summary['unseen_area_summary_csv_path']}`"
            if summary.get("unseen_area_summary_csv_path")
            else "- unseen_area_summary_csv: `(not provided)`"
        ),
        (
            f"- manuscript_freeze_packet_json: `{summary['manuscript_freeze_packet_json_path']}`"
            if summary.get("manuscript_freeze_packet_json_path")
            else "- manuscript_freeze_packet_json: `(not provided)`"
        ),
        (
            f"- transfer_model_scan_json: `{summary['transfer_model_scan_json_path']}`"
            if summary.get("transfer_model_scan_json_path")
            else "- transfer_model_scan_json: `(not provided)`"
        ),
        (
            f"- transfer_gap_summary_csv: `{summary['transfer_gap_summary_csv_path']}`"
            if summary.get("transfer_gap_summary_csv_path")
            else "- transfer_gap_summary_csv: `(not provided)`"
        ),
        (
            f"- temporal_robust_summary_json: `{summary['temporal_robust_summary_json_path']}`"
            if summary.get("temporal_robust_summary_json_path")
            else "- temporal_robust_summary_json: `(not provided)`"
        ),
        (
            f"- out_of_time_threshold_policy_compare_json: "
            f"`{summary['out_of_time_threshold_policy_compare_json_path']}`"
            if summary.get("out_of_time_threshold_policy_compare_json_path")
            else "- out_of_time_threshold_policy_compare_json: `(not provided)`"
        ),
        (
            f"- transfer_policy_governance_lock_json: "
            f"`{summary['transfer_policy_governance_lock_json_path']}`"
            if summary.get("transfer_policy_governance_lock_json_path")
            else "- transfer_policy_governance_lock_json: `(not provided)`"
        ),
        (
            f"- transfer_policy_compare_json: `{summary['transfer_policy_compare_json_path']}`"
            if summary.get("transfer_policy_compare_json_path")
            else "- transfer_policy_compare_json: `(not provided)`"
        ),
        (
            f"- transfer_policy_compare_all_models_json: `{summary['transfer_policy_compare_all_models_json_path']}`"
            if summary.get("transfer_policy_compare_all_models_json_path")
            else "- transfer_policy_compare_all_models_json: `(not provided)`"
        ),
        (
            f"- transfer_calibration_probe_json: `{summary['transfer_calibration_probe_json_path']}`"
            if summary.get("transfer_calibration_probe_json_path")
            else "- transfer_calibration_probe_json: `(not provided)`"
        ),
        (
            f"- external_validity_manuscript_assets_json: `{summary['external_validity_manuscript_assets_json_path']}`"
            if summary.get("external_validity_manuscript_assets_json_path")
            else "- external_validity_manuscript_assets_json: `(not provided)`"
        ),
        (
            f"- multisource_transfer_model_scan_summary_json: "
            f"`{summary['multisource_transfer_model_scan_summary_json_path']}`"
            if summary.get("multisource_transfer_model_scan_summary_json_path")
            else "- multisource_transfer_model_scan_summary_json: `(not provided)`"
        ),
        (
            f"- multisource_transfer_governance_bridge_json: "
            f"`{summary['multisource_transfer_governance_bridge_json_path']}`"
            if summary.get("multisource_transfer_governance_bridge_json_path")
            else "- multisource_transfer_governance_bridge_json: `(not provided)`"
        ),
        (
            f"- data_algorithm_quality_review_json: "
            f"`{summary['data_algorithm_quality_review_json_path']}`"
            if summary.get("data_algorithm_quality_review_json_path")
            else "- data_algorithm_quality_review_json: `(not provided)`"
        ),
        "",
        "## Recommendation Snapshot",
        "",
        "| Region | Dataset | Model | Family | F1 mean±std | ECE mean±std | Gate |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in recommendation_rows:
        dataset = str(row.get("dataset", ""))
        lines.append(
            "| {region} | {dataset} | {model} | {family} | {f1m}±{f1s} | {ecem}±{eces} | {gate} |".format(
                region=_region_from_dataset(dataset),
                dataset=dataset,
                model=row.get("model_name", ""),
                family=row.get("model_family", ""),
                f1m=_fmt(row.get("f1_mean")),
                f1s=_fmt(row.get("f1_std")),
                ecem=_fmt(row.get("ece_mean")),
                eces=_fmt(row.get("ece_std")),
                gate=row.get("gate_status", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Examiner Findings",
            "",
            "1. Calibration governance is active.",
            f"Calibration gate enabled for all regions: `{gate_all_enabled}` (threshold=`{_fmt(gate_threshold)}`)",
            "",
            "2. Out-of-time drift remains region-dependent.",
            f"- negative-ΔF1 regions: `{len(oot_negative_regions)}`",
        ]
    )
    for item in sorted(oot_negative_regions, key=lambda payload: payload["delta_f1"]):
        lines.append(
            f"- {item['region']}: model `{item['model_name']}`, ΔF1 `{item['delta_f1']:.4f}`, ΔECE `{item['delta_ece']:.4f}`"
        )

    lines.extend(
        [
            "",
            "3. Cross-region transfer still shows substantial degradation on multiple directions.",
            f"- negative transfer pairs: `{len(transfer_negative_pairs)}` / `{len(transfer_rows)}`",
        ]
    )
    for item in sorted(transfer_negative_pairs, key=lambda payload: payload["delta_f1"])[:6]:
        lines.append(
            f"- {item['source_region']} -> {item['target_region']}: `{item['model_name']}` ΔF1 `{item['delta_f1']:.4f}`"
        )

    lines.extend(
        [
            "",
            "4. Seed variance outliers are concentrated in neural/CNN candidates.",
            f"- high variance candidates (F1 std>=0.03): `{len(high_variance_candidates)}`",
        ]
    )
    for item in sorted(high_variance_candidates, key=lambda payload: payload["f1_std"], reverse=True)[:8]:
        lines.append(
            f"- {item['dataset']} / {item['model_name']}: F1 std `{item['f1_std']:.4f}`, ECE mean `{item['ece_mean']:.4f}`"
        )

    lines.extend(
        [
            "",
            "5. Error taxonomy indicates region-specific FN pressure that should be addressed in discussion.",
            "",
            "| Region | Positive Support (approx) | FP | FN |",
            "|---|---:|---:|---:|",
        ]
    )
    for region in sorted(set(list(positive_support_by_region.keys()) + list(fp_fn_by_region.keys()))):
        support = positive_support_by_region.get(region, 0)
        fp = fp_fn_by_region.get(region, {}).get("fp", 0)
        fn = fp_fn_by_region.get(region, {}).get("fn", 0)
        lines.append(f"| {region} | {support} | {fp} | {fn} |")

    if significance_rows:
        f1_ci_true = sum(1 for row in significance_rows if str(row.get("f1_rec_better_ci", "")).lower() == "true")
        ece_ci_true = sum(1 for row in significance_rows if str(row.get("ece_rec_lower_ci", "")).lower() == "true")
        lines.extend(
            [
                "",
                "## Significance Addendum",
                "",
                f"- source: `{significance_path_resolved}`",
                f"- datasets with `F1 rec>cmp (CI)=True`: `{f1_ci_true}/{len(significance_rows)}`",
                f"- datasets with `ECE rec<cmp (CI)=True`: `{ece_ci_true}/{len(significance_rows)}`",
            ]
        )
    if threshold_robustness_rows:
        nonzero_regret_profiles = [
            row for row in threshold_robustness_rows if (_safe_float(row.get("mean_regret")) or 0.0) > 0.0
        ]
        worst = sorted(
            nonzero_regret_profiles,
            key=lambda row: float(_safe_float(row.get("mean_regret")) or 0.0),
            reverse=True,
        )[:3]
        lines.extend(
            [
                "",
                "## Threshold-Robustness Addendum",
                "",
                f"- source: `{threshold_robustness_path_resolved}`",
                f"- non-zero regret profiles: `{len(nonzero_regret_profiles)}/{len(threshold_robustness_rows)}`",
            ]
        )
        for row in worst:
            lines.append(
                "- {dataset}/{profile}: mean_regret `{regret}` (mean_rec_th `{rec_th}` vs mean_best_th `{best_th}`)".format(
                    dataset=row.get("dataset", ""),
                    profile=row.get("profile", ""),
                    regret=_fmt(row.get("mean_regret"), digits=3),
                    rec_th=_fmt(row.get("mean_recommended_threshold")),
                    best_th=_fmt(row.get("mean_best_threshold")),
                )
            )
    if unseen_area_summary_rows:
        unseen = unseen_area_summary_rows[0]
        low_support_count = int(_safe_float(unseen.get("true_area_low_support_count")) or 0)
        low_support_splits = str(unseen.get("low_support_region_splits", "")).strip()
        transfer_negative = int(_safe_float(unseen.get("transfer_negative_delta_count")) or 0)
        transfer_rows_total = int(_safe_float(unseen.get("transfer_row_count")) or 0)
        transfer_region_count = int(_safe_float(unseen.get("transfer_region_count")) or 0)
        supported_split_count = int(_safe_float(unseen.get("true_area_supported_split_count")) or 0)
        total_split_count = int(_safe_float(unseen.get("true_area_split_count")) or 0)
        lines.extend(
            [
                "",
                "## True Unseen-Area Addendum",
                "",
                f"- source: `{unseen_area_summary_path_resolved}`",
                f"- supported true-area splits: `{supported_split_count}/{total_split_count}`",
                f"- low-support true-area splits: `{low_support_count}` ({low_support_splits if low_support_splits else 'none'})",
                (
                    f"- own_ship hgbt F1 range: `{_fmt(unseen.get('own_ship_hgbt_f1_min'))}"
                    f" - {_fmt(unseen.get('own_ship_hgbt_f1_max'))}`"
                ),
                (
                    f"- transfer negative-ΔF1 pairs: `{transfer_negative}/{transfer_rows_total}`"
                ),
                f"- transfer harbor coverage: `{transfer_region_count}` regions",
            ]
        )

    freeze_has_unseen_claim = bool(manuscript_freeze_packet.get("unseen_claim_text"))
    freeze_has_threshold_lock = int(_safe_float(manuscript_freeze_packet.get("profile_lock_count")) or 0) > 0
    freeze_has_caption = bool(manuscript_freeze_packet.get("caption_addendum_text"))
    if manuscript_freeze_packet:
        lines.extend(
            [
                "",
                "## Manuscript Freeze Addendum",
                "",
                f"- source: `{manuscript_freeze_packet_path_resolved}`",
                f"- operator profile lock rows: `{manuscript_freeze_packet.get('profile_lock_count', 0)}`",
                f"- max locked mean regret: `{_fmt(manuscript_freeze_packet.get('max_locked_mean_regret'), digits=3)}`",
            ]
        )

    if transfer_model_scan:
        recommended_model = str(transfer_model_scan.get("recommended_model", "")).strip()
        recommended_row = None
        for row in transfer_model_scan_rows:
            if str(row.get("model_name", "")).strip() == recommended_model:
                recommended_row = row
                break
        lines.extend(
            [
                "",
                "## Transfer-Model-Scan Addendum",
                "",
                f"- source: `{transfer_model_scan_path_resolved}`",
                f"- source_region: `{transfer_model_scan.get('source_region', '')}`",
                f"- recommended_model_under_scan_rule: `{recommended_model or 'n/a'}`",
                f"- selection_rule: `{transfer_model_scan.get('selection_rule', '')}`",
            ]
        )
        if recommended_row:
            lines.extend(
                [
                    (
                        "- recommended model summary: min target F1 `{min_f1}`, mean target F1 `{mean_f1}`, "
                        "max target ECE `{max_ece}`"
                    ).format(
                        min_f1=_fmt(recommended_row.get("min_target_f1")),
                        mean_f1=_fmt(recommended_row.get("mean_target_f1")),
                        max_ece=_fmt(recommended_row.get("max_target_ece")),
                    ),
                ]
            )

    if multisource_transfer_model_scan_summary:
        lines.extend(
            [
                "",
                "## Multi-Source Transfer-Model-Scan Addendum",
                "",
                f"- source: `{multisource_transfer_model_scan_summary_path_resolved}`",
                (
                    f"- recommended combined-pass sources: "
                    f"`{multisource_transfer_model_scan_summary.get('recommended_combined_pass_count', 'n/a')}/"
                    f"{multisource_transfer_model_scan_summary.get('source_count', 'n/a')}`"
                ),
                (
                    f"- best combined-pass sources: "
                    f"`{multisource_transfer_model_scan_summary.get('best_combined_pass_count', 'n/a')}/"
                    f"{multisource_transfer_model_scan_summary.get('source_count', 'n/a')}`"
                ),
                (
                    f"- recommendation mismatch count (recommended vs best-combined model): "
                    f"`{multisource_transfer_model_scan_summary.get('recommendation_mismatch_count', 'n/a')}`"
                ),
                (
                    f"- source summary csv: "
                    f"`{multisource_transfer_model_scan_summary.get('source_summary_csv_path', '')}`"
                ),
            ]
        )

    if multisource_transfer_governance_bridge:
        lines.extend(
            [
                "",
                "## Multi-Source Transfer Governance-Bridge Addendum",
                "",
                f"- source: `{multisource_transfer_governance_bridge_path_resolved}`",
                (
                    f"- baseline combined-pass sources: "
                    f"`{multisource_transfer_governance_bridge.get('baseline_combined_pass_count', 'n/a')}/"
                    f"{multisource_transfer_governance_bridge.get('source_count', 'n/a')}`"
                ),
                (
                    f"- governed combined-pass sources: "
                    f"`{multisource_transfer_governance_bridge.get('governed_combined_pass_count', 'n/a')}/"
                    f"{multisource_transfer_governance_bridge.get('source_count', 'n/a')}`"
                ),
                (
                    f"- improved source count after governance bridge: "
                    f"`{multisource_transfer_governance_bridge.get('improved_source_count', 'n/a')}`"
                ),
                (
                    f"- governed detail csv: "
                    f"`{multisource_transfer_governance_bridge.get('detail_csv_path', '')}`"
                ),
            ]
        )

    if data_algorithm_quality_review:
        lines.extend(
            [
                "",
                "## Data-Algorithm Quality-Review Addendum",
                "",
                f"- source: `{data_algorithm_quality_review_path_resolved}`",
                (
                    f"- baseline combined-pass datasets: "
                    f"`{data_algorithm_quality_review.get('baseline_combined_pass_count', 'n/a')}/"
                    f"{data_algorithm_quality_review.get('dataset_count', 'n/a')}`"
                ),
                (
                    f"- final combined-pass datasets: "
                    f"`{data_algorithm_quality_review.get('final_combined_pass_count', 'n/a')}/"
                    f"{data_algorithm_quality_review.get('dataset_count', 'n/a')}`"
                ),
                (
                    f"- governance-improved datasets: "
                    f"`{data_algorithm_quality_review.get('governance_improved_dataset_count', 'n/a')}`"
                ),
                (
                    f"- high-risk model rows: "
                    f"`{data_algorithm_quality_review.get('high_risk_model_count', 'n/a')}`"
                ),
                (
                    f"- todo rows: "
                    f"`{data_algorithm_quality_review.get('todo_count', 'n/a')}`"
                ),
                (
                    f"- DQ-5 acceptance met: "
                    f"`{_to_bool(data_algorithm_quality_review.get('dq5_acceptance_met'))}`"
                ),
                (
                    f"- dataset scorecard csv: "
                    f"`{data_algorithm_quality_review.get('dataset_scorecard_csv_path', '')}`"
                ),
                (
                    f"- high-risk models csv: "
                    f"`{data_algorithm_quality_review.get('high_risk_models_csv_path', '')}`"
                ),
                (
                    f"- todo csv: "
                    f"`{data_algorithm_quality_review.get('todo_csv_path', '')}`"
                ),
                (
                    f"- transfer override seed-stress json: "
                    f"`{data_algorithm_quality_review.get('transfer_override_seed_stress_test_json_path', '')}`"
                ),
                (
                    f"- manuscript freeze packet json: "
                    f"`{data_algorithm_quality_review.get('manuscript_freeze_packet_json_path', '')}`"
                ),
            ]
        )
        stress = data_algorithm_quality_review.get("transfer_override_seed_stress_test", {})
        if isinstance(stress, dict) and stress:
            lines.extend(
                [
                    (
                        f"- transfer override seeds completed: "
                        f"`{stress.get('completed_seed_count', 'n/a')}/{stress.get('seed_count', 'n/a')}`"
                    ),
                    (
                        f"- transfer-gate improved seed count: "
                        f"`{stress.get('override_better_transfer_gate_count', 'n/a')}`"
                    ),
                    (
                        f"- DQ-3 acceptance met: "
                        f"`{_to_bool(stress.get('dq3_acceptance_met'))}`"
                    ),
                    (
                        f"- transfer override per-seed csv: "
                        f"`{stress.get('per_seed_csv_path', '')}`"
                    ),
                ]
            )
        freeze = data_algorithm_quality_review.get("manuscript_freeze_packet", {})
        if isinstance(freeze, dict) and freeze:
            lines.extend(
                [
                    (
                        f"- model-claim stable recommendations: "
                        f"`{freeze.get('recommended_stable_count', 'n/a')}/"
                        f"{freeze.get('recommended_model_count', 'n/a')}`"
                    ),
                    (
                        f"- model-claim appendix-only rows: "
                        f"`{freeze.get('appendix_only_count', 'n/a')}`"
                    ),
                    (
                        f"- model-claim hygiene ready: "
                        f"`{_to_bool(freeze.get('recommended_claim_hygiene_ready'))}`"
                    ),
                    (
                        f"- model-claim scope csv: "
                        f"`{freeze.get('model_claim_scope_csv_path', '')}`"
                    ),
                    (
                        f"- model-claim caveat sentence: "
                        f"{freeze.get('model_claim_caveat_text', '')}"
                    ),
                ]
            )

    if transfer_gap_summary_rows:
        gap = transfer_gap_summary_rows[0]
        lines.extend(
            [
                "",
                "## Transfer-Gap Diagnostics Addendum",
                "",
                f"- source: `{transfer_gap_summary_path_resolved}`",
                f"- negative ΔF1 pairs (fixed threshold): `{gap.get('negative_delta_pair_count', 'n/a')}`",
                f"- negative ΔF1 pairs with CI upper<0: `{gap.get('negative_delta_ci_pair_count', 'n/a')}`",
                f"- pairs with target retune gain >=0.05 F1: `{gap.get('pairs_with_target_retune_gain_ge_0_05', 'n/a')}`",
                (
                    f"- max target retune gain pair: `{gap.get('max_target_retune_gain_pair', '')}` "
                    f"(`{_fmt(gap.get('max_target_retune_gain'))}`)"
                ),
            ]
        )

    if temporal_robust_summary:
        lines.extend(
            [
                "",
                "## Temporal-Robustness Addendum",
                "",
                f"- source: `{temporal_robust_summary_path_resolved}`",
                (
                    f"- recommendation changed datasets: "
                    f"`{temporal_robust_summary.get('changed_recommendation_count', 'n/a')}/"
                    f"{temporal_robust_summary.get('dataset_count', 'n/a')}`"
                ),
                (
                    f"- temporal target pass(current->robust): "
                    f"`{temporal_robust_summary.get('current_temporal_target_pass_count', 'n/a')} -> "
                    f"{temporal_robust_summary.get('robust_temporal_target_pass_count', 'n/a')}`"
                ),
                (
                    f"- temporal target feasible datasets(any/ece-pass): "
                    f"`{temporal_robust_summary.get('temporal_target_feasible_any_model_count', 'n/a')} / "
                    f"{temporal_robust_summary.get('temporal_target_feasible_with_ece_gate_count', 'n/a')}`"
                ),
                (
                    f"- best observed out-of-time ΔF1 (any/ece-pass): "
                    f"`{_fmt(temporal_robust_summary.get('best_observed_out_of_time_delta_f1_mean_any_model'))} / "
                    f"{_fmt(temporal_robust_summary.get('best_observed_out_of_time_delta_f1_mean_ece_pass_model'))}`"
                ),
                (
                    f"- max robust in-time regression from best F1: "
                    f"`{_fmt(temporal_robust_summary.get('max_robust_in_time_regression_from_best_f1'))}`"
                ),
            ]
        )

    if out_of_time_threshold_policy_compare:
        policy_rows = list(out_of_time_threshold_policy_compare.get("policies", []))
        houston_rows = list(out_of_time_threshold_policy_compare.get("houston_rows", []))
        lines.extend(
            [
                "",
                "## Out-of-Time Threshold-Policy Addendum",
                "",
                f"- source: `{out_of_time_threshold_policy_compare_path_resolved}`",
                f"- compared policies: `{len(policy_rows)}`",
                (
                    f"- recommended policy (excluding oracle): "
                    f"`{out_of_time_threshold_policy_compare.get('recommended_policy_excluding_oracle', 'n/a')}`"
                ),
                (
                    f"- temporal gate threshold: "
                    f"`{_fmt(out_of_time_threshold_policy_compare.get('min_out_of_time_delta_f1'))}`"
                ),
            ]
        )
        for row in policy_rows:
            lines.append(
                (
                    "- {policy}: combined pass `{combined}/{total}`, "
                    "temporal pass `{temporal}/{total}`, mean ΔF1 `{delta}`, max OOT ECE `{ece}`"
                ).format(
                    policy=row.get("policy", ""),
                    combined=row.get("combined_pass_count", "n/a"),
                    temporal=row.get("temporal_pass_count", "n/a"),
                    total=row.get("completed_count", "n/a"),
                    delta=_fmt(row.get("mean_delta_f1")),
                    ece=_fmt(row.get("max_out_of_time_ece")),
                )
            )
        houston_fixed = next(
            (
                row
                for row in houston_rows
                if str(row.get("policy", "")) == "fixed_baseline_threshold"
                and str(row.get("status", "")) == "completed"
            ),
            None,
        )
        houston_val = next(
            (
                row
                for row in houston_rows
                if str(row.get("policy", "")) == "oot_val_tuned"
                and str(row.get("status", "")) == "completed"
            ),
            None,
        )
        if houston_val and houston_fixed:
            lines.append(
                (
                    "- houston(hgbt) ΔF1 val-tuned->fixed-baseline: "
                    "`{vdelta}->{fdelta}` (combined pass: `{vpass}->{fpass}`)"
                ).format(
                    vdelta=_fmt(houston_val.get("delta_f1")),
                    fdelta=_fmt(houston_fixed.get("delta_f1")),
                    vpass="yes" if bool(houston_val.get("combined_pass")) else "no",
                    fpass="yes" if bool(houston_fixed.get("combined_pass")) else "no",
                )
            )

    if transfer_policy_governance_lock:
        lines.extend(
            [
                "",
                "## Transfer-Policy Governance-Lock Addendum",
                "",
                f"- source: `{transfer_policy_governance_lock_path_resolved}`",
                (
                    f"- selected transfer override: "
                    f"`{transfer_policy_governance_lock.get('selected_transfer_model', 'n/a')}/"
                    f"{transfer_policy_governance_lock.get('selected_transfer_method', 'n/a')}`"
                ),
                (
                    f"- baseline->projected negative pairs (global): "
                    f"`{transfer_policy_governance_lock.get('baseline_negative_pairs_global', 'n/a')}->"
                    f"{transfer_policy_governance_lock.get('projected_negative_pairs_global', 'n/a')}`"
                ),
                (
                    f"- baseline->projected negative pairs (source): "
                    f"`{transfer_policy_governance_lock.get('baseline_negative_pairs_source', 'n/a')}->"
                    f"{transfer_policy_governance_lock.get('projected_negative_pairs_source', 'n/a')}`"
                ),
                (
                    f"- out-of-time policy pass: "
                    f"`{transfer_policy_governance_lock.get('out_of_time_policy_pass', 'n/a')}`"
                ),
                (
                    f"- transfer policy pass: "
                    f"`{transfer_policy_governance_lock.get('transfer_policy_pass', 'n/a')}`"
                ),
                (
                    f"- governance ready for lock: "
                    f"`{transfer_policy_governance_lock.get('governance_ready_for_lock', 'n/a')}`"
                ),
                (
                    f"- policy lock csv: "
                    f"`{transfer_policy_governance_lock.get('policy_lock_csv_path', '')}`"
                ),
                (
                    f"- projected transfer csv: "
                    f"`{transfer_policy_governance_lock.get('projected_transfer_check_csv_path', '')}`"
                ),
            ]
        )

    if transfer_policy_compare:
        policy_rows = list(transfer_policy_compare.get("rows", []))
        lines.extend(
            [
                "",
                "## Transfer-Policy-Compare Addendum",
                "",
                f"- source: `{transfer_policy_compare_path_resolved}`",
                f"- compared shortlist models: `{len(policy_rows)}`",
            ]
        )
        for row in policy_rows:
            lines.append(
                (
                    "- {model}: negative pairs fixed->retuned `{fixed}->{retuned}` "
                    "(mean retune gain `{gain}`)"
                ).format(
                    model=row.get("model_name", ""),
                    fixed=row.get("negative_fixed_count", "n/a"),
                    retuned=row.get("negative_retuned_count", "n/a"),
                    gain=_fmt(row.get("mean_retune_gain_f1")),
                )
            )

    if transfer_policy_compare_all_models:
        policy_all_rows = list(transfer_policy_compare_all_models.get("rows", []))
        zero_negative_retuned = [
            str(row.get("model_name", ""))
            for row in policy_all_rows
            if int(_safe_float(row.get("negative_retuned_count")) or 0) == 0
        ]
        lines.extend(
            [
                "",
                "## Transfer-Policy-Compare (All Models) Addendum",
                "",
                f"- source: `{transfer_policy_compare_all_models_path_resolved}`",
                f"- compared models: `{len(policy_all_rows)}`",
                (
                    f"- models with zero negative pairs after retune: "
                    f"`{', '.join(sorted(zero_negative_retuned)) if zero_negative_retuned else 'none'}`"
                ),
            ]
        )
        for row in policy_all_rows:
            lines.append(
                (
                    "- {model}: pair_count `{pairs}`, negative fixed->retuned `{fixed}->{retuned}`, "
                    "mean ΔF1 fixed->retuned `{fixed_delta}->{retuned_delta}`"
                ).format(
                    model=row.get("model_name", ""),
                    pairs=row.get("pair_count", "n/a"),
                    fixed=row.get("negative_fixed_count", "n/a"),
                    retuned=row.get("negative_retuned_count", "n/a"),
                    fixed_delta=_fmt(row.get("mean_delta_f1_fixed")),
                    retuned_delta=_fmt(row.get("mean_delta_f1_retuned")),
                )
            )

    if transfer_calibration_probe:
        top_fixed = list(transfer_calibration_probe.get("top_combined_pass_fixed", []))
        top_retuned = list(transfer_calibration_probe.get("top_combined_pass_retuned", []))
        lines.extend(
            [
                "",
                "## Transfer-Calibration Probe Addendum",
                "",
                f"- source: `{transfer_calibration_probe_path_resolved}`",
                (
                    f"- combined-pass count (fixed/retuned): "
                    f"`{transfer_calibration_probe.get('combined_pass_fixed_count', 'n/a')} / "
                    f"{transfer_calibration_probe.get('combined_pass_retuned_count', 'n/a')}`"
                ),
                (
                    f"- methods scanned: "
                    f"`{', '.join(transfer_calibration_probe.get('methods', []))}`"
                ),
            ]
        )
        if top_fixed:
            best = top_fixed[0]
            lines.append(
                (
                    "- best fixed candidate: `{model}/{method}` "
                    "(mean ΔF1 fixed `{delta}`, max target ECE `{ece}`)"
                ).format(
                    model=best.get("model_name", ""),
                    method=best.get("method", ""),
                    delta=_fmt(best.get("mean_delta_f1_fixed")),
                    ece=_fmt(best.get("max_target_ece")),
                )
            )
        if top_retuned:
            best = top_retuned[0]
            lines.append(
                (
                    "- best retuned candidate: `{model}/{method}` "
                    "(mean ΔF1 retuned `{delta}`, max target ECE `{ece}`)"
                ).format(
                    model=best.get("model_name", ""),
                    method=best.get("method", ""),
                    delta=_fmt(best.get("mean_delta_f1_retuned")),
                    ece=_fmt(best.get("max_target_ece")),
                )
            )

    if external_validity_manuscript_assets:
        lines.extend(
            [
                "",
                "## External-Validity Manuscript-Assets Addendum",
                "",
                f"- source: `{external_validity_manuscript_assets_path_resolved}`",
                (
                    f"- transfer uncertainty directions covered: "
                    f"`{external_validity_manuscript_assets.get('transfer_direction_count', 'n/a')}`"
                ),
                (
                    f"- scenario panels generated: "
                    f"`{external_validity_manuscript_assets.get('scenario_panel_count', 'n/a')}`"
                ),
                (
                    f"- transfer table md: "
                    f"`{external_validity_manuscript_assets.get('transfer_uncertainty_table_md_path', '')}`"
                ),
                (
                    f"- scenario panel md: "
                    f"`{external_validity_manuscript_assets.get('scenario_panels_md_path', '')}`"
                ),
                (
                    f"- integration note md: "
                    f"`{external_validity_manuscript_assets.get('integration_note_md_path', '')}`"
                ),
            ]
        )

    todo_item_1 = "1. Add true unseen-area evidence (outside current same-ecosystem region set)."
    if freeze_has_unseen_claim:
        todo_item_1 = (
            "1. [Closed] Frozen unseen-area evidence statement prepared in manuscript freeze packet "
            f"(`{manuscript_freeze_packet_path_resolved}`)."
        )
    elif unseen_area_summary_rows:
        unseen = unseen_area_summary_rows[0]
        low_support_count = int(_safe_float(unseen.get("true_area_low_support_count")) or 0)
        transfer_region_count = int(_safe_float(unseen.get("transfer_region_count")) or 0)
        low_support_splits = [
            token.strip() for token in str(unseen.get("low_support_region_splits", "")).split(",") if token.strip()
        ]
        low_support_priority = ",".join(low_support_splits) if low_support_splits else "remaining low-support splits"
        if low_support_count > 0 and transfer_region_count < 3:
            todo_item_1 = (
                "1. Increase low-support true-area splits and add one more independent harbor "
                "before final camera-ready claim locking."
            )
        elif low_support_count > 0:
            todo_item_1 = (
                "1. Raise positive support for remaining low-support true-area splits "
                f"(priority: {low_support_priority}) while keeping current multi-harbor transfer evidence."
            )
        else:
            todo_item_1 = (
                "1. Freeze unseen-area evidence statement and cite support-threshold policy "
                "explicitly in the manuscript."
            )

    lines.extend(
        [
            "",
            "## Priority TODO (Examiner View)",
            "",
            todo_item_1,
            (
                "2. [Closed] Operator cost profile lock is frozen in manuscript freeze packet."
                if freeze_has_threshold_lock
                else (
                    "2. Add threshold-policy robustness table under operator cost scenarios (FP-heavy vs FN-heavy)."
                    if not threshold_robustness_rows
                    else "2. Lock one operator cost profile per region and freeze threshold policy text in manuscript."
                )
            ),
            (
                "3. [Closed] Significance one-line caption addendum is frozen in manuscript freeze packet."
                if freeze_has_caption
                else (
                    "3. Add significance notes for top-model deltas (bootstrap CI or paired test) in main table."
                    if not significance_rows
                    else "3. Integrate significance appendix link and one-line interpretation into main result table caption."
                )
            ),
            "",
            "## Top-3 Models Per Dataset (10-seed aggregate)",
            "",
        ]
    )
    for dataset in sorted(top_models.keys()):
        lines.append(f"### {dataset}")
        lines.append("")
        lines.append("| Model | F1 mean±std (CI95) | ECE mean±std |")
        lines.append("|---|---:|---:|")
        for row in top_models[dataset]:
            lines.append(
                "| {model} | {f1m}±{f1s} ({f1ci}) | {ecem}±{eces} |".format(
                    model=row.get("model_name", ""),
                    f1m=_fmt(row.get("f1_mean")),
                    f1s=_fmt(row.get("f1_std")),
                    f1ci=_fmt(row.get("f1_ci95")),
                    ecem=_fmt(row.get("ece_mean")),
                    eces=_fmt(row.get("ece_std")),
                )
            )
        lines.append("")

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary
