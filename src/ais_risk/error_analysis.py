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


def _discover_models_from_prediction_rows(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []
    keys = list(rows[0].keys())
    models: list[str] = []
    for key in keys:
        if key.endswith("_score"):
            name = key[: -len("_score")]
            pred_key = f"{name}_pred"
            if pred_key in rows[0]:
                models.append(name)
    return models


def _build_model_error_rows(
    rows: list[dict[str, str]],
    model_name: str,
    top_k_each: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    score_key = f"{model_name}_score"
    pred_key = f"{model_name}_pred"
    tp = tn = fp = fn = 0
    fp_rows: list[dict[str, Any]] = []
    fn_rows: list[dict[str, Any]] = []

    for row in rows:
        label = _safe_int(row.get("label_future_conflict"))
        pred = _safe_int(row.get(pred_key))
        score = _safe_float(row.get(score_key))
        if label is None or pred is None or score is None:
            continue
        if label == 1 and pred == 1:
            tp += 1
        elif label == 0 and pred == 0:
            tn += 1
        elif label == 0 and pred == 1:
            fp += 1
            fp_rows.append(
                {
                    "model": model_name,
                    "error_type": "FP",
                    "timestamp": row.get("timestamp", ""),
                    "own_mmsi": row.get("own_mmsi", ""),
                    "target_mmsi": row.get("target_mmsi", ""),
                    "label": label,
                    "pred": pred,
                    "score": score,
                }
            )
        elif label == 1 and pred == 0:
            fn += 1
            fn_rows.append(
                {
                    "model": model_name,
                    "error_type": "FN",
                    "timestamp": row.get("timestamp", ""),
                    "own_mmsi": row.get("own_mmsi", ""),
                    "target_mmsi": row.get("target_mmsi", ""),
                    "label": label,
                    "pred": pred,
                    "score": score,
                }
            )

    fp_rows.sort(key=lambda item: float(item["score"]), reverse=True)
    fn_rows.sort(key=lambda item: float(item["score"]))
    selected = []
    for rank, item in enumerate(fp_rows[:top_k_each], start=1):
        payload = dict(item)
        payload["rank"] = rank
        selected.append(payload)
    for rank, item in enumerate(fn_rows[:top_k_each], start=1):
        payload = dict(item)
        payload["rank"] = rank
        selected.append(payload)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    total = tp + tn + fp + fn
    metrics = {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "total": total,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fp_rate": (fp / (fp + tn)) if (fp + tn) else 0.0,
        "fn_rate": (fn / (fn + tp)) if (fn + tp) else 0.0,
    }
    return selected, metrics


def build_error_analysis_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Benchmark Error Analysis Summary",
        "",
        "## Inputs",
        "",
        f"- predictions csv: `{summary['predictions_csv_path']}`",
        f"- models: `{', '.join(summary['model_names'])}`",
        f"- top_k_each: `{summary['top_k_each']}`",
        "",
        "## Model Metrics",
        "",
        "| Model | TP | TN | FP | FN | Precision | Recall | F1 | FP Rate | FN Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_name in summary["model_names"]:
        metrics = summary["models"].get(model_name, {})
        lines.append(
            (
                "| {model} | {tp} | {tn} | {fp} | {fn} | {precision:.4f} | {recall:.4f} | {f1:.4f} | "
                "{fp_rate:.4f} | {fn_rate:.4f} |"
            ).format(
                model=model_name,
                tp=metrics.get("tp", 0),
                tn=metrics.get("tn", 0),
                fp=metrics.get("fp", 0),
                fn=metrics.get("fn", 0),
                precision=float(metrics.get("precision", 0.0)),
                recall=float(metrics.get("recall", 0.0)),
                f1=float(metrics.get("f1", 0.0)),
                fp_rate=float(metrics.get("fp_rate", 0.0)),
                fn_rate=float(metrics.get("fn_rate", 0.0)),
            )
        )
    lines.extend(
        [
            "",
            "## Error Cases",
            "",
            f"- error cases csv: `{summary['error_cases_csv_path']}`",
            f"- total selected error rows: `{summary['selected_error_row_count']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_benchmark_error_analysis(
    predictions_csv_path: str | Path,
    output_prefix: str | Path,
    model_names: list[str] | None = None,
    top_k_each: int = 20,
) -> dict[str, Any]:
    predictions_path = Path(predictions_csv_path)
    with predictions_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError("Prediction CSV is empty.")

    resolved_models = model_names or _discover_models_from_prediction_rows(rows)
    if not resolved_models:
        raise ValueError("No model score/prediction columns found in predictions CSV.")

    selected_errors: list[dict[str, Any]] = []
    model_metrics: dict[str, Any] = {}
    for model_name in resolved_models:
        model_error_rows, metrics = _build_model_error_rows(rows, model_name=model_name, top_k_each=int(top_k_each))
        selected_errors.extend(model_error_rows)
        model_metrics[model_name] = metrics

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    error_cases_csv_path = prefix.with_name(f"{prefix.name}_cases.csv")

    with error_cases_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "model",
            "error_type",
            "rank",
            "timestamp",
            "own_mmsi",
            "target_mmsi",
            "label",
            "pred",
            "score",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in selected_errors:
            writer.writerow(row)

    summary: dict[str, Any] = {
        "status": "completed",
        "predictions_csv_path": str(predictions_path),
        "model_names": resolved_models,
        "top_k_each": int(top_k_each),
        "selected_error_row_count": len(selected_errors),
        "models": model_metrics,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "error_cases_csv_path": str(error_cases_csv_path),
    }

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_error_analysis_summary_markdown(summary), encoding="utf-8")
    return summary
