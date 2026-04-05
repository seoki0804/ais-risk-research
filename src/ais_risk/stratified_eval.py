from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(str(value))
    except Exception:
        return None


def _prediction_models(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []
    models: list[str] = []
    row = rows[0]
    for key in row.keys():
        if key.endswith("_score"):
            name = key[: -len("_score")]
            if f"{name}_pred" in row:
                models.append(name)
    return models


def _key_of_row(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        str(row.get("timestamp", "")),
        str(row.get("own_mmsi", "")),
        str(row.get("target_mmsi", "")),
    )


def _distance_bin(distance_nm: float | None) -> str:
    if distance_nm is None:
        return "unknown"
    if distance_nm < 0.5:
        return "<0.5nm"
    if distance_nm < 1.0:
        return "0.5-1.0nm"
    if distance_nm < 2.0:
        return "1.0-2.0nm"
    if distance_nm < 4.0:
        return "2.0-4.0nm"
    return ">=4.0nm"


def _metrics_from_confusion(tp: int, tn: int, fp: int, fn: int) -> dict[str, Any]:
    total = tp + tn + fp + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / total if total else 0.0
    positive_rate = (tp + fn) / total if total else 0.0
    return {
        "count": total,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "positive_rate": positive_rate,
    }


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _aggregate_strata(
    rows: list[dict[str, Any]],
    model_name: str,
    strata_key: str,
) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, int]] = {}
    for row in rows:
        label = _safe_int(row.get("label_future_conflict"))
        pred = _safe_int(row.get(f"{model_name}_pred"))
        if label is None or pred is None:
            continue
        stratum = str(row.get(strata_key, "unknown") or "unknown")
        state = buckets.setdefault(stratum, {"tp": 0, "tn": 0, "fp": 0, "fn": 0})
        if label == 1 and pred == 1:
            state["tp"] += 1
        elif label == 0 and pred == 0:
            state["tn"] += 1
        elif label == 0 and pred == 1:
            state["fp"] += 1
        elif label == 1 and pred == 0:
            state["fn"] += 1

    output: list[dict[str, Any]] = []
    for stratum, state in sorted(buckets.items()):
        metrics = _metrics_from_confusion(state["tp"], state["tn"], state["fp"], state["fn"])
        output.append(
            {
                "model": model_name,
                "strata_key": strata_key,
                "stratum": stratum,
                **metrics,
            }
        )
    return output


def build_stratified_eval_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Stratified Evaluation Summary",
        "",
        "## Inputs",
        "",
        f"- pairwise_dataset_csv: `{summary['pairwise_dataset_csv_path']}`",
        f"- predictions_csv: `{summary['predictions_csv_path']}`",
        f"- models: `{', '.join(summary['model_names'])}`",
        f"- joined_rows: `{summary['joined_row_count']}`",
        "",
        "## Overall Metrics",
        "",
        "| Model | Count | Accuracy | Precision | Recall | F1 | PositiveRate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model_name in summary["model_names"]:
        metrics = summary.get("overall", {}).get(model_name, {})
        lines.append(
            "| {model} | {count} | {acc} | {p} | {r} | {f1} | {pr} |".format(
                model=model_name,
                count=metrics.get("count", 0),
                acc=_format_metric(metrics.get("accuracy", 0.0)),
                p=_format_metric(metrics.get("precision", 0.0)),
                r=_format_metric(metrics.get("recall", 0.0)),
                f1=_format_metric(metrics.get("f1", 0.0)),
                pr=_format_metric(metrics.get("positive_rate", 0.0)),
            )
        )

    lines.extend(
        [
            "",
            "## Stratified Outputs",
            "",
            f"- strata_metrics_csv: `{summary['strata_metrics_csv_path']}`",
            f"- strata_row_count: `{summary['strata_row_count']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_stratified_evaluation(
    pairwise_dataset_csv_path: str | Path,
    predictions_csv_path: str | Path,
    output_prefix: str | Path,
    model_names: list[str] | None = None,
) -> dict[str, Any]:
    pairwise_path = Path(pairwise_dataset_csv_path)
    predictions_path = Path(predictions_csv_path)

    with pairwise_path.open("r", encoding="utf-8", newline="") as handle:
        pairwise_rows = [dict(row) for row in csv.DictReader(handle)]
    with predictions_path.open("r", encoding="utf-8", newline="") as handle:
        prediction_rows = [dict(row) for row in csv.DictReader(handle)]
    if not pairwise_rows:
        raise ValueError("Pairwise dataset CSV is empty.")
    if not prediction_rows:
        raise ValueError("Predictions CSV is empty.")

    resolved_models = model_names or _prediction_models(prediction_rows)
    if not resolved_models:
        raise ValueError("No model columns discovered from predictions CSV.")

    meta_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in pairwise_rows:
        key = _key_of_row(row)
        meta_by_key[key] = {
            "encounter_type": str(row.get("encounter_type") or "unknown"),
            "distance_nm": _safe_float(row.get("distance_nm")),
        }

    joined_rows: list[dict[str, Any]] = []
    for row in prediction_rows:
        key = _key_of_row(row)
        meta = meta_by_key.get(key)
        if meta is None:
            continue
        payload = dict(row)
        payload["encounter_type"] = meta["encounter_type"]
        payload["distance_bin"] = _distance_bin(meta["distance_nm"])
        joined_rows.append(payload)
    if not joined_rows:
        raise ValueError("No joined rows between pairwise dataset and predictions.")

    overall_metrics: dict[str, Any] = {}
    strata_rows: list[dict[str, Any]] = []
    for model_name in resolved_models:
        confusion = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
        for row in joined_rows:
            label = _safe_int(row.get("label_future_conflict"))
            pred = _safe_int(row.get(f"{model_name}_pred"))
            if label is None or pred is None:
                continue
            if label == 1 and pred == 1:
                confusion["tp"] += 1
            elif label == 0 and pred == 0:
                confusion["tn"] += 1
            elif label == 0 and pred == 1:
                confusion["fp"] += 1
            elif label == 1 and pred == 0:
                confusion["fn"] += 1
        overall_metrics[model_name] = _metrics_from_confusion(
            confusion["tp"],
            confusion["tn"],
            confusion["fp"],
            confusion["fn"],
        )
        strata_rows.extend(_aggregate_strata(joined_rows, model_name=model_name, strata_key="encounter_type"))
        strata_rows.extend(_aggregate_strata(joined_rows, model_name=model_name, strata_key="distance_bin"))

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    strata_metrics_csv_path = prefix.with_name(f"{prefix.name}_strata_metrics.csv")

    with strata_metrics_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "model",
            "strata_key",
            "stratum",
            "count",
            "tp",
            "tn",
            "fp",
            "fn",
            "accuracy",
            "precision",
            "recall",
            "f1",
            "positive_rate",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in strata_rows:
            writer.writerow(row)

    summary: dict[str, Any] = {
        "status": "completed",
        "pairwise_dataset_csv_path": str(pairwise_path),
        "predictions_csv_path": str(predictions_path),
        "model_names": resolved_models,
        "joined_row_count": len(joined_rows),
        "overall": overall_metrics,
        "strata_row_count": len(strata_rows),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "strata_metrics_csv_path": str(strata_metrics_csv_path),
    }

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_stratified_eval_summary_markdown(summary), encoding="utf-8")
    return summary
