from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from .benchmark import load_pairwise_dataset_rows, run_benchmark_on_partitions


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _split_train_val_timestamps(rows: list[dict[str, str]], val_fraction: float) -> tuple[set[str], set[str]]:
    timestamps = sorted({row["timestamp"] for row in rows})
    count = len(timestamps)
    if count < 2:
        raise ValueError("At least 2 unique timestamps are required to split train/validation.")

    val_count = max(1, int(math.floor(count * val_fraction)))
    if val_count >= count:
        val_count = 1
    train_count = count - val_count
    train_timestamps = set(timestamps[:train_count])
    val_timestamps = set(timestamps[train_count:])
    if not train_timestamps or not val_timestamps:
        raise ValueError("Failed to allocate non-empty train/validation timestamp partitions.")
    return train_timestamps, val_timestamps


def _aggregate_model_metrics(folds: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buffer: dict[str, dict[str, list[float]]] = {}
    for fold in folds:
        if fold.get("status") != "completed":
            continue
        for model_name, metrics in fold.get("models", {}).items():
            if metrics.get("status") == "skipped":
                continue
            current = buffer.setdefault(model_name, {"f1": [], "auroc": [], "auprc": []})
            for key in ("f1", "auroc", "auprc"):
                value = metrics.get(key)
                if value is not None:
                    current[key].append(float(value))

    result: dict[str, dict[str, Any]] = {}
    for model_name, values in buffer.items():
        metrics_payload: dict[str, Any] = {"fold_count": len(values["f1"])}
        for key, metric_values in values.items():
            if not metric_values:
                metrics_payload[f"{key}_mean"] = None
                metrics_payload[f"{key}_min"] = None
                metrics_payload[f"{key}_max"] = None
                continue
            metrics_payload[f"{key}_mean"] = float(sum(metric_values) / len(metric_values))
            metrics_payload[f"{key}_min"] = float(min(metric_values))
            metrics_payload[f"{key}_max"] = float(max(metric_values))
        result[model_name] = metrics_payload
    return result


def build_own_ship_loo_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Own-Ship Leave-One-Out Benchmark Summary",
        "",
        "## Dataset",
        "",
        f"- Input: `{summary['input_path']}`",
        f"- Row count: `{summary['row_count']}`",
        f"- Own ship count: `{summary['own_ship_count']}`",
        f"- Evaluated holdouts: `{summary['evaluated_holdouts']}`",
        f"- Completed folds: `{summary['completed_fold_count']}`",
        f"- Random seed: `{summary.get('random_seed', 'n/a')}`",
        "",
        "## Aggregate",
        "",
    ]
    for model_name, metrics in summary.get("aggregate_models", {}).items():
        lines.append(
            (
                f"- `{model_name}`: folds={metrics.get('fold_count', 0)}, "
                f"F1(mean/min/max)={_fmt(metrics.get('f1_mean'))}/{_fmt(metrics.get('f1_min'))}/{_fmt(metrics.get('f1_max'))}, "
                f"AUROC(mean)={_fmt(metrics.get('auroc_mean'))}, AUPRC(mean)={_fmt(metrics.get('auprc_mean'))}"
            )
        )
    lines.extend(["", "## Folds", ""])
    for fold in summary.get("folds", []):
        holdout = fold.get("holdout_own_mmsi", "unknown")
        status = fold.get("status", "unknown")
        lines.append(f"- holdout `{holdout}`: status=`{status}`, test_rows=`{fold.get('test_rows', 0)}`")
    lines.append("")
    return "\n".join(lines)


def run_leave_one_own_ship_out_benchmark(
    input_path: str | Path,
    output_prefix: str | Path,
    model_names: list[str] | None = None,
    holdout_own_mmsis: list[str] | None = None,
    val_fraction: float = 0.2,
    torch_device: str = "auto",
    random_seed: int | None = 42,
) -> dict[str, Any]:
    rows = load_pairwise_dataset_rows(input_path)
    if not rows:
        raise ValueError("Pairwise learning dataset is empty.")

    all_own_mmsis = sorted({str(row["own_mmsi"]) for row in rows})
    if holdout_own_mmsis:
        requested = [str(item) for item in holdout_own_mmsis]
        selected_holdouts = [item for item in requested if item in all_own_mmsis]
    else:
        selected_holdouts = all_own_mmsis
    if not selected_holdouts:
        raise ValueError("No valid holdout own_mmsi values available in dataset.")

    requested_models = model_names or ["rule_score", "logreg", "hgbt"]
    folds: list[dict[str, Any]] = []
    for fold_index, holdout in enumerate(selected_holdouts):
        test_rows = [row for row in rows if str(row["own_mmsi"]) == holdout]
        train_pool = [row for row in rows if str(row["own_mmsi"]) != holdout]
        fold_payload: dict[str, Any] = {
            "holdout_own_mmsi": holdout,
            "test_rows": len(test_rows),
            "train_pool_rows": len(train_pool),
        }
        if not test_rows:
            fold_payload.update({"status": "skipped", "reason": "holdout own ship has no rows"})
            folds.append(fold_payload)
            continue
        if not train_pool:
            fold_payload.update({"status": "skipped", "reason": "train pool is empty after holdout"})
            folds.append(fold_payload)
            continue
        try:
            train_times, val_times = _split_train_val_timestamps(train_pool, val_fraction=val_fraction)
        except Exception as exc:
            fold_payload.update({"status": "skipped", "reason": f"split failed: {exc!r}"})
            folds.append(fold_payload)
            continue

        train_rows = [row for row in train_pool if row["timestamp"] in train_times]
        val_rows = [row for row in train_pool if row["timestamp"] in val_times]
        if not train_rows or not val_rows:
            fold_payload.update({"status": "skipped", "reason": "empty train or validation rows"})
            folds.append(fold_payload)
            continue

        models_summary, _ = run_benchmark_on_partitions(
            train_rows=train_rows,
            val_rows=val_rows,
            test_rows=test_rows,
            model_names=requested_models,
            torch_device=torch_device,
            random_seed=None if random_seed is None else int(random_seed) + int(fold_index),
        )
        fold_payload.update(
            {
                "status": "completed",
                "train_rows": len(train_rows),
                "val_rows": len(val_rows),
                "train_timestamps": len(train_times),
                "val_timestamps": len(val_times),
                "models": models_summary,
            }
        )
        folds.append(fold_payload)

    aggregate_models = _aggregate_model_metrics(folds)
    summary: dict[str, Any] = {
        "status": "completed",
        "input_path": str(input_path),
        "row_count": len(rows),
        "own_ship_count": len(all_own_mmsis),
        "evaluated_holdouts": len(selected_holdouts),
        "completed_fold_count": sum(1 for fold in folds if fold.get("status") == "completed"),
        "split_strategy": "leave_one_own_ship_out",
        "val_fraction": float(val_fraction),
        "model_names": requested_models,
        "random_seed": random_seed,
        "folds": folds,
        "aggregate_models": aggregate_models,
    }

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_own_ship_loo_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_own_ship_loo_summary.md")
    fold_metrics_csv_path = prefix.with_name(f"{prefix.name}_own_ship_loo_fold_metrics.csv")

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_own_ship_loo_summary_markdown(summary), encoding="utf-8")

    with fold_metrics_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "holdout_own_mmsi",
            "status",
            "reason",
            "train_rows",
            "val_rows",
            "test_rows",
            "model_name",
            "f1",
            "auroc",
            "auprc",
            "precision",
            "recall",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for fold in folds:
            models = fold.get("models", {})
            if not models:
                writer.writerow(
                    {
                        "holdout_own_mmsi": fold.get("holdout_own_mmsi"),
                        "status": fold.get("status"),
                        "reason": fold.get("reason", ""),
                        "train_rows": fold.get("train_rows", 0),
                        "val_rows": fold.get("val_rows", 0),
                        "test_rows": fold.get("test_rows", 0),
                        "model_name": "",
                    }
                )
                continue
            for model_name, metrics in models.items():
                writer.writerow(
                    {
                        "holdout_own_mmsi": fold.get("holdout_own_mmsi"),
                        "status": fold.get("status"),
                        "reason": fold.get("reason", ""),
                        "train_rows": fold.get("train_rows", 0),
                        "val_rows": fold.get("val_rows", 0),
                        "test_rows": fold.get("test_rows", 0),
                        "model_name": model_name,
                        "f1": metrics.get("f1"),
                        "auroc": metrics.get("auroc"),
                        "auprc": metrics.get("auprc"),
                        "precision": metrics.get("precision"),
                        "recall": metrics.get("recall"),
                    }
                )

    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_md_path"] = str(summary_md_path)
    summary["fold_metrics_csv_path"] = str(fold_metrics_csv_path)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
