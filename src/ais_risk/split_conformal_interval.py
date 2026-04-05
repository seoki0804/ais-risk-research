from __future__ import annotations

import csv
import json
import math
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


def _clamp01(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def _discover_models(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []
    models: list[str] = []
    for key in rows[0].keys():
        if key.endswith("_score"):
            models.append(key[: -len("_score")])
    return models


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _collect_scores_and_labels(rows: list[dict[str, str]], model_name: str) -> tuple[list[int], list[float], list[dict[str, str]], int]:
    labels: list[int] = []
    scores: list[float] = []
    kept_rows: list[dict[str, str]] = []
    skipped = 0
    score_key = f"{model_name}_score"
    for row in rows:
        label = _safe_int(row.get("label_future_conflict"))
        score = _safe_float(row.get(score_key))
        if label is None or label not in (0, 1) or score is None:
            skipped += 1
            continue
        labels.append(int(label))
        scores.append(_clamp01(score))
        kept_rows.append(row)
    return labels, scores, kept_rows, skipped


def _compute_qhat(labels: list[int], scores: list[float], miscoverage_alpha: float) -> float:
    if not labels or len(labels) != len(scores):
        raise ValueError("Calibration labels and scores must be non-empty and aligned.")
    residuals = sorted(abs(float(label) - float(score)) for label, score in zip(labels, scores))
    n = len(residuals)
    rank = int(math.ceil((n + 1) * (1.0 - float(miscoverage_alpha))))
    rank = min(max(rank, 1), n)
    return float(residuals[rank - 1])


def _build_interval_rows(
    target_rows: list[dict[str, str]],
    model_name: str,
    qhat: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    labels, scores, kept_rows, skipped = _collect_scores_and_labels(target_rows, model_name=model_name)
    output_rows: list[dict[str, Any]] = []
    widths: list[float] = []
    hits = 0

    for row, label, score in zip(kept_rows, labels, scores):
        lower = _clamp01(score - float(qhat))
        upper = _clamp01(score + float(qhat))
        width = float(upper - lower)
        hit = 1 if (float(lower) <= float(label) <= float(upper)) else 0
        hits += hit
        widths.append(width)
        output_rows.append(
            {
                "timestamp": row.get("timestamp", ""),
                "own_mmsi": row.get("own_mmsi", ""),
                "target_mmsi": row.get("target_mmsi", ""),
                "label_future_conflict": str(label),
                "model": model_name,
                "raw_score": f"{float(score):.6f}",
                "score_lower": f"{float(lower):.6f}",
                "score_upper": f"{float(upper):.6f}",
                "interval_width": f"{float(width):.6f}",
                "coverage_hit": str(hit),
                "conformal_qhat": f"{float(qhat):.6f}",
            }
        )

    sample_count = len(output_rows)
    coverage = (hits / sample_count) if sample_count else 0.0
    return output_rows, {
        "status": "completed" if sample_count > 0 else "skipped",
        "sample_count": sample_count,
        "skipped_rows": skipped,
        "coverage": float(coverage),
        "under_coverage": float(1.0 - coverage) if sample_count else 0.0,
        "mean_interval_width": float(sum(widths) / len(widths)) if widths else 0.0,
        "qhat": float(qhat),
    }


def build_split_conformal_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Split Conformal Interval Summary",
        "",
        "## Inputs",
        "",
        f"- calibration_predictions_csv: `{summary['calibration_predictions_csv_path']}`",
        f"- target_predictions_csv: `{summary['target_predictions_csv_path']}`",
        f"- models: `{', '.join(summary['model_names'])}`",
        f"- miscoverage_alpha: `{summary['miscoverage_alpha']:.4f}`",
        "",
        "## Model Metrics",
        "",
        "| Model | Status | Samples | SkippedRows | qhat | Coverage | UnderCoverage | MeanIntervalWidth |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model_name in summary["model_names"]:
        metrics = summary["models"].get(model_name, {})
        lines.append(
            "| {model} | {status} | {samples} | {skipped} | {qhat} | {coverage} | {under} | {width} |".format(
                model=model_name,
                status=metrics.get("status", "unknown"),
                samples=metrics.get("sample_count", 0),
                skipped=metrics.get("skipped_rows", 0),
                qhat=_format_metric(metrics.get("qhat", 0.0)),
                coverage=_format_metric(metrics.get("coverage", 0.0)),
                under=_format_metric(metrics.get("under_coverage", 0.0)),
                width=_format_metric(metrics.get("mean_interval_width", 0.0)),
            )
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- summary_json: `{summary['summary_json_path']}`",
            f"- summary_md: `{summary['summary_md_path']}`",
            f"- interval_csv: `{summary['interval_csv_path']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_split_conformal_interval(
    calibration_predictions_csv_path: str | Path,
    target_predictions_csv_path: str | Path,
    output_prefix: str | Path,
    model_names: list[str] | None = None,
    miscoverage_alpha: float = 0.05,
) -> dict[str, Any]:
    if not 0.0 < float(miscoverage_alpha) < 1.0:
        raise ValueError("miscoverage_alpha must be in (0, 1).")

    calibration_path = Path(calibration_predictions_csv_path)
    target_path = Path(target_predictions_csv_path)

    with calibration_path.open("r", encoding="utf-8", newline="") as handle:
        calibration_rows = [dict(row) for row in csv.DictReader(handle)]
    with target_path.open("r", encoding="utf-8", newline="") as handle:
        target_rows = [dict(row) for row in csv.DictReader(handle)]

    if not calibration_rows:
        raise ValueError("Calibration predictions CSV is empty.")
    if not target_rows:
        raise ValueError("Target predictions CSV is empty.")

    discovered_models = [name for name in _discover_models(calibration_rows) if name in _discover_models(target_rows)]
    resolved_models = model_names or discovered_models
    if not resolved_models:
        raise ValueError("No overlapping models discovered between calibration and target prediction CSVs.")

    all_rows: list[dict[str, Any]] = []
    model_metrics: dict[str, Any] = {}

    for model_name in resolved_models:
        calibration_labels, calibration_scores, _, calibration_skipped = _collect_scores_and_labels(
            calibration_rows, model_name=model_name
        )
        if not calibration_labels:
            model_metrics[model_name] = {
                "status": "skipped",
                "reason": "No valid calibration label/score pairs.",
                "sample_count": 0,
                "skipped_rows": calibration_skipped,
                "coverage": 0.0,
                "under_coverage": 0.0,
                "mean_interval_width": 0.0,
                "qhat": 0.0,
            }
            continue
        qhat = _compute_qhat(
            labels=calibration_labels,
            scores=calibration_scores,
            miscoverage_alpha=float(miscoverage_alpha),
        )
        interval_rows, metrics = _build_interval_rows(target_rows, model_name=model_name, qhat=qhat)
        all_rows.extend(interval_rows)
        model_metrics[model_name] = metrics

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    interval_csv_path = prefix.with_name(f"{prefix.name}_intervals.csv")

    with interval_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "timestamp",
            "own_mmsi",
            "target_mmsi",
            "label_future_conflict",
            "model",
            "raw_score",
            "score_lower",
            "score_upper",
            "interval_width",
            "coverage_hit",
            "conformal_qhat",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    summary: dict[str, Any] = {
        "status": "completed",
        "calibration_predictions_csv_path": str(calibration_path),
        "target_predictions_csv_path": str(target_path),
        "model_names": resolved_models,
        "miscoverage_alpha": float(miscoverage_alpha),
        "models": model_metrics,
        "interval_rows": len(all_rows),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "interval_csv_path": str(interval_csv_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_split_conformal_summary_markdown(summary), encoding="utf-8")
    return summary
