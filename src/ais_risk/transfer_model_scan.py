from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any

from .benchmark import run_pairwise_transfer_benchmark
from .calibration_eval import run_calibration_evaluation


DETAIL_FIELDS = [
    "source_region",
    "target_region",
    "model_name",
    "status",
    "threshold",
    "source_f1",
    "target_f1",
    "delta_f1",
    "target_auroc",
    "target_auprc",
    "target_ece",
    "target_brier",
    "transfer_summary_json_path",
    "target_predictions_csv_path",
    "target_calibration_summary_json_path",
]

MODEL_SUMMARY_FIELDS = [
    "source_region",
    "model_name",
    "target_count",
    "completed_target_count",
    "mean_target_f1",
    "min_target_f1",
    "mean_delta_f1",
    "min_delta_f1",
    "mean_target_ece",
    "max_target_ece",
    "all_targets_ece_leq_max",
]


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


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _parse_targets(raw: str) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    for token in str(raw).split(","):
        item = token.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Invalid target mapping: {item}. Expected region:path.")
        region, path = item.split(":", 1)
        region_name = region.strip()
        path_value = path.strip()
        if not region_name or not path_value:
            raise ValueError(f"Invalid target mapping: {item}.")
        targets.append((region_name, path_value))
    if not targets:
        raise ValueError("No target mapping parsed.")
    return targets


def run_transfer_model_scan(
    source_region: str,
    source_input_path: str | Path,
    target_input_paths_by_region: dict[str, str | Path],
    model_names: list[str],
    output_root: str | Path,
    split_strategy: str = "own_ship",
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    threshold_grid_step: float = 0.01,
    torch_device: str = "auto",
    random_seed: int = 42,
    calibration_bins: int = 10,
    calibration_ece_max: float = 0.10,
) -> dict[str, Any]:
    if not model_names:
        raise ValueError("model_names must be non-empty")

    source_region_value = str(source_region).strip()
    source_path = Path(source_input_path).resolve()
    output_root_path = Path(output_root).resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)

    detail_rows: list[dict[str, Any]] = []
    for target_region in sorted(target_input_paths_by_region.keys()):
        target_path = Path(target_input_paths_by_region[target_region]).resolve()
        run_prefix = output_root_path / f"{source_region_value}_to_{target_region}" / "model_scan"
        transfer_summary = run_pairwise_transfer_benchmark(
            train_input_path=source_path,
            target_input_path=target_path,
            output_prefix=run_prefix,
            model_names=model_names,
            train_fraction=float(train_fraction),
            val_fraction=float(val_fraction),
            split_strategy=split_strategy,
            torch_device=torch_device,
            random_seed=int(random_seed),
            threshold_grid_step=float(threshold_grid_step),
        )
        target_predictions_path = Path(transfer_summary["target_predictions_csv_path"])
        calibration_prefix = run_prefix.with_name(f"{run_prefix.name}_target_calibration")
        calibration_summary = run_calibration_evaluation(
            predictions_csv_path=target_predictions_path,
            output_prefix=calibration_prefix,
            model_names=model_names,
            num_bins=int(calibration_bins),
        )
        for model_name in model_names:
            model_summary = transfer_summary.get("models", {}).get(model_name, {})
            if str(model_summary.get("status", "")) != "completed":
                detail_rows.append(
                    {
                        "source_region": source_region_value,
                        "target_region": target_region,
                        "model_name": model_name,
                        "status": str(model_summary.get("status", "unknown")),
                        "threshold": None,
                        "source_f1": None,
                        "target_f1": None,
                        "delta_f1": None,
                        "target_auroc": None,
                        "target_auprc": None,
                        "target_ece": None,
                        "target_brier": None,
                        "transfer_summary_json_path": transfer_summary.get("transfer_summary_json_path", ""),
                        "target_predictions_csv_path": str(target_predictions_path),
                        "target_calibration_summary_json_path": calibration_summary.get("summary_json_path", ""),
                    }
                )
                continue
            source_metrics = model_summary.get("source_test", {})
            target_metrics = model_summary.get("target_transfer", {})
            source_f1 = _safe_float(source_metrics.get("f1"))
            target_f1 = _safe_float(target_metrics.get("f1"))
            row = {
                "source_region": source_region_value,
                "target_region": target_region,
                "model_name": model_name,
                "status": "completed",
                "threshold": _safe_float(model_summary.get("threshold")),
                "source_f1": source_f1,
                "target_f1": target_f1,
                "delta_f1": (float(target_f1) - float(source_f1)) if (source_f1 is not None and target_f1 is not None) else None,
                "target_auroc": _safe_float(target_metrics.get("auroc")),
                "target_auprc": _safe_float(target_metrics.get("auprc")),
                "target_ece": _safe_float(calibration_summary.get("models", {}).get(model_name, {}).get("ece")),
                "target_brier": _safe_float(calibration_summary.get("models", {}).get(model_name, {}).get("brier_score")),
                "transfer_summary_json_path": transfer_summary.get("transfer_summary_json_path", ""),
                "target_predictions_csv_path": str(target_predictions_path),
                "target_calibration_summary_json_path": calibration_summary.get("summary_json_path", ""),
            }
            detail_rows.append(row)

    by_model: dict[str, list[dict[str, Any]]] = {}
    for row in detail_rows:
        model_name = str(row.get("model_name", ""))
        if model_name:
            by_model.setdefault(model_name, []).append(row)

    model_summary_rows: list[dict[str, Any]] = []
    for model_name in sorted(by_model.keys()):
        rows = by_model[model_name]
        completed = [row for row in rows if str(row.get("status", "")) == "completed"]
        target_f1_values = [float(row["target_f1"]) for row in completed if row.get("target_f1") is not None]
        delta_f1_values = [float(row["delta_f1"]) for row in completed if row.get("delta_f1") is not None]
        ece_values = [float(row["target_ece"]) for row in completed if row.get("target_ece") is not None]
        all_targets_ece_leq_max = bool(ece_values) and all(value <= float(calibration_ece_max) for value in ece_values)
        model_summary_rows.append(
            {
                "source_region": source_region_value,
                "model_name": model_name,
                "target_count": len(rows),
                "completed_target_count": len(completed),
                "mean_target_f1": float(mean(target_f1_values)) if target_f1_values else None,
                "min_target_f1": min(target_f1_values) if target_f1_values else None,
                "mean_delta_f1": float(mean(delta_f1_values)) if delta_f1_values else None,
                "min_delta_f1": min(delta_f1_values) if delta_f1_values else None,
                "mean_target_ece": float(mean(ece_values)) if ece_values else None,
                "max_target_ece": max(ece_values) if ece_values else None,
                "all_targets_ece_leq_max": all_targets_ece_leq_max,
            }
        )

    ece_pass_rows = [row for row in model_summary_rows if row.get("all_targets_ece_leq_max") and row.get("min_target_f1") is not None]
    selection_pool = ece_pass_rows if ece_pass_rows else [row for row in model_summary_rows if row.get("min_target_f1") is not None]
    selection_rule = (
        "all_targets_ece_leq_max_then_max_min_target_f1_then_max_mean_target_f1_then_max_mean_delta_f1"
        if ece_pass_rows
        else "fallback_max_min_target_f1_then_max_mean_target_f1_then_max_mean_delta_f1"
    )
    recommended_model = ""
    if selection_pool:
        selection_pool.sort(
            key=lambda row: (
                -float(row.get("min_target_f1") or -1.0),
                -float(row.get("mean_target_f1") or -1.0),
                -float(row.get("mean_delta_f1") or -999.0),
                str(row.get("model_name", "")),
            )
        )
        recommended_model = str(selection_pool[0]["model_name"])

    output_prefix_path = output_root_path / f"{source_region_value}_transfer_model_scan"
    detail_csv_path = output_prefix_path.with_name(output_prefix_path.name + "_detail").with_suffix(".csv")
    model_summary_csv_path = output_prefix_path.with_name(output_prefix_path.name + "_model_summary").with_suffix(".csv")
    summary_md_path = output_prefix_path.with_suffix(".md")
    summary_json_path = output_prefix_path.with_suffix(".json")
    _write_csv(detail_csv_path, detail_rows, DETAIL_FIELDS)
    _write_csv(model_summary_csv_path, model_summary_rows, MODEL_SUMMARY_FIELDS)

    md_lines = [
        "# Transfer Model Scan",
        "",
        "## Inputs",
        "",
        f"- source_region: `{source_region_value}`",
        f"- source_input: `{source_path}`",
        f"- split_strategy: `{split_strategy}`",
        f"- train_fraction: `{train_fraction}`",
        f"- val_fraction: `{val_fraction}`",
        f"- threshold_grid_step: `{threshold_grid_step}`",
        f"- calibration_bins: `{calibration_bins}`",
        f"- calibration_ece_max: `{_fmt(calibration_ece_max)}`",
        f"- model_names: `{', '.join(model_names)}`",
        "",
        "## Model Summary",
        "",
        "| Model | Completed Targets | Mean Target F1 | Min Target F1 | Mean ΔF1 | Max Target ECE | ECE Gate(All Targets) |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in model_summary_rows:
        md_lines.append(
            "| {model} | {completed}/{total} | {mean_t_f1} | {min_t_f1} | {mean_d_f1} | {max_ece} | {ece_gate} |".format(
                model=row.get("model_name", ""),
                completed=row.get("completed_target_count", 0),
                total=row.get("target_count", 0),
                mean_t_f1=_fmt(row.get("mean_target_f1")),
                min_t_f1=_fmt(row.get("min_target_f1")),
                mean_d_f1=_fmt(row.get("mean_delta_f1")),
                max_ece=_fmt(row.get("max_target_ece")),
                ece_gate="pass" if bool(row.get("all_targets_ece_leq_max")) else "fail",
            )
        )
    md_lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"- selection_rule: `{selection_rule}`",
            f"- recommended_model: `{recommended_model or 'n/a'}`",
            "",
            "## Outputs",
            "",
            f"- detail_csv: `{detail_csv_path}`",
            f"- model_summary_csv: `{model_summary_csv_path}`",
            f"- summary_md: `{summary_md_path}`",
            f"- summary_json: `{summary_json_path}`",
            "",
        ]
    )
    summary_md_path.write_text("\n".join(md_lines), encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "completed",
        "source_region": source_region_value,
        "source_input_path": str(source_path),
        "target_regions": sorted(target_input_paths_by_region.keys()),
        "model_names": model_names,
        "split_strategy": split_strategy,
        "train_fraction": float(train_fraction),
        "val_fraction": float(val_fraction),
        "threshold_grid_step": float(threshold_grid_step),
        "calibration_bins": int(calibration_bins),
        "calibration_ece_max": float(calibration_ece_max),
        "detail_csv_path": str(detail_csv_path),
        "model_summary_csv_path": str(model_summary_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
        "recommended_model": recommended_model,
        "selection_rule": selection_rule,
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


__all__ = [
    "run_transfer_model_scan",
    "_parse_targets",
]
