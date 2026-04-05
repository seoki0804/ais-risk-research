from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from .config import load_config
from .geo import nm_to_m
from .grid import build_grid, risk_label
from .models import ProjectConfig


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _build_case_id(timestamp: str, own_mmsi: str, model_name: str) -> str:
    safe_timestamp = timestamp.replace(":", "-")
    return f"{safe_timestamp}__{own_mmsi}__{model_name}"


def _relative_position_xy_m(distance_nm: float, relative_bearing_deg: float) -> tuple[float, float]:
    distance_m = nm_to_m(distance_nm)
    bearing_rad = math.radians(relative_bearing_deg)
    x_m = distance_m * math.sin(bearing_rad)
    y_m = distance_m * math.cos(bearing_rad)
    return x_m, y_m


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _build_pairwise_lookup(rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str, str], dict[str, str]], int]:
    lookup: dict[tuple[str, str, str], dict[str, str]] = {}
    duplicate_keys = 0
    for row in rows:
        key = (
            str(row.get("timestamp", "")),
            str(row.get("own_mmsi", "")),
            str(row.get("target_mmsi", "")),
        )
        if key in lookup:
            duplicate_keys += 1
            continue
        lookup[key] = row
    return lookup, duplicate_keys


def _discover_models(rows: list[dict[str, str]]) -> list[str]:
    models: list[str] = []
    seen: set[str] = set()
    for row in rows:
        model_name = str(row.get("model") or "").strip()
        if not model_name or model_name in seen:
            continue
        models.append(model_name)
        seen.add(model_name)
    return models


def _project_case_to_cells(
    case_rows: list[dict[str, Any]],
    config: ProjectConfig,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cells = build_grid(config)
    raw_values = [0.0] * len(cells)
    lower_values = [0.0] * len(cells)
    mean_values = [0.0] * len(cells)
    upper_values = [0.0] * len(cells)
    sigma_sq = config.grid.kernel_sigma_m * config.grid.kernel_sigma_m
    support_radius_sq = (config.grid.kernel_sigma_m * 3.0) ** 2

    for target_row in case_rows:
        x_m = float(target_row["x_m"])
        y_m = float(target_row["y_m"])
        raw_score = float(target_row["raw_score"])
        lower_score = float(target_row["score_lower"])
        mean_score = float(target_row["score_mean"])
        upper_score = float(target_row["score_upper"])
        for index, (cx_m, cy_m) in enumerate(cells):
            dx = cx_m - x_m
            dy = cy_m - y_m
            dist_sq = dx * dx + dy * dy
            if dist_sq > support_radius_sq:
                continue
            kernel_weight = math.exp(-(dist_sq / (2.0 * sigma_sq)))
            if raw_score > 0.0:
                raw_values[index] = max(raw_values[index], raw_score * kernel_weight)
            if lower_score > 0.0:
                lower_values[index] = max(lower_values[index], lower_score * kernel_weight)
            if mean_score > 0.0:
                mean_values[index] = max(mean_values[index], mean_score * kernel_weight)
            if upper_score > 0.0:
                upper_values[index] = max(upper_values[index], upper_score * kernel_weight)

    cell_area_nm2 = (config.grid.cell_size_m * config.grid.cell_size_m) / (1852.0 * 1852.0)
    projected_rows: list[dict[str, Any]] = []
    for (x_m, y_m), raw_value, lower_value, mean_value, upper_value in zip(
        cells,
        raw_values,
        lower_values,
        mean_values,
        upper_values,
        strict=True,
    ):
        projected_rows.append(
            {
                "x_m": f"{x_m:.2f}",
                "y_m": f"{y_m:.2f}",
                "risk_raw": f"{raw_value:.6f}",
                "risk_lower": f"{lower_value:.6f}",
                "risk_mean": f"{mean_value:.6f}",
                "risk_upper": f"{upper_value:.6f}",
                "label_raw": risk_label(raw_value, config),
                "label_lower": risk_label(lower_value, config),
                "label_mean": risk_label(mean_value, config),
                "label_upper": risk_label(upper_value, config),
            }
        )

    band_spans = [upper - lower for lower, upper in zip(lower_values, upper_values, strict=True)]
    return projected_rows, {
        "cell_count": len(projected_rows),
        "max_risk_raw": max(raw_values) if raw_values else 0.0,
        "max_risk_lower": max(lower_values) if lower_values else 0.0,
        "max_risk_mean": max(mean_values) if mean_values else 0.0,
        "max_risk_upper": max(upper_values) if upper_values else 0.0,
        "mean_risk_raw": (sum(raw_values) / len(raw_values)) if raw_values else 0.0,
        "mean_risk_lower": (sum(lower_values) / len(lower_values)) if lower_values else 0.0,
        "mean_risk_mean": (sum(mean_values) / len(mean_values)) if mean_values else 0.0,
        "mean_risk_upper": (sum(upper_values) / len(upper_values)) if upper_values else 0.0,
        "max_cell_band_span": max(band_spans) if band_spans else 0.0,
        "mean_cell_band_span": (sum(band_spans) / len(band_spans)) if band_spans else 0.0,
        "warning_area_raw_nm2": sum(1 for value in raw_values if value >= config.thresholds.warning) * cell_area_nm2,
        "warning_area_lower_nm2": sum(1 for value in lower_values if value >= config.thresholds.warning) * cell_area_nm2,
        "warning_area_mean_nm2": sum(1 for value in mean_values if value >= config.thresholds.warning) * cell_area_nm2,
        "warning_area_upper_nm2": sum(1 for value in upper_values if value >= config.thresholds.warning) * cell_area_nm2,
        "caution_area_raw_nm2": sum(1 for value in raw_values if value >= config.thresholds.safe) * cell_area_nm2,
        "caution_area_lower_nm2": sum(1 for value in lower_values if value >= config.thresholds.safe) * cell_area_nm2,
        "caution_area_mean_nm2": sum(1 for value in mean_values if value >= config.thresholds.safe) * cell_area_nm2,
        "caution_area_upper_nm2": sum(1 for value in upper_values if value >= config.thresholds.safe) * cell_area_nm2,
    }


def _build_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Prediction Grid Projection Summary",
        "",
        "## Inputs",
        "",
        f"- pairwise_csv: `{summary['pairwise_csv_path']}`",
        f"- sample_bands_csv: `{summary['sample_bands_csv_path']}`",
        f"- config_path: `{summary['config_path']}`",
        f"- models: `{', '.join(summary['model_names'])}`",
        f"- case_rank_metric: `{summary['case_rank_metric']}`",
        f"- case_limit: `{summary['case_limit']}`",
        "",
        "## Model Metrics",
        "",
        "| Model | Status | JoinedRows | UnmatchedRows | CaseCount | SelectedCases | MeanCaseMaxRaw | MeanCaseMaxMean | MeanCaseMaxBandSpan |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_name in summary["model_names"]:
        metrics = summary["models"].get(model_name, {})
        lines.append(
            "| {model} | {status} | {joined} | {unmatched} | {cases} | {selected} | {case_max_raw} | {case_max_mean} | {case_band} |".format(
                model=model_name,
                status=metrics.get("status", "unknown"),
                joined=metrics.get("joined_rows", 0),
                unmatched=metrics.get("unmatched_rows", 0),
                cases=metrics.get("case_count", 0),
                selected=metrics.get("selected_case_count", 0),
                case_max_raw=_format_metric(metrics.get("mean_case_max_risk_raw", 0.0)),
                case_max_mean=_format_metric(metrics.get("mean_case_max_risk_mean", 0.0)),
                case_band=_format_metric(metrics.get("mean_case_max_band_span", 0.0)),
            )
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- summary_json: `{summary['summary_json_path']}`",
            f"- summary_md: `{summary['summary_md_path']}`",
            f"- projected_targets_csv: `{summary['projected_targets_csv_path']}`",
            f"- case_summary_csv: `{summary['case_summary_csv_path']}`",
            f"- projected_cells_csv: `{summary['projected_cells_csv_path']}`",
            f"- projected_target_rows: `{summary['projected_target_rows']}`",
            f"- projected_cell_rows: `{summary['projected_cell_rows']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_prediction_grid_projection(
    pairwise_csv_path: str | Path,
    sample_bands_csv_path: str | Path,
    output_prefix: str | Path,
    config_path: str | Path = "configs/base.toml",
    model_names: list[str] | None = None,
    case_limit: int | None = 10,
    case_rank_metric: str = "max_risk_mean",
    selected_case_ids: list[str] | None = None,
) -> dict[str, Any]:
    if case_limit is not None and case_limit <= 0:
        raise ValueError("case_limit must be positive when provided.")
    if case_rank_metric not in {"max_risk_mean", "max_cell_band_span", "target_count"}:
        raise ValueError("case_rank_metric must be one of: max_risk_mean, max_cell_band_span, target_count.")

    pairwise_path = Path(pairwise_csv_path)
    sample_bands_path = Path(sample_bands_csv_path)
    resolved_config_path = Path(config_path)
    config = load_config(resolved_config_path)

    pairwise_rows = _read_csv_rows(pairwise_path)
    sample_band_rows = _read_csv_rows(sample_bands_path)
    if not pairwise_rows:
        raise ValueError("Pairwise CSV is empty.")
    if not sample_band_rows:
        raise ValueError("Sample band CSV is empty.")

    pairwise_lookup, duplicate_pairwise_keys = _build_pairwise_lookup(pairwise_rows)
    discovered_models = _discover_models(sample_band_rows)
    resolved_models = model_names or discovered_models
    if not resolved_models:
        raise ValueError("No models found in sample band CSV.")

    output_root = Path(f"{output_prefix}")
    output_root.parent.mkdir(parents=True, exist_ok=True)

    projected_target_rows: list[dict[str, Any]] = []
    case_rows_by_model: dict[str, dict[str, list[dict[str, Any]]]] = {model_name: {} for model_name in resolved_models}
    unmatched_rows_by_model: dict[str, int] = {model_name: 0 for model_name in resolved_models}
    projected_rows_by_model: dict[str, int] = {model_name: 0 for model_name in resolved_models}
    model_metrics: dict[str, Any] = {}

    for row in sample_band_rows:
        model_name = str(row.get("model") or "").strip()
        if model_name not in resolved_models:
            continue
        key = (
            str(row.get("timestamp", "")),
            str(row.get("own_mmsi", "")),
            str(row.get("target_mmsi", "")),
        )
        pairwise_row = pairwise_lookup.get(key)
        if pairwise_row is None:
            unmatched_rows_by_model[model_name] = unmatched_rows_by_model.get(model_name, 0) + 1
            continue
        distance_nm = _safe_float(pairwise_row.get("distance_nm"))
        relative_bearing_deg = _safe_float(pairwise_row.get("relative_bearing_deg"))
        score_lower = _safe_float(row.get("score_lower"))
        score_mean = _safe_float(row.get("score_mean"))
        score_upper = _safe_float(row.get("score_upper"))
        raw_score = _safe_float(row.get("raw_score"))
        band_width = _safe_float(row.get("band_width"))
        if None in {distance_nm, relative_bearing_deg, score_lower, score_mean, score_upper, band_width}:
            unmatched_rows_by_model[model_name] = unmatched_rows_by_model.get(model_name, 0) + 1
            continue
        resolved_raw_score = float(score_mean) if raw_score is None else float(raw_score)
        x_m, y_m = _relative_position_xy_m(float(distance_nm), float(relative_bearing_deg))
        case_id = _build_case_id(str(row.get("timestamp", "")), str(row.get("own_mmsi", "")), model_name)
        output_row = {
            "case_id": case_id,
            "timestamp": str(row.get("timestamp", "")),
            "own_mmsi": str(row.get("own_mmsi", "")),
            "target_mmsi": str(row.get("target_mmsi", "")),
            "model": model_name,
            "distance_nm": f"{float(distance_nm):.6f}",
            "relative_bearing_deg": f"{float(relative_bearing_deg):.6f}",
            "x_m": f"{x_m:.2f}",
            "y_m": f"{y_m:.2f}",
            "raw_score": f"{resolved_raw_score:.6f}",
            "score_lower": f"{float(score_lower):.6f}",
            "score_mean": f"{float(score_mean):.6f}",
            "score_upper": f"{float(score_upper):.6f}",
            "band_width": f"{float(band_width):.6f}",
            "label_future_conflict": str(row.get("label_future_conflict", "")),
            "encounter_type": str(pairwise_row.get("encounter_type", "")),
            "target_vessel_type": str(pairwise_row.get("target_vessel_type", "")),
        }
        projected_target_rows.append(output_row)
        case_rows_by_model.setdefault(model_name, {}).setdefault(case_id, []).append(output_row)
        projected_rows_by_model[model_name] = projected_rows_by_model.get(model_name, 0) + 1

    case_summary_rows: list[dict[str, Any]] = []
    selected_case_ids_set = set(selected_case_ids or [])
    projected_cells_by_case: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for model_name in resolved_models:
        model_cases = case_rows_by_model.get(model_name, {})
        model_case_summaries: list[dict[str, Any]] = []
        for case_id, case_rows in model_cases.items():
            projected_cells, cell_metrics = _project_case_to_cells(case_rows, config)
            projected_cells_by_case[(model_name, case_id)] = projected_cells
            case_summary = {
                "case_id": case_id,
                "timestamp": case_rows[0]["timestamp"],
                "own_mmsi": case_rows[0]["own_mmsi"],
                "model": model_name,
                "target_count": len(case_rows),
                "mean_target_band_width": sum(float(item["band_width"]) for item in case_rows) / len(case_rows),
                "max_target_band_width": max(float(item["band_width"]) for item in case_rows),
                **cell_metrics,
                "_projected_cells": projected_cells,
            }
            model_case_summaries.append(case_summary)

        if case_rank_metric == "max_cell_band_span":
            model_case_summaries.sort(key=lambda item: float(item["max_cell_band_span"]), reverse=True)
        elif case_rank_metric == "target_count":
            model_case_summaries.sort(key=lambda item: int(item["target_count"]), reverse=True)
        else:
            model_case_summaries.sort(key=lambda item: float(item["max_risk_mean"]), reverse=True)

        selected_case_ids_for_model = set(selected_case_ids or [])
        if not selected_case_ids_for_model:
            limited_summaries = model_case_summaries if case_limit is None else model_case_summaries[:case_limit]
            selected_case_ids_for_model.update(str(item["case_id"]) for item in limited_summaries)
        selected_case_ids_set.update(selected_case_ids_for_model)

        selected_count = 0
        for case_summary in model_case_summaries:
            if case_summary["case_id"] in selected_case_ids_for_model:
                selected_count += 1
            case_summary_rows.append({key: value for key, value in case_summary.items() if key != "_projected_cells"})

        model_metrics[model_name] = {
            "status": "completed" if model_case_summaries else "skipped",
            "joined_rows": projected_rows_by_model.get(model_name, 0),
            "unmatched_rows": unmatched_rows_by_model.get(model_name, 0),
            "case_count": len(model_case_summaries),
            "selected_case_count": selected_count,
            "mean_case_max_risk_mean": (
                sum(float(item["max_risk_mean"]) for item in model_case_summaries) / len(model_case_summaries)
                if model_case_summaries
                else 0.0
            ),
            "mean_case_max_risk_raw": (
                sum(float(item["max_risk_raw"]) for item in model_case_summaries) / len(model_case_summaries)
                if model_case_summaries
                else 0.0
            ),
            "mean_case_max_band_span": (
                sum(float(item["max_cell_band_span"]) for item in model_case_summaries) / len(model_case_summaries)
                if model_case_summaries
                else 0.0
            ),
        }

    case_summary_rows.sort(key=lambda item: (str(item["model"]), str(item["timestamp"]), str(item["own_mmsi"])))
    projected_cell_rows: list[dict[str, Any]] = []
    for case_summary in case_summary_rows:
        if str(case_summary["case_id"]) not in selected_case_ids_set:
            continue
        model_name = str(case_summary["model"])
        case_id = str(case_summary["case_id"])
        projected_cells = projected_cells_by_case.get((model_name, case_id), [])
        for cell in projected_cells:
            projected_cell_rows.append(
                {
                    "case_id": case_id,
                    "timestamp": case_summary["timestamp"],
                    "own_mmsi": case_summary["own_mmsi"],
                    "model": model_name,
                    **cell,
                }
            )

    projected_targets_csv_path = output_root.with_name(f"{output_root.name}_projected_targets.csv")
    case_summary_csv_path = output_root.with_name(f"{output_root.name}_case_summary.csv")
    projected_cells_csv_path = output_root.with_name(f"{output_root.name}_projected_cells.csv")
    summary_json_path = output_root.with_name(f"{output_root.name}_summary.json")
    summary_md_path = output_root.with_name(f"{output_root.name}_summary.md")

    with projected_targets_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "timestamp",
                "own_mmsi",
                "target_mmsi",
                "model",
                "distance_nm",
                "relative_bearing_deg",
                "x_m",
                "y_m",
                "raw_score",
                "score_lower",
                "score_mean",
                "score_upper",
                "band_width",
                "label_future_conflict",
                "encounter_type",
                "target_vessel_type",
            ],
        )
        writer.writeheader()
        writer.writerows(projected_target_rows)

    with case_summary_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "timestamp",
                "own_mmsi",
                "model",
                "target_count",
                "mean_target_band_width",
                "max_target_band_width",
                "cell_count",
                "max_risk_raw",
                "max_risk_lower",
                "max_risk_mean",
                "max_risk_upper",
                "mean_risk_raw",
                "mean_risk_lower",
                "mean_risk_mean",
                "mean_risk_upper",
                "max_cell_band_span",
                "mean_cell_band_span",
                "warning_area_raw_nm2",
                "warning_area_lower_nm2",
                "warning_area_mean_nm2",
                "warning_area_upper_nm2",
                "caution_area_raw_nm2",
                "caution_area_lower_nm2",
                "caution_area_mean_nm2",
                "caution_area_upper_nm2",
            ],
        )
        writer.writeheader()
        writer.writerows(case_summary_rows)

    with projected_cells_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "timestamp",
                "own_mmsi",
                "model",
                "x_m",
                "y_m",
                "risk_raw",
                "risk_lower",
                "risk_mean",
                "risk_upper",
                "label_raw",
                "label_lower",
                "label_mean",
                "label_upper",
            ],
        )
        writer.writeheader()
        writer.writerows(projected_cell_rows)

    summary = {
        "status": "completed" if case_summary_rows else "skipped",
        "pairwise_csv_path": str(pairwise_path),
        "sample_bands_csv_path": str(sample_bands_path),
        "config_path": str(resolved_config_path),
        "model_names": resolved_models,
        "case_rank_metric": case_rank_metric,
        "case_limit": case_limit,
        "selected_case_ids": sorted(selected_case_ids_set),
        "duplicate_pairwise_keys": duplicate_pairwise_keys,
        "projected_target_rows": sum(projected_rows_by_model.values()),
        "unmatched_sample_rows": sum(unmatched_rows_by_model.values()),
        "case_summary_rows": len(case_summary_rows),
        "projected_cell_rows": len(projected_cell_rows),
        "projected_targets_csv_path": str(projected_targets_csv_path),
        "case_summary_csv_path": str(case_summary_csv_path),
        "projected_cells_csv_path": str(projected_cells_csv_path),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "models": model_metrics,
    }

    with summary_json_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    summary_md_path.write_text(_build_summary_markdown(summary), encoding="utf-8")
    return summary
