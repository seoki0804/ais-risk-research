from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import NormalDist
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


def _discover_models_from_prediction_rows(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []
    models: list[str] = []
    for key in rows[0].keys():
        if key.endswith("_score"):
            model_name = key[: -len("_score")]
            models.append(model_name)
    return models


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _load_calibration_bins(rows: list[dict[str, str]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        model_name = str(row.get("model") or "").strip()
        if not model_name:
            continue
        grouped.setdefault(model_name, []).append(
            {
                "bin_index": _safe_int(row.get("bin_index")),
                "bin_lower": _safe_float(row.get("bin_lower")),
                "bin_upper": _safe_float(row.get("bin_upper")),
                "count": _safe_int(row.get("count")) or 0,
                "avg_score": _safe_float(row.get("avg_score")),
                "empirical_rate": _safe_float(row.get("empirical_rate")),
            }
        )
    for model_name in grouped:
        grouped[model_name].sort(key=lambda item: int(item.get("bin_index") or -1))
    return grouped


def _find_matching_bin(score: float, model_bins: list[dict[str, Any]]) -> dict[str, Any] | None:
    clipped = _clamp01(score)
    for item in model_bins:
        lower = item.get("bin_lower")
        upper = item.get("bin_upper")
        if lower is None or upper is None:
            continue
        if clipped == 1.0 and upper >= 1.0 and lower <= 1.0:
            return item
        if float(lower) <= clipped < float(upper):
            return item
    return None


def _wilson_interval(phat: float | None, count: int, z_value: float) -> tuple[float | None, float | None]:
    if phat is None or count <= 0:
        return None, None
    n = float(count)
    p = _clamp01(float(phat))
    z_sq = float(z_value) * float(z_value)
    denom = 1.0 + (z_sq / n)
    center = (p + (z_sq / (2.0 * n))) / denom
    margin = (float(z_value) * ((p * (1.0 - p) / n) + (z_sq / (4.0 * n * n))) ** 0.5) / denom
    return _clamp01(center - margin), _clamp01(center + margin)


def _build_sample_rows(
    prediction_rows: list[dict[str, str]],
    model_name: str,
    model_bins: list[dict[str, Any]],
    z_value: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    score_key = f"{model_name}_score"
    pred_key = f"{model_name}_pred"
    output_rows: list[dict[str, Any]] = []
    fallback_rows = 0
    skipped_rows = 0
    widths: list[float] = []
    means: list[float] = []
    raws: list[float] = []

    for row in prediction_rows:
        raw_score = _safe_float(row.get(score_key))
        label = _safe_int(row.get("label_future_conflict"))
        if raw_score is None:
            skipped_rows += 1
            continue
        raw = _clamp01(raw_score)
        matched = _find_matching_bin(raw, model_bins=model_bins)
        band_status = "calibrated"
        if matched is None or int(matched.get("count") or 0) <= 0 or matched.get("empirical_rate") is None:
            fallback_rows += 1
            mean_score = raw
            lower = raw
            upper = raw
            band_status = "fallback_raw_score"
            matched = matched or {
                "bin_index": None,
                "bin_lower": None,
                "bin_upper": None,
                "count": 0,
                "avg_score": None,
                "empirical_rate": None,
            }
        else:
            mean_score = _clamp01(float(matched["empirical_rate"]))
            lower, upper = _wilson_interval(
                phat=float(matched["empirical_rate"]),
                count=int(matched["count"]),
                z_value=float(z_value),
            )
            lower = raw if lower is None else lower
            upper = raw if upper is None else upper

        width = float(upper) - float(lower)
        widths.append(width)
        means.append(float(mean_score))
        raws.append(raw)
        output_rows.append(
            {
                "timestamp": row.get("timestamp", ""),
                "own_mmsi": row.get("own_mmsi", ""),
                "target_mmsi": row.get("target_mmsi", ""),
                "label_future_conflict": "" if label is None else str(label),
                "model": model_name,
                "raw_score": f"{raw:.6f}",
                "raw_pred": row.get(pred_key, ""),
                "band_source_bin": "" if matched.get("bin_index") is None else str(matched["bin_index"]),
                "band_bin_lower": "" if matched.get("bin_lower") is None else f"{float(matched['bin_lower']):.6f}",
                "band_bin_upper": "" if matched.get("bin_upper") is None else f"{float(matched['bin_upper']):.6f}",
                "band_count": str(int(matched.get("count") or 0)),
                "band_avg_score": "" if matched.get("avg_score") is None else f"{float(matched['avg_score']):.6f}",
                "band_empirical_rate": "" if matched.get("empirical_rate") is None else f"{float(matched['empirical_rate']):.6f}",
                "score_lower": f"{float(lower):.6f}",
                "score_mean": f"{float(mean_score):.6f}",
                "score_upper": f"{float(upper):.6f}",
                "band_width": f"{width:.6f}",
                "band_status": band_status,
            }
        )

    sample_count = len(output_rows)
    return output_rows, {
        "status": "completed" if sample_count > 0 else "skipped",
        "sample_count": sample_count,
        "skipped_rows": skipped_rows,
        "fallback_rows": fallback_rows,
        "mean_raw_score": float(sum(raws) / len(raws)) if raws else 0.0,
        "mean_score_mean": float(sum(means) / len(means)) if means else 0.0,
        "mean_band_width": float(sum(widths) / len(widths)) if widths else 0.0,
        "mean_score_lower": float(sum(float(row["score_lower"]) for row in output_rows) / sample_count) if sample_count else 0.0,
        "mean_score_upper": float(sum(float(row["score_upper"]) for row in output_rows) / sample_count) if sample_count else 0.0,
    }


def build_uncertainty_band_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Uncertainty Band Summary",
        "",
        "## Inputs",
        "",
        f"- predictions_csv: `{summary['predictions_csv_path']}`",
        f"- calibration_bins_csv: `{summary['calibration_bins_csv_path']}`",
        f"- models: `{', '.join(summary['model_names'])}`",
        f"- confidence_level: `{summary['confidence_level']:.3f}`",
        f"- z_value: `{summary['z_value']:.4f}`",
        "",
        "## Model Band Metrics",
        "",
        "| Model | Status | Samples | SkippedRows | FallbackRows | MeanRaw | MeanBandMean | MeanBandWidth | MeanLower | MeanUpper |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_name in summary["model_names"]:
        metrics = summary["models"].get(model_name, {})
        lines.append(
            "| {model} | {status} | {samples} | {skipped} | {fallback} | {mean_raw} | {mean_band_mean} | {mean_band_width} | {mean_lower} | {mean_upper} |".format(
                model=model_name,
                status=metrics.get("status", "unknown"),
                samples=metrics.get("sample_count", 0),
                skipped=metrics.get("skipped_rows", 0),
                fallback=metrics.get("fallback_rows", 0),
                mean_raw=_format_metric(metrics.get("mean_raw_score", 0.0)),
                mean_band_mean=_format_metric(metrics.get("mean_score_mean", 0.0)),
                mean_band_width=_format_metric(metrics.get("mean_band_width", 0.0)),
                mean_lower=_format_metric(metrics.get("mean_score_lower", 0.0)),
                mean_upper=_format_metric(metrics.get("mean_score_upper", 0.0)),
            )
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- summary_json: `{summary['summary_json_path']}`",
            f"- summary_md: `{summary['summary_md_path']}`",
            f"- sample_bands_csv: `{summary['sample_bands_csv_path']}`",
            f"- sample_band_rows: `{summary['sample_band_rows']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_uncertainty_band(
    predictions_csv_path: str | Path,
    calibration_bins_csv_path: str | Path,
    output_prefix: str | Path,
    model_names: list[str] | None = None,
    confidence_level: float = 0.95,
) -> dict[str, Any]:
    if not 0.0 < float(confidence_level) < 1.0:
        raise ValueError("confidence_level must be in (0, 1).")

    predictions_path = Path(predictions_csv_path)
    calibration_path = Path(calibration_bins_csv_path)

    with predictions_path.open("r", encoding="utf-8", newline="") as handle:
        prediction_rows = [dict(row) for row in csv.DictReader(handle)]
    if not prediction_rows:
        raise ValueError("Predictions CSV is empty.")

    with calibration_path.open("r", encoding="utf-8", newline="") as handle:
        calibration_rows = [dict(row) for row in csv.DictReader(handle)]
    if not calibration_rows:
        raise ValueError("Calibration bins CSV is empty.")

    discovered_models = _discover_models_from_prediction_rows(prediction_rows)
    bins_by_model = _load_calibration_bins(calibration_rows)
    resolved_models = model_names or [name for name in discovered_models if name in bins_by_model]
    if not resolved_models:
        raise ValueError("No overlapping models found between predictions CSV and calibration bins CSV.")

    z_value = NormalDist().inv_cdf(0.5 + (float(confidence_level) / 2.0))
    all_rows: list[dict[str, Any]] = []
    model_metrics: dict[str, Any] = {}
    for model_name in resolved_models:
        sample_rows, metrics = _build_sample_rows(
            prediction_rows=prediction_rows,
            model_name=model_name,
            model_bins=bins_by_model.get(model_name, []),
            z_value=float(z_value),
        )
        all_rows.extend(sample_rows)
        model_metrics[model_name] = metrics

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    sample_bands_csv_path = prefix.with_name(f"{prefix.name}_sample_bands.csv")

    with sample_bands_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "timestamp",
            "own_mmsi",
            "target_mmsi",
            "label_future_conflict",
            "model",
            "raw_score",
            "raw_pred",
            "band_source_bin",
            "band_bin_lower",
            "band_bin_upper",
            "band_count",
            "band_avg_score",
            "band_empirical_rate",
            "score_lower",
            "score_mean",
            "score_upper",
            "band_width",
            "band_status",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    summary: dict[str, Any] = {
        "status": "completed",
        "predictions_csv_path": str(predictions_path),
        "calibration_bins_csv_path": str(calibration_path),
        "model_names": resolved_models,
        "confidence_level": float(confidence_level),
        "z_value": float(z_value),
        "models": model_metrics,
        "sample_band_rows": len(all_rows),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "sample_bands_csv_path": str(sample_bands_csv_path),
    }

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_uncertainty_band_summary_markdown(summary), encoding="utf-8")
    return summary
