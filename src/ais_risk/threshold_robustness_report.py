from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import mean, stdev
from typing import Any


DETAIL_FIELDS = [
    "region",
    "dataset",
    "seed",
    "model_name",
    "profile",
    "fp_cost",
    "fn_cost",
    "recommended_threshold",
    "best_threshold",
    "best_cost",
    "recommended_cost",
    "regret",
    "fp_at_rec",
    "fn_at_rec",
    "fp_at_best",
    "fn_at_best",
    "predictions_csv_path",
]

SUMMARY_FIELDS = [
    "dataset",
    "model_name",
    "profile",
    "runs",
    "mean_best_threshold",
    "std_best_threshold",
    "mean_recommended_threshold",
    "mean_regret",
    "max_regret",
    "mean_best_cost",
    "mean_recommended_cost",
    "regret_zero_rate",
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


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def _std(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    return float(stdev(values))


def _recommendation_map(path: str | Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in _parse_csv_rows(path):
        dataset = str(row.get("dataset", "")).strip()
        model_name = str(row.get("model_name", "")).strip()
        if dataset and model_name:
            mapping[dataset] = model_name
    return mapping


def _dataset_for_region(recommendation_map: dict[str, str], region: str) -> str | None:
    matches = [dataset for dataset in recommendation_map.keys() if dataset.startswith(f"{region}_")]
    if len(matches) == 1:
        return matches[0]
    exact = f"{region}_pooled_pairwise"
    if exact in recommendation_map:
        return exact
    return matches[0] if matches else None


def _select_recommended_prediction_row(
    leaderboard_csv_path: str | Path,
    dataset: str,
    model_name: str,
) -> dict[str, str] | None:
    for row in _parse_csv_rows(leaderboard_csv_path):
        if str(row.get("dataset", "")) != dataset:
            continue
        if str(row.get("model_name", "")) != model_name:
            continue
        if str(row.get("status", "")) != "completed":
            continue
        return row
    return None


def _prediction_rows(path: str | Path, model_name: str) -> list[tuple[float, int]]:
    score_key = f"{model_name}_score"
    rows: list[tuple[float, int]] = []
    for row in _parse_csv_rows(path):
        score = _safe_float(row.get(score_key))
        label = _safe_float(row.get("label_future_conflict"))
        if score is None or label not in (0.0, 1.0):
            continue
        rows.append((float(score), int(label)))
    return rows


def _cost_counts(scores_labels: list[tuple[float, int]], threshold: float, fp_cost: float, fn_cost: float) -> tuple[float, int, int]:
    fp = fn = 0
    for score, label in scores_labels:
        pred = 1 if score >= threshold else 0
        if pred == 1 and label == 0:
            fp += 1
        elif pred == 0 and label == 1:
            fn += 1
    cost = float(fp_cost * fp + fn_cost * fn)
    return cost, fp, fn


def _parse_profiles(raw: str) -> list[tuple[str, float, float]]:
    profiles: list[tuple[str, float, float]] = []
    for token in str(raw).split(","):
        item = token.strip()
        if not item:
            continue
        parts = item.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid profile format: {item}. expected name:fp_cost:fn_cost")
        name = parts[0].strip()
        fp_cost = float(parts[1])
        fn_cost = float(parts[2])
        profiles.append((name, fp_cost, fn_cost))
    if not profiles:
        raise ValueError("No cost profile parsed.")
    return profiles


def run_threshold_robustness_report(
    recommendation_csv_path: str | Path,
    run_manifest_csv_path: str | Path,
    output_prefix: str | Path,
    threshold_grid: list[float] | None = None,
    cost_profiles: str = "balanced:1:1,fn_heavy:1:3,fn_very_heavy:1:5,fp_heavy:3:1",
) -> dict[str, Any]:
    recommendation_map = _recommendation_map(recommendation_csv_path)
    manifest_rows = _parse_csv_rows(run_manifest_csv_path)
    profiles = _parse_profiles(cost_profiles)
    grid = threshold_grid if threshold_grid is not None else [step / 100.0 for step in range(5, 96, 5)]

    detail_rows: list[dict[str, Any]] = []
    for manifest in manifest_rows:
        region = str(manifest.get("region", "")).strip()
        seed_value = int(_safe_float(manifest.get("seed")) or 0)
        leaderboard_csv_path = str(manifest.get("leaderboard_csv_path", "")).strip()
        if not region or not leaderboard_csv_path:
            continue
        dataset = _dataset_for_region(recommendation_map, region=region)
        if not dataset:
            continue
        model_name = recommendation_map.get(dataset, "")
        if not model_name:
            continue
        selected = _select_recommended_prediction_row(
            leaderboard_csv_path=leaderboard_csv_path,
            dataset=dataset,
            model_name=model_name,
        )
        if not selected:
            continue
        predictions_csv_path = str(selected.get("predictions_csv_path", "")).strip()
        recommended_threshold = _safe_float(selected.get("threshold"))
        if not predictions_csv_path or recommended_threshold is None:
            continue

        scores_labels = _prediction_rows(predictions_csv_path, model_name=model_name)
        if not scores_labels:
            continue

        for profile_name, fp_cost, fn_cost in profiles:
            recommended_cost, fp_at_rec, fn_at_rec = _cost_counts(
                scores_labels=scores_labels,
                threshold=float(recommended_threshold),
                fp_cost=float(fp_cost),
                fn_cost=float(fn_cost),
            )
            candidates: list[tuple[float, float, int, int]] = []
            for threshold in grid:
                cost, fp_count, fn_count = _cost_counts(
                    scores_labels=scores_labels,
                    threshold=float(threshold),
                    fp_cost=float(fp_cost),
                    fn_cost=float(fn_cost),
                )
                candidates.append((cost, float(threshold), fp_count, fn_count))
            candidates.sort(key=lambda item: (item[0], abs(item[1] - float(recommended_threshold)), item[1]))
            best_cost, best_threshold, fp_at_best, fn_at_best = candidates[0]
            detail_rows.append(
                {
                    "region": region,
                    "dataset": dataset,
                    "seed": seed_value,
                    "model_name": model_name,
                    "profile": profile_name,
                    "fp_cost": float(fp_cost),
                    "fn_cost": float(fn_cost),
                    "recommended_threshold": float(recommended_threshold),
                    "best_threshold": float(best_threshold),
                    "best_cost": float(best_cost),
                    "recommended_cost": float(recommended_cost),
                    "regret": float(recommended_cost - best_cost),
                    "fp_at_rec": int(fp_at_rec),
                    "fn_at_rec": int(fn_at_rec),
                    "fp_at_best": int(fp_at_best),
                    "fn_at_best": int(fn_at_best),
                    "predictions_csv_path": predictions_csv_path,
                }
            )

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in detail_rows:
        key = (str(row["dataset"]), str(row["model_name"]), str(row["profile"]))
        grouped.setdefault(key, []).append(row)

    summary_rows: list[dict[str, Any]] = []
    for key in sorted(grouped.keys()):
        dataset, model_name, profile = key
        rows = grouped[key]
        best_thresholds = [float(row["best_threshold"]) for row in rows]
        rec_thresholds = [float(row["recommended_threshold"]) for row in rows]
        regrets = [float(row["regret"]) for row in rows]
        best_costs = [float(row["best_cost"]) for row in rows]
        rec_costs = [float(row["recommended_cost"]) for row in rows]
        summary_rows.append(
            {
                "dataset": dataset,
                "model_name": model_name,
                "profile": profile,
                "runs": len(rows),
                "mean_best_threshold": float(mean(best_thresholds)) if best_thresholds else None,
                "std_best_threshold": _std(best_thresholds) if best_thresholds else None,
                "mean_recommended_threshold": float(mean(rec_thresholds)) if rec_thresholds else None,
                "mean_regret": float(mean(regrets)) if regrets else None,
                "max_regret": max(regrets) if regrets else None,
                "mean_best_cost": float(mean(best_costs)) if best_costs else None,
                "mean_recommended_cost": float(mean(rec_costs)) if rec_costs else None,
                "regret_zero_rate": (sum(1 for item in regrets if math.isclose(item, 0.0, abs_tol=1e-12)) / len(regrets))
                if regrets
                else None,
            }
        )

    output_root = Path(output_prefix).resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    detail_csv_path = output_root.with_name(output_root.name + "_detail").with_suffix(".csv")
    summary_csv_path = output_root.with_name(output_root.name + "_summary").with_suffix(".csv")
    summary_md_path = output_root.with_suffix(".md")
    summary_json_path = output_root.with_suffix(".json")
    _write_csv(detail_csv_path, detail_rows, DETAIL_FIELDS)
    _write_csv(summary_csv_path, summary_rows, SUMMARY_FIELDS)

    lines = [
        "# Threshold Robustness Report (Recommended Models)",
        "",
        "## Inputs",
        "",
        f"- recommendation_csv: `{Path(recommendation_csv_path).resolve()}`",
        f"- run_manifest_csv: `{Path(run_manifest_csv_path).resolve()}`",
        f"- threshold_grid_size: `{len(grid)}`",
        f"- cost_profiles: `{cost_profiles}`",
        "",
        "## Summary",
        "",
        "| Dataset | Model | Profile | Runs | Mean Best Th | Mean Rec Th | Mean Regret | Max Regret | Regret=0 Rate |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {dataset} | {model} | {profile} | {runs} | {best_th} | {rec_th} | {mean_regret} | {max_regret} | {rz} |".format(
                dataset=row.get("dataset", ""),
                model=row.get("model_name", ""),
                profile=row.get("profile", ""),
                runs=row.get("runs", 0),
                best_th=_fmt(row.get("mean_best_threshold")),
                rec_th=_fmt(row.get("mean_recommended_threshold")),
                mean_regret=_fmt(row.get("mean_regret"), digits=3),
                max_regret=_fmt(row.get("max_regret"), digits=3),
                rz=_fmt(row.get("regret_zero_rate")),
            )
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- detail_csv: `{detail_csv_path}`",
            f"- summary_csv: `{summary_csv_path}`",
            f"- summary_md: `{summary_md_path}`",
            f"- summary_json: `{summary_json_path}`",
            "",
        ]
    )
    summary_md_path.write_text("\n".join(lines), encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "completed",
        "row_count_detail": len(detail_rows),
        "row_count_summary": len(summary_rows),
        "detail_csv_path": str(detail_csv_path),
        "summary_csv_path": str(summary_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
