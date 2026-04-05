from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .focus_seed_compare import run_focus_seed_compare_bundle
from .own_ship_quality_gate import (
    apply_own_ship_quality_gate,
    build_own_ship_quality_gate_summary,
    save_own_ship_quality_gate_outputs,
)
from .workflow import run_ingestion_workflow


def _parse_mmsi_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    unique: list[str] = []
    seen: set[str] = set()
    for item in values:
        mmsi = str(item).strip()
        if not mmsi or mmsi in seen:
            continue
        unique.append(mmsi)
        seen.add(mmsi)
    return unique


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except Exception:
        return None


def _fmt(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _fmt_delta(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.{digits}f}"


def _bool_str(value: bool) -> str:
    return "yes" if bool(value) else "no"


def _load_candidate_rows(path_value: str | Path) -> list[dict[str, str]]:
    path = Path(path_value)
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    if not rows:
        return []
    rows.sort(key=lambda row: (_safe_int(row.get("rank")) or 999999, str(row.get("mmsi", ""))))
    return rows


def _select_focus_candidate_rows(
    candidate_rows: list[dict[str, str]],
    start_rank: int,
    select_count: int,
) -> list[dict[str, str]]:
    if not candidate_rows:
        return []
    start_index = max(0, int(start_rank) - 1)
    target_count = max(1, int(select_count))
    ordered = candidate_rows[start_index:] + candidate_rows[:start_index]
    selected: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in ordered:
        mmsi = str(row.get("mmsi") or "").strip()
        if not mmsi or mmsi in seen:
            continue
        selected.append(row)
        seen.add(mmsi)
        if len(selected) >= target_count:
            break
    return selected


def _sort_candidate_rows_by_rank(candidate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        candidate_rows,
        key=lambda row: (_safe_int(row.get("rank")) or 999999, str(row.get("mmsi", ""))),
    )


def _write_selected_focus_mmsis_csv(
    path_value: str | Path,
    focus_mmsis: list[str],
    selection_mode: str,
    selected_candidate_rows: list[dict[str, str]],
) -> None:
    path = Path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate_by_mmsi = {
        str(row.get("mmsi") or "").strip(): row
        for row in selected_candidate_rows
        if str(row.get("mmsi") or "").strip()
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "selection_order",
            "selection_mode",
            "mmsi",
            "source_rank",
            "candidate_score",
            "recommended_timestamp",
            "reason_summary",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, mmsi in enumerate(focus_mmsis, start=1):
            candidate = candidate_by_mmsi.get(mmsi, {})
            writer.writerow(
                {
                    "selection_order": index,
                    "selection_mode": selection_mode,
                    "mmsi": mmsi,
                    "source_rank": _safe_int(candidate.get("rank")),
                    "candidate_score": _safe_float(candidate.get("candidate_score")),
                    "recommended_timestamp": candidate.get("recommended_timestamp", ""),
                    "reason_summary": candidate.get("reason_summary", ""),
                }
            )


def _resolve_auto_select_workflow_output_dir(
    prefix: Path,
    auto_select_workflow_output_dir: str | Path | None,
) -> Path:
    if auto_select_workflow_output_dir is None:
        return prefix.with_name(f"{prefix.name}_auto_focus_workflow")
    requested = Path(auto_select_workflow_output_dir)
    if str(requested).strip() == "outputs/focus_seed_pipeline/auto_focus_workflow":
        return prefix.with_name(f"{prefix.name}_auto_focus_workflow")
    return requested


def _sort_gate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            1 if bool(row.get("gate_passed", False)) else 0,
            _safe_float(row.get("mean_aggregate_score")) or -999.0,
            _safe_float(row.get("mean_delta_case_f1_mean")) or -999.0,
            -(_safe_float(row.get("std_delta_case_f1_mean")) or 999.0),
            str(row.get("modelset_key", "")),
        ),
        reverse=True,
    )


def _build_validation_gate(
    aggregate_rows: list[dict[str, Any]],
    min_seed_count: int,
    min_mean_aggregate_score: float,
    min_delta_case_f1_mean: float,
    max_delta_case_f1_std: float,
    max_delta_repeat_std_mean: float,
    max_delta_calibration_ece: float,
    require_calibration_metric: bool,
    allow_focus_tilt: bool,
    allow_mixed: bool,
) -> dict[str, Any]:
    gate_rows: list[dict[str, Any]] = []
    for row in aggregate_rows:
        robustness_label = str(row.get("robustness_label") or "")
        seed_count = _safe_int(row.get("seed_count")) or 0
        mean_aggregate_score = _safe_float(row.get("mean_aggregate_score"))
        mean_delta_case_f1_mean = _safe_float(row.get("mean_delta_case_f1_mean"))
        std_delta_case_f1_mean = _safe_float(row.get("std_delta_case_f1_mean"))
        mean_delta_repeat_std_mean = _safe_float(row.get("mean_delta_repeat_std_mean"))
        mean_delta_calibration_ece = _safe_float(row.get("mean_delta_calibration_ece"))

        fail_reasons: list[str] = []
        if seed_count < int(min_seed_count):
            fail_reasons.append(f"seed_count<{int(min_seed_count)}")
        if robustness_label == "focus_robust":
            pass
        elif robustness_label == "focus_tilt" and bool(allow_focus_tilt):
            pass
        elif robustness_label == "mixed" and bool(allow_mixed):
            pass
        else:
            fail_reasons.append(f"robustness={robustness_label or 'unknown'}")
        if mean_aggregate_score is None or mean_aggregate_score < float(min_mean_aggregate_score):
            fail_reasons.append(f"mean_score<{float(min_mean_aggregate_score):.4f}")
        if mean_delta_case_f1_mean is None or mean_delta_case_f1_mean < float(min_delta_case_f1_mean):
            fail_reasons.append(f"mean_delta_case_f1<{float(min_delta_case_f1_mean):.4f}")
        if std_delta_case_f1_mean is None or std_delta_case_f1_mean > float(max_delta_case_f1_std):
            fail_reasons.append(f"std_delta_case_f1>{float(max_delta_case_f1_std):.4f}")
        if mean_delta_repeat_std_mean is None or mean_delta_repeat_std_mean > float(max_delta_repeat_std_mean):
            fail_reasons.append(f"mean_delta_repeat_std>{float(max_delta_repeat_std_mean):.4f}")
        if mean_delta_calibration_ece is None:
            if bool(require_calibration_metric):
                fail_reasons.append("missing_delta_calibration_ece")
        elif mean_delta_calibration_ece > float(max_delta_calibration_ece):
            fail_reasons.append(f"mean_delta_calibration_ece>{float(max_delta_calibration_ece):.4f}")

        gate_rows.append(
            {
                "modelset_key": row.get("modelset_key"),
                "seed_count": seed_count,
                "robustness_label": robustness_label,
                "mean_aggregate_score": mean_aggregate_score,
                "mean_delta_case_f1_mean": mean_delta_case_f1_mean,
                "std_delta_case_f1_mean": std_delta_case_f1_mean,
                "mean_delta_repeat_std_mean": mean_delta_repeat_std_mean,
                "mean_delta_calibration_ece": mean_delta_calibration_ece,
                "gate_passed": len(fail_reasons) == 0,
                "fail_reasons": fail_reasons,
                "fail_reason_text": "; ".join(fail_reasons),
            }
        )

    gate_rows = _sort_gate_rows(gate_rows)
    passed_rows = [row for row in gate_rows if bool(row.get("gate_passed", False))]
    recommended_row: dict[str, Any] | None = None
    recommendation_basis = "no_modelset"
    overall_decision = "fail"
    if passed_rows:
        recommended_row = passed_rows[0]
        recommendation_basis = "best_passed_modelset"
        overall_decision = "pass"
    elif gate_rows:
        recommended_row = gate_rows[0]
        recommendation_basis = "best_available_fallback"
    return {
        "overall_decision": overall_decision,
        "passed_modelset_count": len(passed_rows),
        "total_modelset_count": len(gate_rows),
        "recommended_modelset_key": (recommended_row or {}).get("modelset_key"),
        "recommendation_basis": recommendation_basis,
        "gate_rows": gate_rows,
    }


def _write_gate_rows_csv(path_value: str | Path, gate_rows: list[dict[str, Any]]) -> None:
    path = Path(path_value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "modelset_key",
            "seed_count",
            "robustness_label",
            "mean_aggregate_score",
            "mean_delta_case_f1_mean",
            "std_delta_case_f1_mean",
            "mean_delta_repeat_std_mean",
            "mean_delta_calibration_ece",
            "gate_passed",
            "fail_reason_text",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in gate_rows:
            writer.writerow(
                {
                    "modelset_key": row.get("modelset_key"),
                    "seed_count": row.get("seed_count"),
                    "robustness_label": row.get("robustness_label"),
                    "mean_aggregate_score": row.get("mean_aggregate_score"),
                    "mean_delta_case_f1_mean": row.get("mean_delta_case_f1_mean"),
                    "std_delta_case_f1_mean": row.get("std_delta_case_f1_mean"),
                    "mean_delta_repeat_std_mean": row.get("mean_delta_repeat_std_mean"),
                    "mean_delta_calibration_ece": row.get("mean_delta_calibration_ece"),
                    "gate_passed": row.get("gate_passed"),
                    "fail_reason_text": row.get("fail_reason_text", ""),
                }
            )


def build_focus_seed_pipeline_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Focus Seed Pipeline Summary",
        "",
        "## Inputs",
        "",
        f"- manifest_path: `{summary.get('manifest_path', 'n/a')}`",
        f"- raw_input_path: `{summary.get('raw_input_path', 'n/a')}`",
        f"- focus_mmsi_resolution_mode: `{summary.get('focus_mmsi_resolution_mode', 'n/a')}`",
        f"- requested_focus_mmsis: `{summary.get('requested_focus_mmsis', [])}`",
        f"- focus_own_ship_mmsis: `{summary.get('focus_own_ship_mmsis', [])}`",
        f"- seed_values: `{summary.get('seed_values', [])}`",
        f"- benchmark_modelsets: `{summary.get('benchmark_modelsets', [])}`",
        f"- run_count: `{summary.get('run_count', 0)}`",
        "",
        "## Auto Candidate Selection",
        "",
        f"- auto_select_focus_mmsis: `{summary.get('auto_select_focus_mmsis', False)}`",
        f"- auto_select_count: `{summary.get('auto_select_count', 'n/a')}`",
        f"- auto_select_start_rank: `{summary.get('auto_select_start_rank', 'n/a')}`",
        f"- auto_workflow_summary_json_path: `{summary.get('auto_workflow_summary_json_path', 'n/a')}`",
        f"- auto_workflow_candidates_path: `{summary.get('auto_workflow_candidates_path', 'n/a')}`",
        "",
        "## Auto Candidate Quality Gate",
        "",
        f"- auto_candidate_quality_gate_applied: `{summary.get('auto_candidate_quality_gate_applied', False)}`",
        f"- auto_candidate_quality_gate_strict: `{summary.get('auto_candidate_quality_gate_strict', False)}`",
        f"- auto_candidate_quality_gate_passed_count: `{summary.get('auto_candidate_quality_gate_passed_count', 0)}` / `{summary.get('auto_candidate_quality_gate_candidate_count', 0)}`",
        f"- auto_candidate_quality_gate_fallback_used: `{summary.get('auto_candidate_quality_gate_fallback_used', False)}`",
        f"- auto_candidate_quality_gate_summary_json_path: `{summary.get('auto_candidate_quality_gate_summary_json_path', 'n/a')}`",
        f"- auto_candidate_quality_gate_summary_md_path: `{summary.get('auto_candidate_quality_gate_summary_md_path', 'n/a')}`",
        f"- auto_candidate_quality_gate_rows_csv_path: `{summary.get('auto_candidate_quality_gate_rows_csv_path', 'n/a')}`",
        "",
        "## Outputs",
        "",
        f"- selected_focus_mmsis_csv_path: `{summary.get('selected_focus_mmsis_csv_path', 'n/a')}`",
        f"- focus_seed_compare_summary_json_path: `{summary.get('focus_seed_compare_summary_json_path', 'n/a')}`",
        f"- focus_seed_compare_summary_md_path: `{summary.get('focus_seed_compare_summary_md_path', 'n/a')}`",
        f"- validation_gate_rows_csv_path: `{summary.get('validation_gate_rows_csv_path', 'n/a')}`",
        "",
        "## Validation Gate",
        "",
        f"- gate_overall_decision: `{summary.get('validation_gate_overall_decision', 'n/a')}`",
        f"- passed_modelset_count: `{summary.get('validation_gate_passed_modelset_count', 0)}` / `{summary.get('validation_gate_total_modelset_count', 0)}`",
        f"- recommended_modelset_key: `{summary.get('validation_gate_recommended_modelset_key', 'n/a')}`",
        f"- recommendation_basis: `{summary.get('validation_gate_recommendation_basis', 'n/a')}`",
        f"- min_seed_count: `{summary.get('validation_gate_min_seed_count', 'n/a')}`",
        f"- min_mean_aggregate_score: `{summary.get('validation_gate_min_mean_aggregate_score', 'n/a')}`",
        f"- min_delta_case_f1_mean: `{summary.get('validation_gate_min_delta_case_f1_mean', 'n/a')}`",
        f"- max_delta_case_f1_std: `{summary.get('validation_gate_max_delta_case_f1_std', 'n/a')}`",
        f"- max_delta_repeat_std_mean: `{summary.get('validation_gate_max_delta_repeat_std_mean', 'n/a')}`",
        f"- max_delta_calibration_ece: `{summary.get('validation_gate_max_delta_calibration_ece', 'n/a')}`",
        f"- require_calibration_metric: `{summary.get('validation_gate_require_calibration_metric', False)}`",
        f"- allow_focus_tilt: `{summary.get('validation_gate_allow_focus_tilt', False)}`",
        f"- allow_mixed: `{summary.get('validation_gate_allow_mixed', False)}`",
        "",
        "## Modelset Aggregate",
        "",
        "| Modelset | Seed Count | Focus-Favor Count | Baseline-Favor Count | Mixed Count | Mean Score | Mean Delta Case F1 | Mean Delta Cal ECE | Robustness Label |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("aggregate_by_modelset", []):
        lines.append(
            "| {modelset} | {seed_count} | {focus_favor} | {baseline_favor} | {mixed} | {mean_score} | {mean_case} | {mean_ece} | {robustness} |".format(
                modelset=row.get("modelset_key", "unknown"),
                seed_count=row.get("seed_count", 0),
                focus_favor=row.get("focus_favor_count", 0),
                baseline_favor=row.get("baseline_favor_count", 0),
                mixed=row.get("mixed_count", 0),
                mean_score=_fmt(_safe_float(row.get("mean_aggregate_score"))),
                mean_case=_fmt_delta(_safe_float(row.get("mean_delta_case_f1_mean"))),
                mean_ece=_fmt_delta(_safe_float(row.get("mean_delta_calibration_ece"))),
                robustness=row.get("robustness_label", "n/a"),
            )
        )
    lines.extend(
        [
            "",
            "## Validation Gate Rows",
            "",
            "| Modelset | Gate Passed | Seed Count | Robustness | Mean Score | Mean Delta Case F1 | Std Delta Case F1 | Mean Delta Repeat Std | Mean Delta Cal ECE | Fail Reasons |",
            "|---|---|---:|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in summary.get("validation_gate_rows", []):
        lines.append(
            "| {modelset} | {passed} | {seed_count} | {robustness} | {mean_score} | {mean_case} | {std_case} | {mean_repeat_std} | {mean_ece} | {reasons} |".format(
                modelset=row.get("modelset_key", "unknown"),
                passed=_bool_str(bool(row.get("gate_passed", False))),
                seed_count=row.get("seed_count", 0),
                robustness=row.get("robustness_label", "n/a"),
                mean_score=_fmt(_safe_float(row.get("mean_aggregate_score"))),
                mean_case=_fmt_delta(_safe_float(row.get("mean_delta_case_f1_mean"))),
                std_case=_fmt(_safe_float(row.get("std_delta_case_f1_mean"))),
                mean_repeat_std=_fmt_delta(_safe_float(row.get("mean_delta_repeat_std_mean"))),
                mean_ece=_fmt_delta(_safe_float(row.get("mean_delta_calibration_ece"))),
                reasons=row.get("fail_reason_text", "") or "-",
            )
        )
    lines.append("")
    return "\n".join(lines)


def run_focus_seed_pipeline(
    manifest_path: str | Path,
    raw_input_path: str | Path,
    output_prefix: str | Path,
    benchmark_modelsets: list[list[str]],
    focus_own_ship_mmsis: list[str] | None = None,
    seed_values: list[int] | None = None,
    auto_select_focus_mmsis: bool = True,
    auto_select_count: int = 3,
    auto_select_start_rank: int = 1,
    auto_select_workflow_output_dir: str | Path | None = None,
    auto_select_workflow_top_n: int | None = None,
    auto_select_workflow_min_targets: int = 1,
    auto_select_workflow_radius_nm: float | None = None,
    auto_candidate_quality_gate_apply: bool = False,
    auto_candidate_quality_gate_strict: bool = False,
    auto_candidate_quality_gate_min_row_count: int = 80,
    auto_candidate_quality_gate_min_observed_row_count: int = 40,
    auto_candidate_quality_gate_max_interpolation_ratio: float = 0.70,
    auto_candidate_quality_gate_min_heading_coverage_ratio: float = 0.50,
    auto_candidate_quality_gate_min_movement_ratio: float = 0.30,
    auto_candidate_quality_gate_min_active_window_ratio: float = 0.10,
    auto_candidate_quality_gate_min_average_nearby_targets: float = 0.50,
    auto_candidate_quality_gate_max_segment_break_count: int = 50,
    auto_candidate_quality_gate_min_candidate_score: float = 0.20,
    auto_candidate_quality_gate_min_recommended_target_count: int = 1,
    config_path: str | Path = "configs/base.toml",
    ingestion_bundle_name: str | None = None,
    ingestion_config_path: str | Path | None = None,
    source_preset_name: str | None = "auto",
    manual_column_map_text: str | None = None,
    vessel_types_text: str | None = None,
    output_root: str | Path = "outputs/focus_seed_pipeline",
    pairwise_split_strategy: str = "own_ship",
    run_calibration_eval: bool = True,
    run_own_ship_loo: bool = True,
    run_own_ship_case_eval: bool = True,
    own_ship_case_eval_min_rows: int = 30,
    own_ship_case_eval_repeat_count: int = 3,
    build_study_journals: bool = False,
    study_journal_output_template: str | None = None,
    study_journal_note: str | None = None,
    torch_device: str = "auto",
    compare_epsilon: float = 1e-9,
    focus_label: str = "focused_single_own_ship",
    baseline_label: str = "baseline_multi_own_ship",
    reuse_baseline_across_mmsis: bool = True,
    validation_gate_min_seed_count: int = 3,
    validation_gate_min_mean_aggregate_score: float = 0.0,
    validation_gate_min_delta_case_f1_mean: float = 0.0,
    validation_gate_max_delta_case_f1_std: float = 0.05,
    validation_gate_max_delta_repeat_std_mean: float = 0.02,
    validation_gate_max_delta_calibration_ece: float = 0.0,
    validation_gate_require_calibration_metric: bool = False,
    validation_gate_allow_focus_tilt: bool = True,
    validation_gate_allow_mixed: bool = False,
) -> dict[str, Any]:
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    requested_mmsis = _parse_mmsi_list(focus_own_ship_mmsis)
    focus_mmsis = requested_mmsis.copy()
    selected_candidate_rows: list[dict[str, str]] = []
    auto_workflow_summary_json_path = ""
    auto_workflow_candidates_path = ""
    auto_candidate_quality_gate_summary_json_path = ""
    auto_candidate_quality_gate_summary_md_path = ""
    auto_candidate_quality_gate_rows_csv_path = ""
    auto_candidate_quality_gate_summary: dict[str, Any] | None = None
    auto_candidate_quality_gate_passed_count = 0
    auto_candidate_quality_gate_candidate_count = 0
    auto_candidate_quality_gate_fallback_used = False
    focus_resolution_mode = "manual" if requested_mmsis else "auto_candidates"

    if not focus_mmsis:
        if not auto_select_focus_mmsis:
            raise ValueError(
                "focus_own_ship_mmsis is empty and auto_select_focus_mmsis=False. "
                "Provide MMSI list or enable auto selection."
            )

        requested_count = max(1, int(auto_select_count))
        requested_start_rank = max(1, int(auto_select_start_rank))
        workflow_top_n = auto_select_workflow_top_n
        resolved_auto_select_workflow_output_dir = _resolve_auto_select_workflow_output_dir(
            prefix=prefix,
            auto_select_workflow_output_dir=auto_select_workflow_output_dir,
        )
        if workflow_top_n is None:
            workflow_top_n = max(3, requested_start_rank + requested_count - 1)
        workflow_summary = run_ingestion_workflow(
            input_path=raw_input_path,
            output_dir=resolved_auto_select_workflow_output_dir,
            project_config_path=config_path,
            ingestion_bundle_name=ingestion_bundle_name,
            ingestion_config_path=ingestion_config_path,
            source_preset_name=source_preset_name,
            manual_column_map_text=manual_column_map_text,
            vessel_types_text=vessel_types_text,
            radius_nm=auto_select_workflow_radius_nm,
            top_n=max(1, int(workflow_top_n)),
            min_targets=max(1, int(auto_select_workflow_min_targets)),
        )
        auto_workflow_summary_json_path = str(workflow_summary.get("summary_json_path") or "")
        auto_workflow_candidates_path = str(workflow_summary.get("own_ship_candidates_path") or "")
        candidate_rows = _load_candidate_rows(auto_workflow_candidates_path)
        if auto_candidate_quality_gate_apply and candidate_rows:
            gated_rows = apply_own_ship_quality_gate(
                candidate_rows,
                min_row_count=int(auto_candidate_quality_gate_min_row_count),
                min_observed_row_count=int(auto_candidate_quality_gate_min_observed_row_count),
                max_interpolation_ratio=float(auto_candidate_quality_gate_max_interpolation_ratio),
                min_heading_coverage_ratio=float(auto_candidate_quality_gate_min_heading_coverage_ratio),
                min_movement_ratio=float(auto_candidate_quality_gate_min_movement_ratio),
                min_active_window_ratio=float(auto_candidate_quality_gate_min_active_window_ratio),
                min_average_nearby_targets=float(auto_candidate_quality_gate_min_average_nearby_targets),
                max_segment_break_count=int(auto_candidate_quality_gate_max_segment_break_count),
                min_candidate_score=float(auto_candidate_quality_gate_min_candidate_score),
                min_recommended_target_count=int(auto_candidate_quality_gate_min_recommended_target_count),
            )
            auto_candidate_quality_gate_candidate_count = len(gated_rows)
            passed_candidate_rows = [row for row in gated_rows if bool(row.get("gate_passed"))]
            auto_candidate_quality_gate_passed_count = len(passed_candidate_rows)
            auto_candidate_quality_gate_summary = build_own_ship_quality_gate_summary(
                gated_rows,
                input_path=auto_workflow_candidates_path,
                min_row_count=int(auto_candidate_quality_gate_min_row_count),
                min_observed_row_count=int(auto_candidate_quality_gate_min_observed_row_count),
                max_interpolation_ratio=float(auto_candidate_quality_gate_max_interpolation_ratio),
                min_heading_coverage_ratio=float(auto_candidate_quality_gate_min_heading_coverage_ratio),
                min_movement_ratio=float(auto_candidate_quality_gate_min_movement_ratio),
                min_active_window_ratio=float(auto_candidate_quality_gate_min_active_window_ratio),
                min_average_nearby_targets=float(auto_candidate_quality_gate_min_average_nearby_targets),
                max_segment_break_count=int(auto_candidate_quality_gate_max_segment_break_count),
                min_candidate_score=float(auto_candidate_quality_gate_min_candidate_score),
                min_recommended_target_count=int(auto_candidate_quality_gate_min_recommended_target_count),
            )
            (
                gate_summary_json_path,
                gate_summary_md_path,
                gate_rows_csv_path,
            ) = save_own_ship_quality_gate_outputs(
                prefix.with_name(f"{prefix.name}_auto_candidate_quality_gate"),
                auto_candidate_quality_gate_summary,
                gated_rows,
            )
            auto_candidate_quality_gate_summary_json_path = str(gate_summary_json_path)
            auto_candidate_quality_gate_summary_md_path = str(gate_summary_md_path)
            auto_candidate_quality_gate_rows_csv_path = str(gate_rows_csv_path)
            if passed_candidate_rows:
                candidate_rows = _sort_candidate_rows_by_rank(passed_candidate_rows)
            elif auto_candidate_quality_gate_strict:
                raise ValueError(
                    "Auto candidate quality gate rejected every own-ship candidate. "
                    f"See {auto_candidate_quality_gate_summary_md_path}."
                )
            else:
                auto_candidate_quality_gate_fallback_used = True
        selected_candidate_rows = _select_focus_candidate_rows(
            candidate_rows=candidate_rows,
            start_rank=requested_start_rank,
            select_count=requested_count,
        )
        focus_mmsis = [str(row.get("mmsi") or "").strip() for row in selected_candidate_rows if str(row.get("mmsi") or "").strip()]
        if not focus_mmsis:
            top = workflow_summary.get("top_recommendation", {})
            fallback = str(top.get("mmsi") or "").strip()
            if fallback:
                focus_mmsis = [fallback]

    if not focus_mmsis:
        raise ValueError("Unable to resolve focus own-ship MMSI list.")

    selected_focus_mmsis_csv_path = prefix.with_name(f"{prefix.name}_selected_focus_mmsis.csv")
    _write_selected_focus_mmsis_csv(
        path_value=selected_focus_mmsis_csv_path,
        focus_mmsis=focus_mmsis,
        selection_mode=focus_resolution_mode,
        selected_candidate_rows=selected_candidate_rows,
    )

    seed_compare_prefix = prefix.with_name(f"{prefix.name}_seed_compare")
    seed_summary = run_focus_seed_compare_bundle(
        manifest_path=manifest_path,
        raw_input_path=raw_input_path,
        output_prefix=seed_compare_prefix,
        focus_own_ship_mmsis=focus_mmsis,
        seed_values=seed_values,
        benchmark_modelsets=benchmark_modelsets,
        config_path=config_path,
        ingestion_bundle_name=ingestion_bundle_name,
        ingestion_config_path=ingestion_config_path,
        source_preset_name=source_preset_name,
        manual_column_map_text=manual_column_map_text,
        vessel_types_text=vessel_types_text,
        output_root=output_root,
        pairwise_split_strategy=pairwise_split_strategy,
        run_calibration_eval=bool(run_calibration_eval),
        run_own_ship_loo=bool(run_own_ship_loo),
        run_own_ship_case_eval=bool(run_own_ship_case_eval),
        own_ship_case_eval_min_rows=int(own_ship_case_eval_min_rows),
        own_ship_case_eval_repeat_count=max(1, int(own_ship_case_eval_repeat_count)),
        build_study_journals=bool(build_study_journals),
        study_journal_output_template=study_journal_output_template,
        study_journal_note=study_journal_note,
        torch_device=torch_device,
        compare_epsilon=float(compare_epsilon),
        focus_label=focus_label,
        baseline_label=baseline_label,
        reuse_baseline_across_mmsis=bool(reuse_baseline_across_mmsis),
    )

    validation_gate = _build_validation_gate(
        aggregate_rows=list(seed_summary.get("aggregate_by_modelset", [])),
        min_seed_count=max(1, int(validation_gate_min_seed_count)),
        min_mean_aggregate_score=float(validation_gate_min_mean_aggregate_score),
        min_delta_case_f1_mean=float(validation_gate_min_delta_case_f1_mean),
        max_delta_case_f1_std=float(validation_gate_max_delta_case_f1_std),
        max_delta_repeat_std_mean=float(validation_gate_max_delta_repeat_std_mean),
        max_delta_calibration_ece=float(validation_gate_max_delta_calibration_ece),
        require_calibration_metric=bool(validation_gate_require_calibration_metric),
        allow_focus_tilt=bool(validation_gate_allow_focus_tilt),
        allow_mixed=bool(validation_gate_allow_mixed),
    )
    validation_gate_rows = list(validation_gate.get("gate_rows", []))

    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    validation_gate_rows_csv_path = prefix.with_name(f"{prefix.name}_validation_gate_rows.csv")
    _write_gate_rows_csv(validation_gate_rows_csv_path, validation_gate_rows)
    summary: dict[str, Any] = {
        "status": "completed",
        "manifest_path": str(manifest_path),
        "raw_input_path": str(raw_input_path),
        "focus_mmsi_resolution_mode": focus_resolution_mode,
        "auto_select_focus_mmsis": bool(auto_select_focus_mmsis),
        "auto_select_count": max(1, int(auto_select_count)),
        "auto_select_start_rank": max(1, int(auto_select_start_rank)),
        "auto_workflow_summary_json_path": auto_workflow_summary_json_path,
        "auto_workflow_candidates_path": auto_workflow_candidates_path,
        "auto_candidate_quality_gate_applied": bool(auto_candidate_quality_gate_apply),
        "auto_candidate_quality_gate_strict": bool(auto_candidate_quality_gate_strict),
        "auto_candidate_quality_gate_candidate_count": int(auto_candidate_quality_gate_candidate_count),
        "auto_candidate_quality_gate_passed_count": int(auto_candidate_quality_gate_passed_count),
        "auto_candidate_quality_gate_fallback_used": bool(auto_candidate_quality_gate_fallback_used),
        "auto_candidate_quality_gate_summary": auto_candidate_quality_gate_summary or {},
        "auto_candidate_quality_gate_summary_json_path": auto_candidate_quality_gate_summary_json_path,
        "auto_candidate_quality_gate_summary_md_path": auto_candidate_quality_gate_summary_md_path,
        "auto_candidate_quality_gate_rows_csv_path": auto_candidate_quality_gate_rows_csv_path,
        "requested_focus_mmsis": requested_mmsis,
        "focus_own_ship_mmsis": focus_mmsis,
        "seed_values": seed_summary.get("seed_values", []),
        "benchmark_modelsets": seed_summary.get("benchmark_modelsets", benchmark_modelsets),
        "run_count": int(seed_summary.get("run_count", 0)),
        "focus_seed_compare_prefix": str(seed_compare_prefix),
        "selected_focus_mmsis_csv_path": str(selected_focus_mmsis_csv_path),
        "focus_seed_compare_summary_json_path": seed_summary.get("summary_json_path"),
        "focus_seed_compare_summary_md_path": seed_summary.get("summary_md_path"),
        "focus_seed_compare_seed_rows_csv_path": seed_summary.get("seed_rows_csv_path"),
        "focus_seed_compare_modelset_seed_rows_csv_path": seed_summary.get("modelset_seed_rows_csv_path"),
        "focus_seed_compare_aggregate_csv_path": seed_summary.get("aggregate_csv_path"),
        "seed_rows": seed_summary.get("seed_rows", []),
        "aggregate_by_modelset": seed_summary.get("aggregate_by_modelset", []),
        "validation_gate_rows_csv_path": str(validation_gate_rows_csv_path),
        "validation_gate_overall_decision": validation_gate.get("overall_decision"),
        "validation_gate_passed_modelset_count": validation_gate.get("passed_modelset_count", 0),
        "validation_gate_total_modelset_count": validation_gate.get("total_modelset_count", 0),
        "validation_gate_recommended_modelset_key": validation_gate.get("recommended_modelset_key", ""),
        "validation_gate_recommendation_basis": validation_gate.get("recommendation_basis", ""),
        "validation_gate_rows": validation_gate_rows,
        "validation_gate_min_seed_count": max(1, int(validation_gate_min_seed_count)),
        "validation_gate_min_mean_aggregate_score": float(validation_gate_min_mean_aggregate_score),
        "validation_gate_min_delta_case_f1_mean": float(validation_gate_min_delta_case_f1_mean),
        "validation_gate_max_delta_case_f1_std": float(validation_gate_max_delta_case_f1_std),
        "validation_gate_max_delta_repeat_std_mean": float(validation_gate_max_delta_repeat_std_mean),
        "validation_gate_max_delta_calibration_ece": float(validation_gate_max_delta_calibration_ece),
        "validation_gate_require_calibration_metric": bool(validation_gate_require_calibration_metric),
        "validation_gate_allow_focus_tilt": bool(validation_gate_allow_focus_tilt),
        "validation_gate_allow_mixed": bool(validation_gate_allow_mixed),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_focus_seed_pipeline_markdown(summary), encoding="utf-8")
    return summary
