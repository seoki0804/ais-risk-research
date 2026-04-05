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


def _summarize_interval_csv(path: Path, baseline_name: str) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        model_name = str(row.get("model") or "").strip()
        if not model_name:
            continue
        grouped.setdefault(model_name, []).append(row)

    models: dict[str, Any] = {}
    for model_name, model_rows in grouped.items():
        widths: list[float] = []
        hits = 0
        valid = 0
        for row in model_rows:
            lower = _safe_float(row.get("score_lower"))
            upper = _safe_float(row.get("score_upper"))
            label = _safe_int(row.get("label_future_conflict"))
            if lower is None or upper is None or label is None:
                continue
            valid += 1
            widths.append(float(upper) - float(lower))
            if float(lower) <= float(label) <= float(upper):
                hits += 1
        coverage = (hits / valid) if valid else 0.0
        models[model_name] = {
            "baseline": baseline_name,
            "sample_count": valid,
            "coverage": float(coverage),
            "under_coverage": float(1.0 - coverage) if valid else 0.0,
            "mean_interval_width": float(sum(widths) / len(widths)) if widths else 0.0,
        }
    return {
        "baseline_name": baseline_name,
        "path": str(path),
        "models": models,
    }


def build_uncertainty_interval_compare_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Uncertainty Interval Baseline Comparison",
        "",
        "## Inputs",
        "",
        f"- baseline_a: `{summary['baseline_a_path']}`",
        f"- baseline_b: `{summary['baseline_b_path']}`",
        "",
        "Coverage below means empirical label-in-interval coverage on the target set, not a formal decision-threshold coverage claim.",
        "",
        "| Model | Baseline | Samples | EmpiricalLabelCoverage | UnderCoverage | MeanIntervalWidth |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in summary["rows"]:
        lines.append(
            "| {model} | {baseline} | {sample_count} | {coverage:.4f} | {under_coverage:.4f} | {mean_interval_width:.4f} |".format(
                **row
            )
        )
    return "\n".join(lines)


def run_uncertainty_interval_compare(
    baseline_a_csv_path: str | Path,
    baseline_b_csv_path: str | Path,
    output_prefix: str | Path,
    baseline_a_name: str = "wilson_bin",
    baseline_b_name: str = "split_conformal",
) -> dict[str, Any]:
    baseline_a = _summarize_interval_csv(Path(baseline_a_csv_path), baseline_name=baseline_a_name)
    baseline_b = _summarize_interval_csv(Path(baseline_b_csv_path), baseline_name=baseline_b_name)

    rows: list[dict[str, Any]] = []
    for source in (baseline_a, baseline_b):
        for model_name, metrics in source["models"].items():
            rows.append(
                {
                    "model": model_name,
                    "baseline": metrics["baseline"],
                    "sample_count": metrics["sample_count"],
                    "coverage": metrics["coverage"],
                    "under_coverage": metrics["under_coverage"],
                    "mean_interval_width": metrics["mean_interval_width"],
                }
            )

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    summary_csv_path = prefix.with_name(f"{prefix.name}_rows.csv")

    with summary_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["model", "baseline", "sample_count", "coverage", "under_coverage", "mean_interval_width"],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, Any] = {
        "status": "completed",
        "baseline_a_path": str(baseline_a["path"]),
        "baseline_b_path": str(baseline_b["path"]),
        "baseline_a_name": baseline_a_name,
        "baseline_b_name": baseline_b_name,
        "rows": rows,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "summary_csv_path": str(summary_csv_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_uncertainty_interval_compare_markdown(summary), encoding="utf-8")
    return summary
