from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


DETAIL_FIELDS = [
    "dataset",
    "model_family",
    "model_name",
    "baseline_f1_mean",
    "baseline_f1_std",
    "baseline_ece_mean",
    "out_of_time_f1_mean",
    "out_of_time_ece_mean",
    "out_of_time_delta_f1_mean",
    "in_f1_band",
    "ece_gate_pass",
    "temporal_gate_pass",
    "temporal_penalty",
    "robust_score",
]

COMPARISON_FIELDS = [
    "dataset",
    "current_model_name",
    "robust_model_name",
    "changed",
    "current_f1_mean",
    "robust_f1_mean",
    "current_ece_mean",
    "robust_ece_mean",
    "current_out_of_time_delta_f1_mean",
    "robust_out_of_time_delta_f1_mean",
    "current_meets_temporal_target",
    "robust_meets_temporal_target",
    "best_available_out_of_time_delta_f1_mean_any_model",
    "best_available_out_of_time_delta_f1_mean_ece_pass",
    "temporal_target_feasible_any_model",
    "temporal_target_feasible_with_ece_gate",
    "robust_in_time_regression_from_best_f1",
    "robust_gate_status",
    "robust_selection_rule",
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


def _parse_csv_map(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    mapping: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        dataset = str(row.get("dataset", "")).strip()
        model = str(row.get("model_name", "")).strip()
        if not dataset or not model:
            continue
        mapping[(dataset, model)] = row
    return mapping


def _recommendation_map(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    rows = _parse_csv_rows(path)
    output: dict[str, str] = {}
    for row in rows:
        dataset = str(row.get("dataset", "")).strip()
        model_name = str(row.get("model_name", "")).strip()
        if dataset and model_name:
            output[dataset] = model_name
    return output


def _temporal_penalty(
    delta_f1: float | None,
    min_out_of_time_delta_f1: float,
    missing_delta_penalty: float = 1.0,
) -> float:
    if delta_f1 is None:
        return float(missing_delta_penalty)
    return max(0.0, float(min_out_of_time_delta_f1) - float(delta_f1))


def run_temporal_robust_recommendation(
    baseline_aggregate_csv_path: str | Path,
    out_of_time_aggregate_csv_path: str | Path,
    output_prefix: str | Path,
    baseline_recommendation_csv_path: str | Path | None = None,
    dataset_prefix_filters: list[str] | None = None,
    f1_tolerance: float = 0.01,
    max_ece_mean: float | None = 0.10,
    min_out_of_time_delta_f1: float = -0.05,
    delta_penalty_weight: float = 1.0,
) -> dict[str, Any]:
    baseline_rows = _parse_csv_rows(baseline_aggregate_csv_path)
    out_of_time_rows = _parse_csv_rows(out_of_time_aggregate_csv_path)
    baseline_recommendation = _recommendation_map(baseline_recommendation_csv_path)

    oot_map = _parse_csv_map(out_of_time_rows)

    normalized_prefixes = [str(prefix).strip().lower() for prefix in (dataset_prefix_filters or []) if str(prefix).strip()]
    if normalized_prefixes:
        baseline_rows = [
            row
            for row in baseline_rows
            if any(str(row.get("dataset", "")).strip().lower().startswith(f"{prefix}_") for prefix in normalized_prefixes)
        ]

    enriched_rows: list[dict[str, Any]] = []
    by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in baseline_rows:
        dataset = str(row.get("dataset", "")).strip()
        model_name = str(row.get("model_name", "")).strip()
        if not dataset or not model_name:
            continue
        baseline_f1 = _safe_float(row.get("f1_mean"))
        baseline_ece = _safe_float(row.get("ece_mean"))
        baseline_f1_std = _safe_float(row.get("f1_std"))
        if baseline_f1 is None:
            continue
        oot_row = oot_map.get((dataset, model_name), {})
        oot_f1 = _safe_float(oot_row.get("f1_mean"))
        oot_ece = _safe_float(oot_row.get("ece_mean"))
        oot_delta_f1 = (float(oot_f1) - float(baseline_f1)) if (oot_f1 is not None and baseline_f1 is not None) else None
        payload = {
            "dataset": dataset,
            "model_family": str(row.get("model_family", "")),
            "model_name": model_name,
            "baseline_f1_mean": baseline_f1,
            "baseline_f1_std": baseline_f1_std,
            "baseline_ece_mean": baseline_ece,
            "out_of_time_f1_mean": oot_f1,
            "out_of_time_ece_mean": oot_ece,
            "out_of_time_delta_f1_mean": oot_delta_f1,
            "in_f1_band": False,
            "ece_gate_pass": False,
            "temporal_gate_pass": False,
            "temporal_penalty": None,
            "robust_score": None,
        }
        enriched_rows.append(payload)
        by_dataset[dataset].append(payload)

    comparison_rows: list[dict[str, Any]] = []
    recommendation_rows: list[dict[str, Any]] = []
    for dataset in sorted(by_dataset.keys()):
        rows = by_dataset[dataset]
        best_f1 = max(float(row["baseline_f1_mean"]) for row in rows)
        for row in rows:
            row["in_f1_band"] = bool(float(row["baseline_f1_mean"]) >= float(best_f1) - float(f1_tolerance))
            if max_ece_mean is None:
                row["ece_gate_pass"] = True
            else:
                ece_value = _safe_float(row.get("baseline_ece_mean"))
                row["ece_gate_pass"] = bool(ece_value is not None and float(ece_value) <= float(max_ece_mean))
            delta = _safe_float(row.get("out_of_time_delta_f1_mean"))
            row["temporal_gate_pass"] = bool(delta is not None and float(delta) >= float(min_out_of_time_delta_f1))
            penalty = _temporal_penalty(delta, min_out_of_time_delta_f1=float(min_out_of_time_delta_f1))
            row["temporal_penalty"] = float(penalty)
            row["robust_score"] = float(row["baseline_f1_mean"]) - (float(delta_penalty_weight) * float(penalty))

        full_gate_band = [row for row in rows if row["in_f1_band"] and row["ece_gate_pass"] and row["temporal_gate_pass"]]
        full_gate_all = [row for row in rows if row["ece_gate_pass"] and row["temporal_gate_pass"]]
        ece_band = [row for row in rows if row["in_f1_band"] and row["ece_gate_pass"]]
        if full_gate_band:
            selection_pool = full_gate_band
            gate_status = "pass_within_f1_band_with_temporal_gate"
            selection_rule = "f1_band+ece_gate+temporal_gate_then_max_robust_score_then_min_ece_then_min_f1_std"
        elif full_gate_all:
            selection_pool = full_gate_all
            gate_status = "fallback_to_temporal+ece_gate_outside_f1_band"
            selection_rule = "ece_gate+temporal_gate_then_max_robust_score_then_min_ece_then_min_f1_std"
        elif ece_band:
            selection_pool = ece_band
            gate_status = "temporal_gate_failed_fallback_to_f1_band_with_ece_gate"
            selection_rule = "f1_band+ece_gate_then_max_robust_score_then_min_ece_then_min_f1_std"
        else:
            selection_pool = [row for row in rows if row["in_f1_band"]] or rows
            gate_status = "no_gate_pass_fallback_to_f1_band"
            selection_rule = "f1_band_then_max_robust_score_then_min_ece_then_min_f1_std"

        selection_pool.sort(
            key=lambda row: (
                -float(row.get("robust_score") or -999.0),
                float(row.get("baseline_ece_mean") if row.get("baseline_ece_mean") is not None else 999.0),
                float(row.get("baseline_f1_std") if row.get("baseline_f1_std") is not None else 999.0),
                str(row.get("model_name", "")),
            )
        )
        chosen = selection_pool[0]
        recommendation_row = {
            "dataset": dataset,
            "model_family": chosen.get("model_family", ""),
            "model_name": chosen.get("model_name", ""),
            "f1_mean": chosen.get("baseline_f1_mean"),
            "f1_std": chosen.get("baseline_f1_std"),
            "ece_mean": chosen.get("baseline_ece_mean"),
            "out_of_time_delta_f1_mean": chosen.get("out_of_time_delta_f1_mean"),
            "robust_score": chosen.get("robust_score"),
            "f1_tolerance": float(f1_tolerance),
            "ece_gate_max": max_ece_mean,
            "min_out_of_time_delta_f1": float(min_out_of_time_delta_f1),
            "delta_penalty_weight": float(delta_penalty_weight),
            "gate_status": gate_status,
            "selection_rule": selection_rule,
        }
        recommendation_rows.append(recommendation_row)

        current_model_name = str(baseline_recommendation.get(dataset, "")).strip()
        current_row = None
        if current_model_name:
            current_row = next((row for row in rows if str(row.get("model_name", "")) == current_model_name), None)
        if current_row is None:
            sorted_by_baseline = sorted(
                rows,
                key=lambda row: (
                    -float(row.get("baseline_f1_mean") or -1.0),
                    float(row.get("baseline_ece_mean") if row.get("baseline_ece_mean") is not None else 999.0),
                    str(row.get("model_name", "")),
                ),
            )
            current_row = sorted_by_baseline[0]
            current_model_name = str(current_row.get("model_name", ""))

        robust_model_name = str(chosen.get("model_name", ""))
        robust_regression = float(best_f1) - float(chosen.get("baseline_f1_mean") or 0.0)
        all_delta_values = [
            float(row["out_of_time_delta_f1_mean"])
            for row in rows
            if _safe_float(row.get("out_of_time_delta_f1_mean")) is not None
        ]
        ece_pass_delta_values = [
            float(row["out_of_time_delta_f1_mean"])
            for row in rows
            if row.get("ece_gate_pass") and _safe_float(row.get("out_of_time_delta_f1_mean")) is not None
        ]
        best_any_delta = max(all_delta_values) if all_delta_values else None
        best_ece_pass_delta = max(ece_pass_delta_values) if ece_pass_delta_values else None
        comparison_rows.append(
            {
                "dataset": dataset,
                "current_model_name": current_model_name,
                "robust_model_name": robust_model_name,
                "changed": bool(current_model_name != robust_model_name),
                "current_f1_mean": current_row.get("baseline_f1_mean"),
                "robust_f1_mean": chosen.get("baseline_f1_mean"),
                "current_ece_mean": current_row.get("baseline_ece_mean"),
                "robust_ece_mean": chosen.get("baseline_ece_mean"),
                "current_out_of_time_delta_f1_mean": current_row.get("out_of_time_delta_f1_mean"),
                "robust_out_of_time_delta_f1_mean": chosen.get("out_of_time_delta_f1_mean"),
                "current_meets_temporal_target": bool(
                    _safe_float(current_row.get("out_of_time_delta_f1_mean")) is not None
                    and float(current_row["out_of_time_delta_f1_mean"]) >= float(min_out_of_time_delta_f1)
                ),
                "robust_meets_temporal_target": bool(
                    _safe_float(chosen.get("out_of_time_delta_f1_mean")) is not None
                    and float(chosen["out_of_time_delta_f1_mean"]) >= float(min_out_of_time_delta_f1)
                ),
                "best_available_out_of_time_delta_f1_mean_any_model": best_any_delta,
                "best_available_out_of_time_delta_f1_mean_ece_pass": best_ece_pass_delta,
                "temporal_target_feasible_any_model": bool(
                    best_any_delta is not None and float(best_any_delta) >= float(min_out_of_time_delta_f1)
                ),
                "temporal_target_feasible_with_ece_gate": bool(
                    best_ece_pass_delta is not None and float(best_ece_pass_delta) >= float(min_out_of_time_delta_f1)
                ),
                "robust_in_time_regression_from_best_f1": robust_regression,
                "robust_gate_status": gate_status,
                "robust_selection_rule": selection_rule,
            }
        )

    output_prefix_path = Path(output_prefix).resolve()
    output_prefix_path.parent.mkdir(parents=True, exist_ok=True)
    detail_csv_path = output_prefix_path.with_name(output_prefix_path.name + "_detail").with_suffix(".csv")
    comparison_csv_path = output_prefix_path.with_name(output_prefix_path.name + "_comparison").with_suffix(".csv")
    recommendation_csv_path = output_prefix_path.with_name(output_prefix_path.name + "_recommendation").with_suffix(".csv")
    summary_md_path = output_prefix_path.with_suffix(".md")
    summary_json_path = output_prefix_path.with_suffix(".json")
    _write_csv(detail_csv_path, enriched_rows, DETAIL_FIELDS)
    _write_csv(comparison_csv_path, comparison_rows, COMPARISON_FIELDS)
    _write_csv(recommendation_csv_path, recommendation_rows, sorted({key for row in recommendation_rows for key in row.keys()}))

    changed_count = sum(1 for row in comparison_rows if bool(row.get("changed")))
    robust_target_pass_count = sum(1 for row in comparison_rows if bool(row.get("robust_meets_temporal_target")))
    current_target_pass_count = sum(1 for row in comparison_rows if bool(row.get("current_meets_temporal_target")))
    feasible_any_count = sum(1 for row in comparison_rows if bool(row.get("temporal_target_feasible_any_model")))
    feasible_ece_count = sum(1 for row in comparison_rows if bool(row.get("temporal_target_feasible_with_ece_gate")))
    max_regression = max(
        [float(row.get("robust_in_time_regression_from_best_f1") or 0.0) for row in comparison_rows],
        default=0.0,
    )
    best_observed_delta_any = max(
        [
            float(row.get("best_available_out_of_time_delta_f1_mean_any_model"))
            for row in comparison_rows
            if _safe_float(row.get("best_available_out_of_time_delta_f1_mean_any_model")) is not None
        ],
        default=None,
    )
    best_observed_delta_ece = max(
        [
            float(row.get("best_available_out_of_time_delta_f1_mean_ece_pass"))
            for row in comparison_rows
            if _safe_float(row.get("best_available_out_of_time_delta_f1_mean_ece_pass")) is not None
        ],
        default=None,
    )

    summary: dict[str, Any] = {
        "status": "completed",
        "baseline_aggregate_csv_path": str(Path(baseline_aggregate_csv_path).resolve()),
        "out_of_time_aggregate_csv_path": str(Path(out_of_time_aggregate_csv_path).resolve()),
        "baseline_recommendation_csv_path": (
            str(Path(baseline_recommendation_csv_path).resolve()) if baseline_recommendation_csv_path else ""
        ),
        "dataset_prefix_filters": normalized_prefixes,
        "f1_tolerance": float(f1_tolerance),
        "max_ece_mean": max_ece_mean,
        "min_out_of_time_delta_f1": float(min_out_of_time_delta_f1),
        "delta_penalty_weight": float(delta_penalty_weight),
        "dataset_count": len(by_dataset),
        "changed_recommendation_count": int(changed_count),
        "current_temporal_target_pass_count": int(current_target_pass_count),
        "robust_temporal_target_pass_count": int(robust_target_pass_count),
        "temporal_target_feasible_any_model_count": int(feasible_any_count),
        "temporal_target_feasible_with_ece_gate_count": int(feasible_ece_count),
        "best_observed_out_of_time_delta_f1_mean_any_model": best_observed_delta_any,
        "best_observed_out_of_time_delta_f1_mean_ece_pass_model": best_observed_delta_ece,
        "max_robust_in_time_regression_from_best_f1": float(max_regression),
        "detail_csv_path": str(detail_csv_path),
        "comparison_csv_path": str(comparison_csv_path),
        "recommendation_csv_path": str(recommendation_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
    }

    md_lines = [
        "# Temporal Robust Recommendation",
        "",
        "## Inputs",
        "",
        f"- baseline_aggregate_csv: `{summary['baseline_aggregate_csv_path']}`",
        f"- out_of_time_aggregate_csv: `{summary['out_of_time_aggregate_csv_path']}`",
        (
            f"- baseline_recommendation_csv: `{summary['baseline_recommendation_csv_path']}`"
            if summary["baseline_recommendation_csv_path"]
            else "- baseline_recommendation_csv: `(not provided)`"
        ),
        f"- dataset_prefix_filters: `{', '.join(summary['dataset_prefix_filters']) if summary['dataset_prefix_filters'] else 'all'}`",
        f"- f1_tolerance: `{_fmt(summary['f1_tolerance'])}`",
        f"- max_ece_mean: `{_fmt(summary['max_ece_mean'])}`",
        f"- min_out_of_time_delta_f1: `{_fmt(summary['min_out_of_time_delta_f1'])}`",
        f"- delta_penalty_weight: `{_fmt(summary['delta_penalty_weight'])}`",
        "",
        "## Summary",
        "",
        f"- dataset_count: `{summary['dataset_count']}`",
        f"- changed_recommendation_count: `{summary['changed_recommendation_count']}`",
        (
            f"- temporal_target_pass(current->robust): "
            f"`{summary['current_temporal_target_pass_count']} -> {summary['robust_temporal_target_pass_count']}`"
        ),
        (
            f"- temporal_target_feasible_datasets(any model / ece-pass model): "
            f"`{summary['temporal_target_feasible_any_model_count']} / {summary['temporal_target_feasible_with_ece_gate_count']}`"
        ),
        (
            f"- best observed out-of-time ΔF1 (any / ece-pass): "
            f"`{_fmt(summary['best_observed_out_of_time_delta_f1_mean_any_model'])} / "
            f"{_fmt(summary['best_observed_out_of_time_delta_f1_mean_ece_pass_model'])}`"
        ),
        f"- max robust in-time regression from best F1: `{_fmt(summary['max_robust_in_time_regression_from_best_f1'])}`",
        "",
        "## Current vs Robust",
        "",
        "| Dataset | Current | Robust | Changed | Current ΔF1(oot-in) | Robust ΔF1(oot-in) | Robust Regression(best F1-ref) | Gate Status |",
        "|---|---|---|---|---:|---:|---:|---|",
    ]
    for row in comparison_rows:
        md_lines.append(
            "| {dataset} | {current} | {robust} | {changed} | {c_delta} | {r_delta} | {reg} | {status} |".format(
                dataset=row.get("dataset", ""),
                current=row.get("current_model_name", ""),
                robust=row.get("robust_model_name", ""),
                changed="yes" if bool(row.get("changed")) else "no",
                c_delta=_fmt(row.get("current_out_of_time_delta_f1_mean")),
                r_delta=_fmt(row.get("robust_out_of_time_delta_f1_mean")),
                reg=_fmt(row.get("robust_in_time_regression_from_best_f1")),
                status=row.get("robust_gate_status", ""),
            )
        )

    md_lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- detail_csv: `{summary['detail_csv_path']}`",
            f"- comparison_csv: `{summary['comparison_csv_path']}`",
            f"- recommendation_csv: `{summary['recommendation_csv_path']}`",
            f"- summary_md: `{summary['summary_md_path']}`",
            f"- summary_json: `{summary['summary_json_path']}`",
            "",
        ]
    )

    summary_md_path.write_text("\n".join(md_lines), encoding="utf-8")
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


__all__ = ["run_temporal_robust_recommendation"]
