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
            model_name = key[: -len("_score")]
            models.append(model_name)
    return models


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _bin_index(score: float, num_bins: int) -> int:
    if score <= 0.0:
        return 0
    if score >= 1.0:
        return num_bins - 1
    return min(num_bins - 1, int(score * num_bins))


def _build_calibration_bins(labels: list[int], scores: list[float], num_bins: int) -> list[dict[str, Any]]:
    buckets = [{"count": 0, "score_sum": 0.0, "label_sum": 0.0} for _ in range(num_bins)]
    for label, score in zip(labels, scores):
        index = _bin_index(score, num_bins=num_bins)
        bucket = buckets[index]
        bucket["count"] += 1
        bucket["score_sum"] += float(score)
        bucket["label_sum"] += float(label)

    rows: list[dict[str, Any]] = []
    for index, bucket in enumerate(buckets):
        count = int(bucket["count"])
        avg_score = (bucket["score_sum"] / count) if count else None
        empirical_rate = (bucket["label_sum"] / count) if count else None
        gap_abs = abs(empirical_rate - avg_score) if (count and avg_score is not None and empirical_rate is not None) else None
        rows.append(
            {
                "bin_index": index,
                "bin_lower": index / num_bins,
                "bin_upper": (index + 1) / num_bins,
                "count": count,
                "avg_score": avg_score,
                "empirical_rate": empirical_rate,
                "gap_abs": gap_abs,
            }
        )
    return rows


def _ece_from_bins(bin_rows: list[dict[str, Any]], sample_count: int) -> float:
    if sample_count <= 0:
        return 0.0
    weighted_gap = 0.0
    for row in bin_rows:
        count = int(row["count"])
        gap_abs = row.get("gap_abs")
        if count <= 0 or gap_abs is None:
            continue
        weighted_gap += (count / sample_count) * float(gap_abs)
    return float(weighted_gap)


def _mce_from_bins(bin_rows: list[dict[str, Any]]) -> float:
    max_gap = 0.0
    for row in bin_rows:
        gap_abs = row.get("gap_abs")
        if gap_abs is None:
            continue
        max_gap = max(max_gap, float(gap_abs))
    return float(max_gap)


def _brier_score(labels: list[int], scores: list[float]) -> float:
    if not labels:
        return 0.0
    total = 0.0
    for label, score in zip(labels, scores):
        diff = float(score) - float(label)
        total += diff * diff
    return float(total / len(labels))


def _collect_model_samples(
    rows: list[dict[str, str]],
    model_name: str,
) -> tuple[list[int], list[float], int]:
    labels: list[int] = []
    scores: list[float] = []
    skipped = 0
    score_key = f"{model_name}_score"
    for row in rows:
        label = _safe_int(row.get("label_future_conflict"))
        score = _safe_float(row.get(score_key))
        if label is None or label not in (0, 1) or score is None:
            skipped += 1
            continue
        labels.append(int(label))
        scores.append(min(1.0, max(0.0, float(score))))
    return labels, scores, skipped


def build_calibration_eval_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Calibration Evaluation Summary",
        "",
        "## Inputs",
        "",
        f"- predictions_csv: `{summary['predictions_csv_path']}`",
        f"- models: `{', '.join(summary['model_names'])}`",
        f"- bin_count: `{summary['bin_count']}`",
        "",
        "## Model Calibration Metrics",
        "",
        "| Model | Status | Samples | SkippedRows | Brier | ECE | MCE | MeanScore | PositiveRate |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_name in summary["model_names"]:
        metrics = summary["models"].get(model_name, {})
        lines.append(
            "| {model} | {status} | {samples} | {skipped} | {brier} | {ece} | {mce} | {mean_score} | {positive_rate} |".format(
                model=model_name,
                status=metrics.get("status", "unknown"),
                samples=metrics.get("sample_count", 0),
                skipped=metrics.get("skipped_rows", 0),
                brier=_format_metric(metrics.get("brier_score", 0.0)),
                ece=_format_metric(metrics.get("ece", 0.0)),
                mce=_format_metric(metrics.get("mce", 0.0)),
                mean_score=_format_metric(metrics.get("mean_score", 0.0)),
                positive_rate=_format_metric(metrics.get("positive_rate", 0.0)),
            )
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- summary_json: `{summary['summary_json_path']}`",
            f"- summary_md: `{summary['summary_md_path']}`",
            f"- calibration_bins_csv: `{summary['calibration_bins_csv_path']}`",
            f"- calibration_bin_rows: `{summary['calibration_bin_rows']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_calibration_evaluation(
    predictions_csv_path: str | Path,
    output_prefix: str | Path,
    model_names: list[str] | None = None,
    num_bins: int = 10,
) -> dict[str, Any]:
    if int(num_bins) < 2:
        raise ValueError("num_bins must be >= 2.")
    if int(num_bins) > 100:
        raise ValueError("num_bins must be <= 100.")

    predictions_path = Path(predictions_csv_path)
    with predictions_path.open("r", encoding="utf-8", newline="") as handle:
        prediction_rows = [dict(row) for row in csv.DictReader(handle)]
    if not prediction_rows:
        raise ValueError("Predictions CSV is empty.")

    resolved_models = model_names or _prediction_models(prediction_rows)
    if not resolved_models:
        raise ValueError("No model score columns discovered from predictions CSV.")

    all_bin_rows: list[dict[str, Any]] = []
    model_metrics: dict[str, Any] = {}
    for model_name in resolved_models:
        labels, scores, skipped = _collect_model_samples(prediction_rows, model_name=model_name)
        if not labels:
            model_metrics[model_name] = {
                "status": "skipped",
                "reason": "No valid label/score pairs.",
                "sample_count": 0,
                "skipped_rows": skipped,
                "brier_score": 0.0,
                "ece": 0.0,
                "mce": 0.0,
                "mean_score": 0.0,
                "positive_rate": 0.0,
            }
            continue
        bin_rows = _build_calibration_bins(labels=labels, scores=scores, num_bins=int(num_bins))
        for row in bin_rows:
            all_bin_rows.append(
                {
                    "model": model_name,
                    **row,
                }
            )
        model_metrics[model_name] = {
            "status": "completed",
            "sample_count": len(labels),
            "skipped_rows": skipped,
            "brier_score": _brier_score(labels, scores),
            "ece": _ece_from_bins(bin_rows, sample_count=len(labels)),
            "mce": _mce_from_bins(bin_rows),
            "mean_score": float(sum(scores) / len(scores)) if scores else 0.0,
            "positive_rate": float(sum(labels) / len(labels)) if labels else 0.0,
        }

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    calibration_bins_csv_path = prefix.with_name(f"{prefix.name}_bins.csv")

    with calibration_bins_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "model",
            "bin_index",
            "bin_lower",
            "bin_upper",
            "count",
            "avg_score",
            "empirical_rate",
            "gap_abs",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_bin_rows:
            writer.writerow(row)

    summary: dict[str, Any] = {
        "status": "completed",
        "predictions_csv_path": str(predictions_path),
        "model_names": resolved_models,
        "bin_count": int(num_bins),
        "models": model_metrics,
        "calibration_bin_rows": len(all_bin_rows),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "calibration_bins_csv_path": str(calibration_bins_csv_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_calibration_eval_summary_markdown(summary), encoding="utf-8")
    return summary
