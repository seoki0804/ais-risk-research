from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from .benchmark import load_pairwise_dataset_rows, run_benchmark_on_partitions


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _fmt(value: Any) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.4f}"


def _mean_std(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    mean = float(sum(values) / len(values))
    variance = float(sum((item - mean) ** 2 for item in values) / len(values))
    return mean, float(variance**0.5)


def _ci95_bounds(mean: float | None, std: float | None, sample_size: int) -> tuple[float | None, float | None, float | None]:
    if mean is None or std is None or sample_size <= 0:
        return None, None, None
    margin = float(1.96 * (std / math.sqrt(sample_size)))
    return float(mean - margin), float(mean + margin), float(2.0 * margin)


def _split_ordered_values(
    ordered_values: list[str],
    train_fraction: float,
    val_fraction: float,
) -> tuple[set[str], set[str], set[str]]:
    count = len(ordered_values)
    if count < 3:
        raise ValueError("At least 3 unique timestamps are required for train/val/test split.")

    train_count = max(1, int(math.floor(count * train_fraction)))
    val_count = max(1, int(math.floor(count * val_fraction)))
    if train_count + val_count >= count:
        train_count = max(1, count - 2)
        val_count = 1
    test_count = count - train_count - val_count
    if test_count <= 0:
        if train_count > 1:
            train_count -= 1
        elif val_count > 1:
            val_count -= 1
        test_count = count - train_count - val_count
    if test_count <= 0:
        raise ValueError("Unable to allocate non-empty test split from timestamps.")

    train_values = set(ordered_values[:train_count])
    val_values = set(ordered_values[train_count : train_count + val_count])
    test_values = set(ordered_values[train_count + val_count :])
    return train_values, val_values, test_values


def _rotate_ordered_values(values: list[str], offset: int) -> list[str]:
    if not values:
        return []
    normalized = int(offset) % len(values)
    if normalized == 0:
        return list(values)
    return values[normalized:] + values[:normalized]


def _aggregate_model_metrics(ship_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buffer: dict[str, dict[str, list[float]]] = {}
    for ship in ship_rows:
        if ship.get("status") != "completed":
            continue
        for model_name, metrics in ship.get("models", {}).items():
            if metrics.get("status") == "skipped":
                continue
            slot = buffer.setdefault(model_name, {"f1": [], "auroc": [], "auprc": [], "f1_std_repeat": []})
            for metric in ("f1", "auroc", "auprc", "f1_std_repeat"):
                value = _safe_float(metrics.get(metric))
                if value is not None:
                    slot[metric].append(float(value))

    aggregated: dict[str, dict[str, Any]] = {}
    for model_name, metrics in buffer.items():
        payload: dict[str, Any] = {
            "ship_count": len(metrics["f1"]),
        }
        for metric_name in ("f1", "auroc", "auprc"):
            values = metrics.get(metric_name, [])
            if not values:
                payload[f"{metric_name}_mean"] = None
                payload[f"{metric_name}_std"] = None
                payload[f"{metric_name}_min"] = None
                payload[f"{metric_name}_max"] = None
                payload[f"{metric_name}_ci95_low"] = None
                payload[f"{metric_name}_ci95_high"] = None
                payload[f"{metric_name}_ci95_width"] = None
                continue
            mean, std = _mean_std(values)
            low, high, width = _ci95_bounds(mean, std, len(values))
            payload[f"{metric_name}_mean"] = mean
            payload[f"{metric_name}_std"] = std
            payload[f"{metric_name}_min"] = float(min(values))
            payload[f"{metric_name}_max"] = float(max(values))
            payload[f"{metric_name}_ci95_low"] = low
            payload[f"{metric_name}_ci95_high"] = high
            payload[f"{metric_name}_ci95_width"] = width

        f1_std_repeat_values = metrics.get("f1_std_repeat", [])
        if not f1_std_repeat_values:
            payload["f1_std_repeat_mean"] = None
            payload["f1_std_repeat_max"] = None
        else:
            payload["f1_std_repeat_mean"] = float(sum(f1_std_repeat_values) / len(f1_std_repeat_values))
            payload["f1_std_repeat_max"] = float(max(f1_std_repeat_values))
        aggregated[model_name] = payload
    return aggregated


def _aggregate_repeat_models(repeat_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buffer: dict[str, dict[str, list[float]]] = {}
    for repeat in repeat_rows:
        if repeat.get("status") != "completed":
            continue
        for model_name, metrics in repeat.get("models", {}).items():
            if metrics.get("status") == "skipped":
                continue
            slot = buffer.setdefault(
                model_name,
                {
                    "f1": [],
                    "auroc": [],
                    "auprc": [],
                    "precision": [],
                    "recall": [],
                    "threshold": [],
                },
            )
            for metric in slot.keys():
                value = _safe_float(metrics.get(metric))
                if value is not None:
                    slot[metric].append(float(value))

    output: dict[str, dict[str, Any]] = {}
    for model_name, metrics in buffer.items():
        payload: dict[str, Any] = {
            "status": "completed",
            "repeat_count": len(metrics["f1"]),
        }
        for metric_name, values in metrics.items():
            if not values:
                payload[metric_name] = None
                payload[f"{metric_name}_std_repeat"] = None
                payload[f"{metric_name}_ci95_low_repeat"] = None
                payload[f"{metric_name}_ci95_high_repeat"] = None
                payload[f"{metric_name}_ci95_width_repeat"] = None
                continue
            mean, std = _mean_std(values)
            low, high, width = _ci95_bounds(mean, std, len(values))
            payload[metric_name] = mean
            payload[f"{metric_name}_std_repeat"] = std
            payload[f"{metric_name}_ci95_low_repeat"] = low
            payload[f"{metric_name}_ci95_high_repeat"] = high
            payload[f"{metric_name}_ci95_width_repeat"] = width
        output[model_name] = payload
    return output


def build_own_ship_case_eval_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Own-Ship Case Evaluation Summary",
        "",
        "## Inputs",
        "",
        f"- input: `{summary['input_path']}`",
        f"- model_names: `{', '.join(summary['model_names'])}`",
        f"- train_fraction: `{summary['train_fraction']}`",
        f"- val_fraction: `{summary['val_fraction']}`",
        f"- min_rows_per_ship: `{summary['min_rows_per_ship']}`",
        f"- repeat_count: `{summary['repeat_count']}`",
        f"- repeat_strategy: `{summary['repeat_strategy']}`",
        f"- random_seed: `{summary.get('random_seed', 'n/a')}`",
        f"- requested_own_ships: `{summary['requested_own_ships']}`",
        "",
        "## Execution",
        "",
        f"- candidate_own_ships: `{summary['candidate_own_ship_count']}`",
        f"- evaluated_own_ships: `{summary['evaluated_own_ship_count']}`",
        f"- completed_own_ships: `{summary['completed_own_ship_count']}`",
        f"- skipped_own_ships: `{summary['skipped_own_ship_count']}`",
        f"- completed_repeats_total: `{summary.get('completed_repeats_total', 0)}`",
        f"- requested_repeats_total: `{summary.get('requested_repeats_total', 0)}`",
        "",
        "## Aggregate",
        "",
    ]
    for model_name, metrics in summary.get("aggregate_models", {}).items():
        lines.append(
            "- `{model}`: ships={ships}, F1(mean/std/ci95/min/max)={f1_mean}/{f1_std}/{f1_ci_low}~{f1_ci_high}/{f1_min}/{f1_max}, repeat_std(mean/max)={f1_std_repeat_mean}/{f1_std_repeat_max}, AUROC(mean)={auroc_mean}, AUPRC(mean)={auprc_mean}".format(
                model=model_name,
                ships=metrics.get("ship_count", 0),
                f1_mean=_fmt(metrics.get("f1_mean")),
                f1_std=_fmt(metrics.get("f1_std")),
                f1_ci_low=_fmt(metrics.get("f1_ci95_low")),
                f1_ci_high=_fmt(metrics.get("f1_ci95_high")),
                f1_min=_fmt(metrics.get("f1_min")),
                f1_max=_fmt(metrics.get("f1_max")),
                f1_std_repeat_mean=_fmt(metrics.get("f1_std_repeat_mean")),
                f1_std_repeat_max=_fmt(metrics.get("f1_std_repeat_max")),
                auroc_mean=_fmt(metrics.get("auroc_mean")),
                auprc_mean=_fmt(metrics.get("auprc_mean")),
            )
        )

    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- summary_json: `{summary['summary_json_path']}`",
            f"- summary_md: `{summary['summary_md_path']}`",
            f"- ship_metrics_csv: `{summary['ship_metrics_csv_path']}`",
            f"- repeat_metrics_csv: `{summary['repeat_metrics_csv_path']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_own_ship_case_evaluation(
    input_path: str | Path,
    output_prefix: str | Path,
    model_names: list[str] | None = None,
    own_mmsis: list[str] | None = None,
    min_rows_per_ship: int = 30,
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    repeat_count: int = 1,
    torch_device: str = "auto",
    random_seed: int | None = 42,
) -> dict[str, Any]:
    rows = load_pairwise_dataset_rows(input_path)
    if not rows:
        raise ValueError("Pairwise learning dataset is empty.")

    requested_models = model_names or ["rule_score", "logreg", "hgbt"]
    all_own_mmsis = sorted({str(row.get("own_mmsi", "")) for row in rows if row.get("own_mmsi")})
    if own_mmsis:
        requested_own_mmsis = [str(item) for item in own_mmsis]
        selected_own_mmsis = [item for item in requested_own_mmsis if item in all_own_mmsis]
    else:
        requested_own_mmsis = []
        selected_own_mmsis = all_own_mmsis
    if not selected_own_mmsis:
        raise ValueError("No valid own_mmsi values available in dataset.")

    repeat_count_value = max(1, int(repeat_count))
    ships: list[dict[str, Any]] = []
    for ship_index, own_mmsi in enumerate(selected_own_mmsis):
        ship_rows = [row for row in rows if str(row.get("own_mmsi", "")) == own_mmsi]
        unique_timestamps = sorted({str(row.get("timestamp", "")) for row in ship_rows if row.get("timestamp")})
        payload: dict[str, Any] = {
            "own_mmsi": own_mmsi,
            "row_count": len(ship_rows),
            "timestamp_count": len(unique_timestamps),
            "repeat_count": repeat_count_value,
        }
        if len(ship_rows) < int(min_rows_per_ship):
            payload.update(
                {
                    "status": "skipped",
                    "reason": f"row_count below min_rows_per_ship ({len(ship_rows)} < {int(min_rows_per_ship)})",
                }
            )
            ships.append(payload)
            continue
        if len(unique_timestamps) < 3:
            payload.update(
                {
                    "status": "skipped",
                    "reason": "at least 3 unique timestamps are required",
                }
            )
            ships.append(payload)
            continue

        repeat_results: list[dict[str, Any]] = []
        for repeat_index in range(repeat_count_value):
            rotation = 0
            if repeat_count_value > 1:
                rotation = int((len(unique_timestamps) * repeat_index) / repeat_count_value)
            rotated_timestamps = _rotate_ordered_values(unique_timestamps, offset=rotation)
            repeat_payload: dict[str, Any] = {
                "repeat_index": repeat_index,
                "rotation": rotation,
            }
            try:
                train_timestamps, val_timestamps, test_timestamps = _split_ordered_values(
                    rotated_timestamps,
                    train_fraction=float(train_fraction),
                    val_fraction=float(val_fraction),
                )
            except Exception as exc:
                repeat_payload.update(
                    {
                        "status": "skipped",
                        "reason": f"timestamp split failed: {exc!r}",
                    }
                )
                repeat_results.append(repeat_payload)
                continue

            train_rows = [row for row in ship_rows if str(row.get("timestamp", "")) in train_timestamps]
            val_rows = [row for row in ship_rows if str(row.get("timestamp", "")) in val_timestamps]
            test_rows = [row for row in ship_rows if str(row.get("timestamp", "")) in test_timestamps]
            if not train_rows or not val_rows or not test_rows:
                repeat_payload.update(
                    {
                        "status": "skipped",
                        "reason": "empty train/val/test partition after timestamp split",
                    }
                )
                repeat_results.append(repeat_payload)
                continue

            models_summary, _ = run_benchmark_on_partitions(
                train_rows=train_rows,
                val_rows=val_rows,
                test_rows=test_rows,
                model_names=requested_models,
                torch_device=torch_device,
                random_seed=(
                    None
                    if random_seed is None
                    else int(random_seed) + int(ship_index * 1000) + int(repeat_index)
                ),
            )
            repeat_payload.update(
                {
                    "status": "completed",
                    "train_rows": len(train_rows),
                    "val_rows": len(val_rows),
                    "test_rows": len(test_rows),
                    "train_timestamps": len(train_timestamps),
                    "val_timestamps": len(val_timestamps),
                    "test_timestamps": len(test_timestamps),
                    "models": models_summary,
                }
            )
            repeat_results.append(repeat_payload)

        completed_repeats = [item for item in repeat_results if item.get("status") == "completed"]
        if not completed_repeats:
            payload.update(
                {
                    "status": "skipped",
                    "reason": "all repeats skipped",
                    "completed_repeat_count": 0,
                    "repeat_results": repeat_results,
                }
            )
            ships.append(payload)
            continue

        first_completed = completed_repeats[0]
        aggregate_repeat_models = _aggregate_repeat_models(repeat_results)
        payload.update(
            {
                "status": "completed",
                "train_rows": first_completed.get("train_rows", 0),
                "val_rows": first_completed.get("val_rows", 0),
                "test_rows": first_completed.get("test_rows", 0),
                "train_timestamps": first_completed.get("train_timestamps", 0),
                "val_timestamps": first_completed.get("val_timestamps", 0),
                "test_timestamps": first_completed.get("test_timestamps", 0),
                "completed_repeat_count": len(completed_repeats),
                "models": aggregate_repeat_models,
                "repeat_results": repeat_results,
            }
        )
        ships.append(payload)

    aggregate_models = _aggregate_model_metrics(ships)
    completed = [item for item in ships if item.get("status") == "completed"]
    skipped = [item for item in ships if item.get("status") != "completed"]
    completed_repeats_total = sum(int(item.get("completed_repeat_count", 0)) for item in completed)
    requested_repeats_total = len(selected_own_mmsis) * repeat_count_value

    summary: dict[str, Any] = {
        "status": "completed",
        "input_path": str(input_path),
        "model_names": requested_models,
        "train_fraction": float(train_fraction),
        "val_fraction": float(val_fraction),
        "min_rows_per_ship": int(min_rows_per_ship),
        "repeat_count": repeat_count_value,
        "repeat_strategy": "timestamp_rotate",
        "random_seed": random_seed,
        "requested_own_ships": requested_own_mmsis,
        "candidate_own_ship_count": len(all_own_mmsis),
        "evaluated_own_ship_count": len(selected_own_mmsis),
        "completed_own_ship_count": len(completed),
        "skipped_own_ship_count": len(skipped),
        "completed_repeats_total": completed_repeats_total,
        "requested_repeats_total": requested_repeats_total,
        "ships": ships,
        "aggregate_models": aggregate_models,
    }

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    ship_metrics_csv_path = prefix.with_name(f"{prefix.name}_ship_metrics.csv")
    repeat_metrics_csv_path = prefix.with_name(f"{prefix.name}_repeat_metrics.csv")

    with ship_metrics_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "own_mmsi",
            "status",
            "reason",
            "row_count",
            "timestamp_count",
            "train_rows",
            "val_rows",
            "test_rows",
            "repeat_count",
            "completed_repeat_count",
            "model_name",
            "f1",
            "auroc",
            "auprc",
            "precision",
            "recall",
            "threshold",
            "f1_std_repeat",
            "auroc_std_repeat",
            "auprc_std_repeat",
            "f1_ci95_low_repeat",
            "f1_ci95_high_repeat",
            "f1_ci95_width_repeat",
            "metric_scope",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for ship in ships:
            models = ship.get("models", {})
            if not models:
                writer.writerow(
                    {
                        "own_mmsi": ship.get("own_mmsi"),
                        "status": ship.get("status"),
                        "reason": ship.get("reason", ""),
                        "row_count": ship.get("row_count", 0),
                        "timestamp_count": ship.get("timestamp_count", 0),
                        "train_rows": ship.get("train_rows", 0),
                        "val_rows": ship.get("val_rows", 0),
                        "test_rows": ship.get("test_rows", 0),
                        "repeat_count": ship.get("repeat_count", 0),
                        "completed_repeat_count": ship.get("completed_repeat_count", 0),
                        "metric_scope": "aggregate",
                    }
                )
                continue
            for model_name, metrics in models.items():
                writer.writerow(
                    {
                        "own_mmsi": ship.get("own_mmsi"),
                        "status": ship.get("status"),
                        "reason": ship.get("reason", ""),
                        "row_count": ship.get("row_count", 0),
                        "timestamp_count": ship.get("timestamp_count", 0),
                        "train_rows": ship.get("train_rows", 0),
                        "val_rows": ship.get("val_rows", 0),
                        "test_rows": ship.get("test_rows", 0),
                        "repeat_count": ship.get("repeat_count", 0),
                        "completed_repeat_count": ship.get("completed_repeat_count", 0),
                        "model_name": model_name,
                        "f1": metrics.get("f1"),
                        "auroc": metrics.get("auroc"),
                        "auprc": metrics.get("auprc"),
                        "precision": metrics.get("precision"),
                        "recall": metrics.get("recall"),
                        "threshold": metrics.get("threshold"),
                        "f1_std_repeat": metrics.get("f1_std_repeat"),
                        "auroc_std_repeat": metrics.get("auroc_std_repeat"),
                        "auprc_std_repeat": metrics.get("auprc_std_repeat"),
                        "f1_ci95_low_repeat": metrics.get("f1_ci95_low_repeat"),
                        "f1_ci95_high_repeat": metrics.get("f1_ci95_high_repeat"),
                        "f1_ci95_width_repeat": metrics.get("f1_ci95_width_repeat"),
                        "metric_scope": "aggregate",
                    }
                )

    with repeat_metrics_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "own_mmsi",
            "repeat_index",
            "rotation",
            "status",
            "reason",
            "row_count",
            "timestamp_count",
            "train_rows",
            "val_rows",
            "test_rows",
            "model_name",
            "f1",
            "auroc",
            "auprc",
            "precision",
            "recall",
            "threshold",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for ship in ships:
            repeat_results = ship.get("repeat_results", [])
            if not repeat_results:
                writer.writerow(
                    {
                        "own_mmsi": ship.get("own_mmsi"),
                        "status": ship.get("status"),
                        "reason": ship.get("reason", ""),
                        "row_count": ship.get("row_count", 0),
                        "timestamp_count": ship.get("timestamp_count", 0),
                    }
                )
                continue
            for repeat in repeat_results:
                models = repeat.get("models", {})
                if not models:
                    writer.writerow(
                        {
                            "own_mmsi": ship.get("own_mmsi"),
                            "repeat_index": repeat.get("repeat_index", 0),
                            "rotation": repeat.get("rotation", 0),
                            "status": repeat.get("status", "skipped"),
                            "reason": repeat.get("reason", ""),
                            "row_count": ship.get("row_count", 0),
                            "timestamp_count": ship.get("timestamp_count", 0),
                            "train_rows": repeat.get("train_rows", 0),
                            "val_rows": repeat.get("val_rows", 0),
                            "test_rows": repeat.get("test_rows", 0),
                        }
                    )
                    continue
                for model_name, metrics in models.items():
                    writer.writerow(
                        {
                            "own_mmsi": ship.get("own_mmsi"),
                            "repeat_index": repeat.get("repeat_index", 0),
                            "rotation": repeat.get("rotation", 0),
                            "status": repeat.get("status", "completed"),
                            "reason": repeat.get("reason", ""),
                            "row_count": ship.get("row_count", 0),
                            "timestamp_count": ship.get("timestamp_count", 0),
                            "train_rows": repeat.get("train_rows", 0),
                            "val_rows": repeat.get("val_rows", 0),
                            "test_rows": repeat.get("test_rows", 0),
                            "model_name": model_name,
                            "f1": metrics.get("f1"),
                            "auroc": metrics.get("auroc"),
                            "auprc": metrics.get("auprc"),
                            "precision": metrics.get("precision"),
                            "recall": metrics.get("recall"),
                            "threshold": metrics.get("threshold"),
                        }
                    )

    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_md_path"] = str(summary_md_path)
    summary["ship_metrics_csv_path"] = str(ship_metrics_csv_path)
    summary["repeat_metrics_csv_path"] = str(repeat_metrics_csv_path)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_own_ship_case_eval_summary_markdown(summary), encoding="utf-8")
    return summary
