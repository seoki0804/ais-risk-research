from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from math import sqrt
from typing import Any

from .all_models import run_all_supported_models


AGG_FIELDS = [
    "dataset",
    "model_family",
    "model_name",
    "runs",
    "f1_mean",
    "f1_std",
    "f1_ci95",
    "precision_mean",
    "precision_std",
    "recall_mean",
    "recall_std",
    "auroc_mean",
    "auroc_std",
    "auroc_ci95",
    "ece_mean",
    "ece_std",
    "ece_ci95",
    "brier_mean",
    "brier_std",
    "brier_ci95",
    "positive_count_mean",
]


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


def _ci95(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    return float(1.96 * _std(values) / sqrt(len(values)))


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


def _winner_rows(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_dataset_seed: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        if str(row.get("status", "")) != "completed":
            continue
        dataset = str(row.get("dataset", ""))
        seed = int(row.get("seed", 0))
        by_dataset_seed[(dataset, seed)].append(row)

    winners: list[dict[str, Any]] = []
    for (dataset, seed), rows in sorted(by_dataset_seed.items()):
        rows.sort(key=lambda item: (-float(item.get("f1", -1.0)), str(item.get("model_name", ""))))
        winner = rows[0]
        winners.append(
            {
                "dataset": dataset,
                "seed": seed,
                "model_family": winner.get("model_family", ""),
                "model_name": winner.get("model_name", ""),
                "f1": winner.get("f1"),
                "auroc": winner.get("auroc"),
                "ece": winner.get("ece"),
            }
        )
    return winners


def _winner_summary_rows(winner_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str, str], int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    for row in winner_rows:
        dataset = str(row["dataset"])
        key = (dataset, str(row["model_family"]), str(row["model_name"]))
        counts[key] += 1
        totals[dataset] += 1

    out: list[dict[str, Any]] = []
    for (dataset, family, model), count in sorted(counts.items()):
        total = totals.get(dataset, 0)
        out.append(
            {
                "dataset": dataset,
                "model_family": family,
                "model_name": model,
                "wins": count,
                "total_seeds": total,
                "win_rate": (float(count) / float(total)) if total > 0 else 0.0,
            }
        )
    return out


def _recommendation_rows(
    aggregate_rows: list[dict[str, Any]],
    f1_tolerance: float,
    max_ece_mean: float | None,
) -> list[dict[str, Any]]:
    by_dataset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in aggregate_rows:
        by_dataset[str(row.get("dataset", ""))].append(row)

    recommendations: list[dict[str, Any]] = []
    for dataset in sorted(by_dataset.keys()):
        rows = by_dataset[dataset]
        rows = [row for row in rows if _safe_float(row.get("f1_mean")) is not None]
        if not rows:
            continue
        best_f1 = max(float(row["f1_mean"]) for row in rows)
        tolerance = float(f1_tolerance)
        f1_candidates = [row for row in rows if float(row["f1_mean"]) >= best_f1 - tolerance]
        gate_enabled = max_ece_mean is not None
        gate_threshold = float(max_ece_mean) if gate_enabled else None

        gate_pass_all = rows
        if gate_enabled:
            gate_pass_all = [
                row
                for row in rows
                if _safe_float(row.get("ece_mean")) is not None and float(row["ece_mean"]) <= float(gate_threshold)
            ]
        gate_pass_f1_candidates = [row for row in f1_candidates if row in gate_pass_all]

        selection_pool = f1_candidates
        gate_status = "disabled"
        selection_rule = "max_f1_mean_within_tolerance_then_min_ece_then_min_f1_std"
        if gate_enabled:
            if gate_pass_f1_candidates:
                selection_pool = gate_pass_f1_candidates
                gate_status = "pass_within_f1_band"
                selection_rule = "ece_gate_then_max_f1_within_tolerance_then_min_ece_then_min_f1_std"
            elif gate_pass_all:
                selection_pool = gate_pass_all
                gate_status = "fallback_to_gate_pass_outside_f1_band"
                selection_rule = "ece_gate_hard_then_max_f1_then_min_ece_then_min_f1_std"
            else:
                selection_pool = f1_candidates
                gate_status = "no_gate_pass_candidate"
                selection_rule = "no_ece_gate_pass_candidate_fallback_to_f1_band"

        if gate_enabled and gate_status == "fallback_to_gate_pass_outside_f1_band":
            selection_pool.sort(
                key=lambda row: (
                    -float(row["f1_mean"]),
                    float(row["ece_mean"]) if _safe_float(row.get("ece_mean")) is not None else float("inf"),
                    float(row["f1_std"]) if _safe_float(row.get("f1_std")) is not None else float("inf"),
                    str(row.get("model_name", "")),
                )
            )
        else:
            selection_pool.sort(
                key=lambda row: (
                    float(row["ece_mean"]) if _safe_float(row.get("ece_mean")) is not None else float("inf"),
                    float(row["f1_std"]) if _safe_float(row.get("f1_std")) is not None else float("inf"),
                    -float(row["f1_mean"]),
                    str(row.get("model_name", "")),
                )
            )
        chosen = selection_pool[0]
        recommendations.append(
            {
                "dataset": dataset,
                "model_family": chosen.get("model_family", ""),
                "model_name": chosen.get("model_name", ""),
                "f1_mean": chosen.get("f1_mean"),
                "f1_std": chosen.get("f1_std"),
                "ece_mean": chosen.get("ece_mean"),
                "ece_std": chosen.get("ece_std"),
                "f1_tolerance": float(tolerance),
                "candidate_count": len(f1_candidates),
                "ece_gate_enabled": bool(gate_enabled),
                "ece_gate_max": gate_threshold,
                "ece_gate_pass_count": len(gate_pass_f1_candidates),
                "ece_gate_pass_total_count": len(gate_pass_all) if gate_enabled else len(rows),
                "gate_status": gate_status,
                "selection_rule": selection_rule,
            }
        )
    return recommendations


def _recommendation_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Seed Sweep Recommendation",
        "",
        "| Dataset | Recommended Model | Family | F1 mean±std | ECE mean±std | Candidate Count | Gate Status |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {dataset} | {model} | {family} | {f1m}±{f1s} | {ecem}±{eces} | {cand} | {gate} |".format(
                dataset=row.get("dataset", ""),
                model=row.get("model_name", ""),
                family=row.get("model_family", ""),
                f1m=_fmt(row.get("f1_mean")),
                f1s=_fmt(row.get("f1_std")),
                ecem=_fmt(row.get("ece_mean")),
                eces=_fmt(row.get("ece_std")),
                cand=row.get("candidate_count", 0),
                gate=row.get("gate_status", ""),
            )
        )
    return "\n".join(lines) + "\n"


def _build_markdown(
    summary: dict[str, Any],
    aggregate_rows: list[dict[str, Any]],
    winner_summary_rows: list[dict[str, Any]],
    recommendation_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# All Models Seed Sweep Summary",
        "",
        "## Inputs",
        "",
        f"- output_root: `{summary['output_root']}`",
        f"- regions: `{', '.join(summary['regions'])}`",
        f"- seeds: `{', '.join(str(item) for item in summary['seeds'])}`",
        f"- include_regional_cnn: `{summary['include_regional_cnn']}`",
        f"- split_strategy: `{summary['split_strategy']}`",
        f"- auto_adjust_split_for_support: `{summary['auto_adjust_split_for_support']}`",
        f"- min_positive_support: `{summary['min_positive_support']}`",
        f"- recommendation_f1_tolerance: `{summary['recommendation_f1_tolerance']}`",
        f"- recommendation_max_ece_mean: `{summary['recommendation_max_ece_mean']}`",
        "",
        "## Aggregated Model Metrics",
        "",
        "| Dataset | Model | Family | Runs | F1 mean±std (CI95) | AUROC mean±std (CI95) | ECE mean±std (CI95) | Positive mean |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in aggregate_rows:
        lines.append(
            "| {dataset} | {model} | {family} | {runs} | {f1m}±{f1s} ({f1ci}) | {aum}±{aus} ({auci}) | {ecem}±{eces} ({ecici}) | {pos} |".format(
                dataset=row.get("dataset", ""),
                model=row.get("model_name", ""),
                family=row.get("model_family", ""),
                runs=row.get("runs", 0),
                f1m=_fmt(row.get("f1_mean")),
                f1s=_fmt(row.get("f1_std")),
                f1ci=_fmt(row.get("f1_ci95")),
                aum=_fmt(row.get("auroc_mean")),
                aus=_fmt(row.get("auroc_std")),
                auci=_fmt(row.get("auroc_ci95")),
                ecem=_fmt(row.get("ece_mean")),
                eces=_fmt(row.get("ece_std")),
                ecici=_fmt(row.get("ece_ci95")),
                pos=_fmt(row.get("positive_count_mean"), digits=1),
            )
        )

    lines.extend(
        [
            "",
            "## Winner Frequency",
            "",
            "| Dataset | Model | Family | Wins | Total Seeds | Win Rate |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in winner_summary_rows:
        lines.append(
            "| {dataset} | {model} | {family} | {wins} | {total} | {rate} |".format(
                dataset=row.get("dataset", ""),
                model=row.get("model_name", ""),
                family=row.get("model_family", ""),
                wins=row.get("wins", 0),
                total=row.get("total_seeds", 0),
                rate=_fmt(row.get("win_rate")),
            )
        )

    lines.extend(
        [
            "",
            "## Recommended Model Per Dataset",
            "",
            "| Dataset | Recommended Model | Family | F1 mean±std | ECE mean±std | Candidate Count | Gate Status |",
            "|---|---|---|---:|---:|---:|---|",
        ]
    )
    for row in recommendation_rows:
        lines.append(
            "| {dataset} | {model} | {family} | {f1m}±{f1s} | {ecem}±{eces} | {cand} | {gate} |".format(
                dataset=row.get("dataset", ""),
                model=row.get("model_name", ""),
                family=row.get("model_family", ""),
                f1m=_fmt(row.get("f1_mean")),
                f1s=_fmt(row.get("f1_std")),
                ecem=_fmt(row.get("ece_mean")),
                eces=_fmt(row.get("ece_std")),
                cand=row.get("candidate_count", 0),
                gate=row.get("gate_status", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- run_manifest_json: `{summary['run_manifest_json_path']}`",
            f"- raw_rows_csv: `{summary['raw_rows_csv_path']}`",
            f"- aggregate_csv: `{summary['aggregate_csv_path']}`",
            f"- winner_rows_csv: `{summary['winner_rows_csv_path']}`",
            f"- winner_summary_csv: `{summary['winner_summary_csv_path']}`",
            f"- recommendation_csv: `{summary['recommendation_csv_path']}`",
            f"- recommendation_json: `{summary['recommendation_json_path']}`",
            f"- recommendation_md: `{summary['recommendation_md_path']}`",
            f"- summary_md: `{summary['summary_md_path']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_all_models_seed_sweep(
    input_paths_by_region: dict[str, str | Path],
    output_root: str | Path,
    seeds: list[int],
    split_strategy: str = "own_ship",
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    torch_device: str = "auto",
    include_regional_cnn: bool = True,
    cnn_losses: list[str] | None = None,
    min_positive_support: int = 10,
    auto_adjust_split_for_support: bool = True,
    recommendation_f1_tolerance: float = 0.01,
    recommendation_max_ece_mean: float | None = 0.10,
) -> dict[str, Any]:
    output_root_path = Path(output_root).resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)

    run_manifest_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []

    for region in sorted(input_paths_by_region.keys()):
        input_path = Path(input_paths_by_region[region]).resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Input CSV does not exist: {input_path}")
        for seed in seeds:
            run_dir = output_root_path / region / f"seed_{int(seed)}"
            summary = run_all_supported_models(
                input_path=input_path,
                output_dir=run_dir,
                split_strategy=split_strategy,
                train_fraction=float(train_fraction),
                val_fraction=float(val_fraction),
                torch_device=torch_device,
                random_seed=int(seed),
                include_regional_cnn=bool(include_regional_cnn),
                cnn_losses=cnn_losses,
                min_positive_support=int(min_positive_support),
                auto_adjust_split_for_support=bool(auto_adjust_split_for_support),
            )
            run_manifest_rows.append(
                {
                    "region": region,
                    "seed": int(seed),
                    "input_csv_path": str(input_path),
                    "summary_json_path": summary["summary_json_path"],
                    "leaderboard_csv_path": summary["leaderboard_csv_path"],
                    "split_was_auto_adjusted": bool(summary.get("split_was_auto_adjusted", False)),
                    "effective_train_fraction": summary.get("effective_train_fraction"),
                    "effective_val_fraction": summary.get("effective_val_fraction"),
                }
            )

            leaderboard_rows = _parse_csv_rows(summary["leaderboard_csv_path"])
            for row in leaderboard_rows:
                payload = dict(row)
                payload["region"] = region
                payload["seed"] = int(seed)
                for key in (
                    "f1",
                    "precision",
                    "recall",
                    "auroc",
                    "auprc",
                    "accuracy",
                    "threshold",
                    "sample_count",
                    "positive_count",
                    "negative_count",
                    "tp",
                    "fp",
                    "tn",
                    "fn",
                    "ece",
                    "brier_score",
                    "elapsed_seconds",
                ):
                    payload[key] = _safe_float(payload.get(key))
                raw_rows.append(payload)

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in raw_rows:
        if str(row.get("status", "")) != "completed":
            continue
        key = (str(row.get("dataset", "")), str(row.get("model_family", "")), str(row.get("model_name", "")))
        grouped[key].append(row)

    aggregate_rows: list[dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        dataset, family, model = key
        f1_values = [float(item["f1"]) for item in rows if item.get("f1") is not None]
        precision_values = [float(item["precision"]) for item in rows if item.get("precision") is not None]
        recall_values = [float(item["recall"]) for item in rows if item.get("recall") is not None]
        auroc_values = [float(item["auroc"]) for item in rows if item.get("auroc") is not None]
        ece_values = [float(item["ece"]) for item in rows if item.get("ece") is not None]
        brier_values = [float(item["brier_score"]) for item in rows if item.get("brier_score") is not None]
        positive_values = [float(item["positive_count"]) for item in rows if item.get("positive_count") is not None]
        aggregate_rows.append(
            {
                "dataset": dataset,
                "model_family": family,
                "model_name": model,
                "runs": len(rows),
                "f1_mean": mean(f1_values) if f1_values else None,
                "f1_std": _std(f1_values) if f1_values else None,
                "f1_ci95": _ci95(f1_values) if f1_values else None,
                "precision_mean": mean(precision_values) if precision_values else None,
                "precision_std": _std(precision_values) if precision_values else None,
                "recall_mean": mean(recall_values) if recall_values else None,
                "recall_std": _std(recall_values) if recall_values else None,
                "auroc_mean": mean(auroc_values) if auroc_values else None,
                "auroc_std": _std(auroc_values) if auroc_values else None,
                "auroc_ci95": _ci95(auroc_values) if auroc_values else None,
                "ece_mean": mean(ece_values) if ece_values else None,
                "ece_std": _std(ece_values) if ece_values else None,
                "ece_ci95": _ci95(ece_values) if ece_values else None,
                "brier_mean": mean(brier_values) if brier_values else None,
                "brier_std": _std(brier_values) if brier_values else None,
                "brier_ci95": _ci95(brier_values) if brier_values else None,
                "positive_count_mean": mean(positive_values) if positive_values else None,
            }
        )
    aggregate_rows.sort(
        key=lambda row: (
            str(row.get("dataset", "")),
            -float(row.get("f1_mean", -1.0) if row.get("f1_mean") is not None else -1.0),
            str(row.get("model_name", "")),
        )
    )

    winner_rows = _winner_rows(raw_rows)
    winner_summary_rows = _winner_summary_rows(winner_rows)
    recommendation_rows = _recommendation_rows(
        aggregate_rows,
        f1_tolerance=float(recommendation_f1_tolerance),
        max_ece_mean=recommendation_max_ece_mean,
    )

    run_manifest_json_path = output_root_path / "all_models_seed_sweep_run_manifest.json"
    raw_rows_csv_path = output_root_path / "all_models_seed_sweep_raw_rows.csv"
    aggregate_csv_path = output_root_path / "all_models_seed_sweep_aggregate.csv"
    winner_rows_csv_path = output_root_path / "all_models_seed_sweep_winner_rows.csv"
    winner_summary_csv_path = output_root_path / "all_models_seed_sweep_winner_summary.csv"
    recommendation_csv_path = output_root_path / "all_models_seed_sweep_recommendation.csv"
    recommendation_json_path = output_root_path / "all_models_seed_sweep_recommendation.json"
    recommendation_md_path = output_root_path / "all_models_seed_sweep_recommendation.md"
    summary_md_path = output_root_path / "all_models_seed_sweep_summary.md"
    summary_json_path = output_root_path / "all_models_seed_sweep_summary.json"

    raw_fieldnames = sorted({key for row in raw_rows for key in row.keys()})
    run_manifest_fieldnames = sorted({key for row in run_manifest_rows for key in row.keys()})
    winner_fieldnames = sorted({key for row in winner_rows for key in row.keys()}) if winner_rows else ["dataset", "seed", "model_family", "model_name", "f1", "auroc", "ece"]
    winner_summary_fieldnames = sorted({key for row in winner_summary_rows for key in row.keys()}) if winner_summary_rows else ["dataset", "model_family", "model_name", "wins", "total_seeds", "win_rate"]
    recommendation_fieldnames = sorted({key for row in recommendation_rows for key in row.keys()}) if recommendation_rows else [
        "dataset",
        "model_family",
        "model_name",
        "f1_mean",
        "f1_std",
        "ece_mean",
        "ece_std",
        "f1_tolerance",
        "candidate_count",
        "ece_gate_enabled",
        "ece_gate_max",
        "ece_gate_pass_count",
        "ece_gate_pass_total_count",
        "gate_status",
        "selection_rule",
    ]

    if run_manifest_rows:
        _write_csv(output_root_path / "all_models_seed_sweep_run_manifest.csv", run_manifest_rows, run_manifest_fieldnames)
    if raw_rows:
        _write_csv(raw_rows_csv_path, raw_rows, raw_fieldnames)
    _write_csv(aggregate_csv_path, aggregate_rows, AGG_FIELDS)
    _write_csv(winner_rows_csv_path, winner_rows, winner_fieldnames)
    _write_csv(winner_summary_csv_path, winner_summary_rows, winner_summary_fieldnames)
    _write_csv(recommendation_csv_path, recommendation_rows, recommendation_fieldnames)
    recommendation_json_path.write_text(json.dumps(recommendation_rows, indent=2), encoding="utf-8")
    recommendation_md_path.write_text(_recommendation_markdown(recommendation_rows), encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "completed",
        "output_root": str(output_root_path),
        "regions": sorted(input_paths_by_region.keys()),
        "seeds": [int(item) for item in seeds],
        "include_regional_cnn": bool(include_regional_cnn),
        "split_strategy": split_strategy,
        "auto_adjust_split_for_support": bool(auto_adjust_split_for_support),
        "min_positive_support": int(min_positive_support),
        "recommendation_f1_tolerance": float(recommendation_f1_tolerance),
        "recommendation_max_ece_mean": recommendation_max_ece_mean,
        "run_count": len(run_manifest_rows),
        "raw_row_count": len(raw_rows),
        "aggregate_row_count": len(aggregate_rows),
        "winner_row_count": len(winner_rows),
        "winner_summary_row_count": len(winner_summary_rows),
        "recommendation_row_count": len(recommendation_rows),
        "run_manifest_json_path": str(run_manifest_json_path),
        "raw_rows_csv_path": str(raw_rows_csv_path),
        "aggregate_csv_path": str(aggregate_csv_path),
        "winner_rows_csv_path": str(winner_rows_csv_path),
        "winner_summary_csv_path": str(winner_summary_csv_path),
        "recommendation_csv_path": str(recommendation_csv_path),
        "recommendation_json_path": str(recommendation_json_path),
        "recommendation_md_path": str(recommendation_md_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
    }

    run_manifest_json_path.write_text(json.dumps(run_manifest_rows, indent=2), encoding="utf-8")
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(_build_markdown(summary, aggregate_rows, winner_summary_rows, recommendation_rows), encoding="utf-8")
    return summary
