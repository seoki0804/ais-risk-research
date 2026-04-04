from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


SUMMARY_FIELDS = [
    "region",
    "dataset",
    "model_name",
    "seed",
    "sample_count",
    "positive_count",
    "negative_count",
    "tp",
    "fp",
    "tn",
    "fn",
    "fp_rate",
    "fn_rate",
    "predictions_csv_path",
]

TAXONOMY_FIELDS = [
    "region",
    "dataset",
    "model_name",
    "seed",
    "error_type",
    "dimension",
    "value",
    "count",
    "share_within_error_type",
]


def _parse_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _recommendation_map(path: str | Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in _parse_csv_rows(path):
        dataset = str(row.get("dataset", "")).strip()
        model = str(row.get("model_name", "")).strip()
        if dataset and model:
            mapping[dataset] = model
    return mapping


def _distance_bucket(value: str | None) -> str:
    try:
        distance = float(value)
    except Exception:
        return "unknown"
    if distance < 0.5:
        return "<0.5nm"
    if distance < 1.0:
        return "0.5-1.0nm"
    if distance < 2.0:
        return "1.0-2.0nm"
    if distance < 5.0:
        return "2.0-5.0nm"
    return ">=5.0nm"


def _tcpa_bucket(value: str | None) -> str:
    try:
        tcpa = float(value)
    except Exception:
        return "unknown"
    if tcpa < 0:
        return "<0min"
    if tcpa < 5:
        return "0-5min"
    if tcpa < 10:
        return "5-10min"
    if tcpa < 20:
        return "10-20min"
    return ">=20min"


def _prediction_map(predictions_csv_path: str | Path, model_name: str) -> dict[tuple[str, str, str], dict[str, int]]:
    out: dict[tuple[str, str, str], dict[str, int]] = {}
    pred_key = f"{model_name}_pred"
    for row in _parse_csv_rows(predictions_csv_path):
        key = (str(row.get("timestamp", "")), str(row.get("own_mmsi", "")), str(row.get("target_mmsi", "")))
        label = row.get("label_future_conflict")
        pred = row.get(pred_key)
        if label not in ("0", "1") or pred not in ("0", "1"):
            continue
        out[key] = {"label": int(label), "pred": int(pred)}
    return out


def _select_predictions_path(leaderboard_csv_path: str | Path, dataset: str, model_name: str) -> str:
    for row in _parse_csv_rows(leaderboard_csv_path):
        if str(row.get("dataset", "")) != dataset:
            continue
        if str(row.get("model_name", "")) != model_name:
            continue
        if str(row.get("status", "")) != "completed":
            continue
        return str(row.get("predictions_csv_path", ""))
    return ""


def run_error_taxonomy_for_recommended_models(
    input_paths_by_region: dict[str, str | Path],
    recommendation_csv_path: str | Path,
    run_manifest_csv_path: str | Path,
    output_root: str | Path,
    seed: int = 42,
) -> dict[str, Any]:
    output_root_path = Path(output_root).resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)
    recommendation_map = _recommendation_map(recommendation_csv_path)
    run_manifest_rows = _parse_csv_rows(run_manifest_csv_path)

    region_rows: list[dict[str, Any]] = []
    taxonomy_rows: list[dict[str, Any]] = []

    for region in sorted(input_paths_by_region.keys()):
        input_path = Path(input_paths_by_region[region]).resolve()
        dataset = input_path.stem
        model_name = recommendation_map.get(dataset, "")
        manifest = [row for row in run_manifest_rows if str(row.get("region", "")) == region and int(str(row.get("seed", "0"))) == int(seed)]
        if not model_name or not manifest:
            continue
        leaderboard_csv_path = manifest[0].get("leaderboard_csv_path", "")
        predictions_csv_path = _select_predictions_path(leaderboard_csv_path, dataset=dataset, model_name=model_name)
        if not predictions_csv_path:
            continue

        pred_map = _prediction_map(predictions_csv_path, model_name=model_name)
        feature_rows = _parse_csv_rows(input_path)
        tp = fp = tn = fn = 0
        error_records: list[dict[str, str]] = []
        for row in feature_rows:
            key = (str(row.get("timestamp", "")), str(row.get("own_mmsi", "")), str(row.get("target_mmsi", "")))
            payload = pred_map.get(key)
            if payload is None:
                continue
            label = int(payload["label"])
            pred = int(payload["pred"])
            if label == 1 and pred == 1:
                tp += 1
            elif label == 0 and pred == 1:
                fp += 1
                error_records.append({**row, "error_type": "fp"})
            elif label == 0 and pred == 0:
                tn += 1
            else:
                fn += 1
                error_records.append({**row, "error_type": "fn"})

        sample_count = tp + fp + tn + fn
        positive_count = tp + fn
        negative_count = tn + fp
        region_rows.append(
            {
                "region": region,
                "dataset": dataset,
                "model_name": model_name,
                "seed": int(seed),
                "sample_count": sample_count,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
                "fp_rate": (fp / max(1, negative_count)),
                "fn_rate": (fn / max(1, positive_count)),
                "predictions_csv_path": predictions_csv_path,
            }
        )

        dims = {
            "encounter_type": lambda item: str(item.get("encounter_type", "unknown") or "unknown"),
            "own_vessel_type": lambda item: str(item.get("own_vessel_type", "unknown") or "unknown"),
            "target_vessel_type": lambda item: str(item.get("target_vessel_type", "unknown") or "unknown"),
            "distance_bucket": lambda item: _distance_bucket(item.get("distance_nm")),
            "tcpa_bucket": lambda item: _tcpa_bucket(item.get("tcpa_min")),
        }
        for error_type in ("fp", "fn"):
            subset = [row for row in error_records if row.get("error_type") == error_type]
            total = len(subset)
            if total == 0:
                continue
            for dim_name, fn_value in dims.items():
                counts: dict[str, int] = {}
                for item in subset:
                    value = fn_value(item)
                    counts[value] = counts.get(value, 0) + 1
                for value, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
                    taxonomy_rows.append(
                        {
                            "region": region,
                            "dataset": dataset,
                            "model_name": model_name,
                            "seed": int(seed),
                            "error_type": error_type,
                            "dimension": dim_name,
                            "value": value,
                            "count": count,
                            "share_within_error_type": float(count / total),
                        }
                    )

    summary_csv_path = output_root_path / "error_taxonomy_region_summary.csv"
    taxonomy_csv_path = output_root_path / "error_taxonomy_details.csv"
    summary_md_path = output_root_path / "error_taxonomy_summary.md"
    summary_json_path = output_root_path / "error_taxonomy_summary.json"

    _write_csv(summary_csv_path, region_rows, SUMMARY_FIELDS)
    _write_csv(taxonomy_csv_path, taxonomy_rows, TAXONOMY_FIELDS)

    lines = [
        "# Error Taxonomy (Recommended Models)",
        "",
        "## Region Summary",
        "",
        "| Region | Dataset | Model | Seed | Samples | FP | FN | FP Rate | FN Rate |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in region_rows:
        lines.append(
            "| {region} | {dataset} | {model} | {seed} | {samples} | {fp} | {fn} | {fpr:.4f} | {fnr:.4f} |".format(
                region=row["region"],
                dataset=row["dataset"],
                model=row["model_name"],
                seed=row["seed"],
                samples=row["sample_count"],
                fp=row["fp"],
                fn=row["fn"],
                fpr=float(row["fp_rate"]),
                fnr=float(row["fn_rate"]),
            )
        )
    lines.extend(
        [
            "",
            "## Top Error Patterns (per region, FP/FN, top 5)",
            "",
        ]
    )
    for region in sorted({row["region"] for row in taxonomy_rows}):
        for error_type in ("fp", "fn"):
            subset = [row for row in taxonomy_rows if row["region"] == region and row["error_type"] == error_type]
            if not subset:
                continue
            subset.sort(key=lambda row: (-int(row["count"]), row["dimension"], row["value"]))
            lines.append(f"### {region} {error_type.upper()}")
            lines.append("")
            lines.append("| Dimension | Value | Count | Share |")
            lines.append("|---|---|---:|---:|")
            for row in subset[:5]:
                lines.append(
                    "| {dim} | {val} | {count} | {share:.4f} |".format(
                        dim=row["dimension"],
                        val=row["value"],
                        count=row["count"],
                        share=float(row["share_within_error_type"]),
                    )
                )
            lines.append("")
    lines.extend(
        [
            "## Outputs",
            "",
            f"- summary_csv: `{summary_csv_path}`",
            f"- taxonomy_csv: `{taxonomy_csv_path}`",
            f"- summary_md: `{summary_md_path}`",
            f"- summary_json: `{summary_json_path}`",
            "",
        ]
    )
    summary_md_path.write_text("\n".join(lines), encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "completed",
        "seed": int(seed),
        "region_count": len(region_rows),
        "summary_csv_path": str(summary_csv_path),
        "taxonomy_csv_path": str(taxonomy_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
