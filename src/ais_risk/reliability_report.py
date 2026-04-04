from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _parse_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _recommendation_map(path: str | Path) -> dict[str, str]:
    rows = _parse_csv_rows(path)
    mapping: dict[str, str] = {}
    for row in rows:
        dataset = str(row.get("dataset", "")).strip()
        model = str(row.get("model_name", "")).strip()
        if dataset and model:
            mapping[dataset] = model
    return mapping


def _bin_index(score: float, num_bins: int) -> int:
    if score <= 0.0:
        return 0
    if score >= 1.0:
        return num_bins - 1
    return min(num_bins - 1, int(score * num_bins))


def _build_bins(labels: list[int], scores: list[float], num_bins: int) -> list[dict[str, Any]]:
    buckets = [{"count": 0, "score_sum": 0.0, "label_sum": 0.0} for _ in range(num_bins)]
    for label, score in zip(labels, scores):
        index = _bin_index(float(score), num_bins=num_bins)
        bucket = buckets[index]
        bucket["count"] += 1
        bucket["score_sum"] += float(score)
        bucket["label_sum"] += float(label)
    rows: list[dict[str, Any]] = []
    for index, bucket in enumerate(buckets):
        count = int(bucket["count"])
        avg_score = (bucket["score_sum"] / count) if count > 0 else None
        empirical_rate = (bucket["label_sum"] / count) if count > 0 else None
        gap_abs = abs(empirical_rate - avg_score) if (avg_score is not None and empirical_rate is not None) else None
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


def _ece(bin_rows: list[dict[str, Any]], sample_count: int) -> float:
    if sample_count <= 0:
        return 0.0
    total = 0.0
    for row in bin_rows:
        if int(row["count"]) <= 0 or row["gap_abs"] is None:
            continue
        total += (int(row["count"]) / sample_count) * float(row["gap_abs"])
    return float(total)


def _brier(labels: list[int], scores: list[float]) -> float:
    if not labels:
        return 0.0
    total = 0.0
    for label, score in zip(labels, scores):
        diff = float(score) - float(label)
        total += diff * diff
    return float(total / len(labels))


def _collect_labels_scores(predictions_csv_path: str | Path, model_name: str) -> tuple[list[int], list[float]]:
    labels: list[int] = []
    scores: list[float] = []
    score_key = f"{model_name}_score"
    for row in _parse_csv_rows(predictions_csv_path):
        label = row.get("label_future_conflict")
        score = _safe_float(row.get(score_key))
        if label not in ("0", "1") or score is None:
            continue
        labels.append(int(label))
        scores.append(min(1.0, max(0.0, float(score))))
    return labels, scores


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _plot_reliability(bin_rows: list[dict[str, Any]], output_path: Path, title: str) -> None:
    xs = [float(row["avg_score"]) for row in bin_rows if row["avg_score"] is not None]
    ys = [float(row["empirical_rate"]) for row in bin_rows if row["empirical_rate"] is not None]
    counts = [int(row["count"]) for row in bin_rows if row["avg_score"] is not None and row["empirical_rate"] is not None]

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1.0, label="perfect")
    if xs:
        ax.scatter(xs, ys, s=[max(20, count * 1.5) for count in counts], alpha=0.8, color="#1f77b4", label="bins")
        ax.plot(xs, ys, color="#1f77b4", linewidth=1.2)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Empirical positive rate")
    ax.set_title(title)
    ax.grid(alpha=0.2)
    ax.legend(loc="lower right")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def run_reliability_report_for_recommended_models(
    recommendation_csv_path: str | Path,
    run_manifest_csv_path: str | Path,
    output_root: str | Path,
    num_bins: int = 10,
) -> dict[str, Any]:
    if int(num_bins) < 2:
        raise ValueError("num_bins must be >= 2")

    output_root_path = Path(output_root).resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)
    recommendation_map = _recommendation_map(recommendation_csv_path)
    run_manifest_rows = _parse_csv_rows(run_manifest_csv_path)

    summary_rows: list[dict[str, Any]] = []
    for run_row in run_manifest_rows:
        leaderboard_csv_path = run_row.get("leaderboard_csv_path", "")
        if not leaderboard_csv_path:
            continue
        leaderboard_rows = _parse_csv_rows(leaderboard_csv_path)
        if not leaderboard_rows:
            continue
        dataset = str(leaderboard_rows[0].get("dataset", "")).strip()
        model_name = recommendation_map.get(dataset, "")
        if not model_name:
            continue
        region = str(run_row.get("region", "")).strip()
        seed = int(str(run_row.get("seed", "0") or "0"))
        selected = [row for row in leaderboard_rows if row.get("model_name") == model_name and row.get("status") == "completed"]
        if not selected:
            continue
        predictions_csv = selected[0].get("predictions_csv_path", "")
        if not predictions_csv:
            continue
        labels, scores = _collect_labels_scores(predictions_csv, model_name=model_name)
        if not labels:
            continue
        summary_rows.append(
            {
                "region": region,
                "dataset": dataset,
                "seed": seed,
                "model_name": model_name,
                "sample_count": len(labels),
                "positive_rate": float(sum(labels) / len(labels)),
                "labels": labels,
                "scores": scores,
            }
        )

    region_rows: list[dict[str, Any]] = []
    region_bin_rows: list[dict[str, Any]] = []
    for region in sorted({row["region"] for row in summary_rows}):
        candidates = [row for row in summary_rows if row["region"] == region]
        if not candidates:
            continue
        dataset = str(candidates[0]["dataset"])
        model_name = str(candidates[0]["model_name"])
        labels: list[int] = []
        scores: list[float] = []
        for row in candidates:
            labels.extend(row["labels"])
            scores.extend(row["scores"])

        bins = _build_bins(labels=labels, scores=scores, num_bins=int(num_bins))
        ece_value = _ece(bins, sample_count=len(labels))
        brier_value = _brier(labels, scores)
        figure_path = output_root_path / f"{region}_recommended_reliability.png"
        _plot_reliability(
            bin_rows=bins,
            output_path=figure_path,
            title=f"{region}: {model_name} reliability",
        )
        for row in bins:
            region_bin_rows.append({"region": region, "dataset": dataset, "model_name": model_name, **row})
        region_rows.append(
            {
                "region": region,
                "dataset": dataset,
                "model_name": model_name,
                "seed_runs": len(candidates),
                "sample_count": len(labels),
                "positive_rate": float(sum(labels) / len(labels)),
                "ece": ece_value,
                "brier_score": brier_value,
                "figure_path": str(figure_path),
            }
        )

    region_summary_csv_path = output_root_path / "reliability_recommended_region_summary.csv"
    region_bins_csv_path = output_root_path / "reliability_recommended_bins.csv"
    summary_md_path = output_root_path / "reliability_recommended_summary.md"
    summary_json_path = output_root_path / "reliability_recommended_summary.json"

    _write_csv(
        region_summary_csv_path,
        region_rows,
        ["region", "dataset", "model_name", "seed_runs", "sample_count", "positive_rate", "ece", "brier_score", "figure_path"],
    )
    _write_csv(
        region_bins_csv_path,
        region_bin_rows,
        ["region", "dataset", "model_name", "bin_index", "bin_lower", "bin_upper", "count", "avg_score", "empirical_rate", "gap_abs"],
    )

    lines = [
        "# Reliability Summary (Recommended Models)",
        "",
        "## Inputs",
        "",
        f"- recommendation_csv: `{Path(recommendation_csv_path).resolve()}`",
        f"- run_manifest_csv: `{Path(run_manifest_csv_path).resolve()}`",
        f"- num_bins: `{int(num_bins)}`",
        "",
        "## Region Summary",
        "",
        "| Region | Dataset | Model | Seed Runs | Samples | Positive Rate | ECE | Brier | Figure |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in region_rows:
        lines.append(
            "| {region} | {dataset} | {model} | {runs} | {samples} | {pr:.4f} | {ece:.4f} | {brier:.4f} | `{fig}` |".format(
                region=row["region"],
                dataset=row["dataset"],
                model=row["model_name"],
                runs=row["seed_runs"],
                samples=row["sample_count"],
                pr=float(row["positive_rate"]),
                ece=float(row["ece"]),
                brier=float(row["brier_score"]),
                fig=row["figure_path"],
            )
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- region_summary_csv: `{region_summary_csv_path}`",
            f"- region_bins_csv: `{region_bins_csv_path}`",
            f"- summary_md: `{summary_md_path}`",
            f"- summary_json: `{summary_json_path}`",
            "",
        ]
    )
    summary_md_path.write_text("\n".join(lines), encoding="utf-8")
    summary: dict[str, Any] = {
        "status": "completed",
        "region_count": len(region_rows),
        "num_bins": int(num_bins),
        "region_summary_csv_path": str(region_summary_csv_path),
        "region_bins_csv_path": str(region_bins_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
