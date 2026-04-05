from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from sklearn.metrics import f1_score


DETAIL_FIELDS = [
    "region",
    "dataset",
    "model_name",
    "policy",
    "status",
    "notes",
    "baseline_threshold",
    "policy_threshold",
    "baseline_f1",
    "out_of_time_f1",
    "delta_f1",
    "baseline_ece",
    "out_of_time_ece",
    "best_in_time_f1",
    "in_time_regression_from_best_f1",
    "ece_gate_pass",
    "temporal_gate_pass",
    "in_time_regression_pass",
    "combined_pass",
    "out_of_time_leaderboard_csv_path",
    "out_of_time_predictions_csv_path",
]


POLICY_SUMMARY_FIELDS = [
    "policy",
    "dataset_count",
    "completed_count",
    "combined_pass_count",
    "temporal_pass_count",
    "ece_pass_count",
    "in_time_regression_pass_count",
    "mean_delta_f1",
    "min_delta_f1",
    "max_out_of_time_ece",
    "max_in_time_regression_from_best_f1",
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


def _build_threshold_grid(step: float = 0.01, minimum: float = 0.0, maximum: float = 1.0) -> list[float]:
    if float(step) <= 0.0:
        raise ValueError("threshold_grid_step must be > 0.")
    lower = max(0.0, float(minimum))
    upper = min(1.0, float(maximum))
    points: list[float] = []
    current = lower
    while current <= upper + (float(step) * 0.5):
        points.append(round(float(current), 6))
        current += float(step)
    return sorted({value for value in points if 0.0 <= value <= 1.0})


def _load_scores_and_labels(predictions_csv_path: str | Path, model_name: str) -> tuple[list[int], list[float]]:
    score_key = f"{model_name}_score"
    labels: list[int] = []
    scores: list[float] = []
    for row in _parse_csv_rows(predictions_csv_path):
        label = _safe_float(row.get("label_future_conflict"))
        score = _safe_float(row.get(score_key))
        if label not in (0.0, 1.0) or score is None:
            continue
        labels.append(int(label))
        scores.append(min(1.0, max(0.0, float(score))))
    return labels, scores


def _f1_at_threshold(labels: list[int], scores: list[float], threshold: float) -> float:
    y_true = np.asarray(labels, dtype=int)
    y_score = np.asarray(scores, dtype=float)
    y_pred = (y_score >= float(threshold)).astype(int)
    return float(f1_score(y_true, y_pred, zero_division=0))


def _best_threshold(labels: list[int], scores: list[float], threshold_grid: list[float]) -> tuple[float, float]:
    best_threshold = float(threshold_grid[0])
    best_f1 = -1.0
    for threshold in threshold_grid:
        score = _f1_at_threshold(labels=labels, scores=scores, threshold=float(threshold))
        if score > best_f1:
            best_f1 = score
            best_threshold = float(threshold)
    return best_threshold, float(best_f1)


def _region_from_dataset(dataset: str) -> str:
    return str(dataset).replace("_pooled_pairwise", "")


def _dataset_passes_prefix_filter(dataset: str, prefixes: list[str]) -> bool:
    if not prefixes:
        return True
    value = str(dataset).strip().lower()
    return any(value.startswith(f"{prefix}_") for prefix in prefixes)


def run_out_of_time_threshold_policy_compare(
    recommendation_csv_path: str | Path,
    baseline_leaderboard_csv_path: str | Path,
    out_of_time_output_root: str | Path,
    output_prefix: str | Path,
    dataset_prefix_filters: list[str] | None = None,
    threshold_grid_step: float = 0.01,
    max_out_of_time_ece: float = 0.10,
    min_out_of_time_delta_f1: float = -0.05,
    max_in_time_regression_from_best_f1: float = 0.02,
    include_oracle_policy: bool = True,
) -> dict[str, Any]:
    threshold_grid = _build_threshold_grid(step=float(threshold_grid_step))
    prefixes = [str(item).strip().lower() for item in (dataset_prefix_filters or []) if str(item).strip()]

    recommendation_rows = _parse_csv_rows(recommendation_csv_path)
    baseline_rows = _parse_csv_rows(baseline_leaderboard_csv_path)
    out_of_time_root = Path(out_of_time_output_root).resolve()

    baseline_by_key: dict[tuple[str, str], dict[str, str]] = {}
    best_in_time_f1_by_dataset: dict[str, float] = {}
    for row in baseline_rows:
        dataset = str(row.get("dataset", "")).strip()
        model_name = str(row.get("model_name", "")).strip()
        if not dataset or not model_name:
            continue
        baseline_by_key[(dataset, model_name)] = row
        f1_value = _safe_float(row.get("f1"))
        if f1_value is None:
            f1_value = _safe_float(row.get("f1_mean"))
        if f1_value is not None:
            best_in_time_f1_by_dataset[dataset] = max(float(f1_value), best_in_time_f1_by_dataset.get(dataset, -1.0))

    detail_rows: list[dict[str, Any]] = []
    for rec_row in recommendation_rows:
        dataset = str(rec_row.get("dataset", "")).strip()
        model_name = str(rec_row.get("model_name", "")).strip()
        if not dataset or not model_name:
            continue
        if not _dataset_passes_prefix_filter(dataset=dataset, prefixes=prefixes):
            continue

        region = _region_from_dataset(dataset)
        baseline_row = baseline_by_key.get((dataset, model_name))
        if baseline_row is None:
            detail_rows.append(
                {
                    "region": region,
                    "dataset": dataset,
                    "model_name": model_name,
                    "policy": "oot_val_tuned",
                    "status": "missing_baseline_row",
                    "notes": "baseline leaderboard row for recommendation is missing",
                    "baseline_threshold": None,
                    "policy_threshold": None,
                    "baseline_f1": None,
                    "out_of_time_f1": None,
                    "delta_f1": None,
                    "baseline_ece": None,
                    "out_of_time_ece": None,
                    "best_in_time_f1": None,
                    "in_time_regression_from_best_f1": None,
                    "ece_gate_pass": False,
                    "temporal_gate_pass": False,
                    "in_time_regression_pass": False,
                    "combined_pass": False,
                    "out_of_time_leaderboard_csv_path": "",
                    "out_of_time_predictions_csv_path": "",
                }
            )
            continue

        baseline_threshold = _safe_float(baseline_row.get("threshold"))
        baseline_f1 = _safe_float(baseline_row.get("f1"))
        if baseline_f1 is None:
            baseline_f1 = _safe_float(baseline_row.get("f1_mean"))
        baseline_ece = _safe_float(baseline_row.get("ece"))
        if baseline_ece is None:
            baseline_ece = _safe_float(baseline_row.get("ece_mean"))
        best_in_time_f1 = _safe_float(best_in_time_f1_by_dataset.get(dataset))
        in_time_regression = (
            float(best_in_time_f1) - float(baseline_f1)
            if best_in_time_f1 is not None and baseline_f1 is not None
            else None
        )

        oot_leaderboard_path = out_of_time_root / region / "timestamp_split" / f"{dataset}_all_models_leaderboard.csv"
        oot_predictions_path = out_of_time_root / region / "timestamp_split" / f"{dataset}_tabular_all_models_test_predictions.csv"
        if not oot_leaderboard_path.exists() or not oot_predictions_path.exists():
            for policy in ["oot_val_tuned", "fixed_baseline_threshold", "oot_oracle_threshold"]:
                if policy == "oot_oracle_threshold" and not include_oracle_policy:
                    continue
                detail_rows.append(
                    {
                        "region": region,
                        "dataset": dataset,
                        "model_name": model_name,
                        "policy": policy,
                        "status": "missing_out_of_time_artifact",
                        "notes": "required out-of-time leaderboard or prediction file is missing",
                        "baseline_threshold": baseline_threshold,
                        "policy_threshold": None,
                        "baseline_f1": baseline_f1,
                        "out_of_time_f1": None,
                        "delta_f1": None,
                        "baseline_ece": baseline_ece,
                        "out_of_time_ece": None,
                        "best_in_time_f1": best_in_time_f1,
                        "in_time_regression_from_best_f1": in_time_regression,
                        "ece_gate_pass": False,
                        "temporal_gate_pass": False,
                        "in_time_regression_pass": bool(
                            in_time_regression is not None
                            and float(in_time_regression) <= float(max_in_time_regression_from_best_f1)
                        ),
                        "combined_pass": False,
                        "out_of_time_leaderboard_csv_path": str(oot_leaderboard_path),
                        "out_of_time_predictions_csv_path": str(oot_predictions_path),
                    }
                )
            continue

        oot_rows = _parse_csv_rows(oot_leaderboard_path)
        oot_model_rows = [row for row in oot_rows if str(row.get("model_name", "")).strip() == model_name]
        if not oot_model_rows:
            for policy in ["oot_val_tuned", "fixed_baseline_threshold", "oot_oracle_threshold"]:
                if policy == "oot_oracle_threshold" and not include_oracle_policy:
                    continue
                detail_rows.append(
                    {
                        "region": region,
                        "dataset": dataset,
                        "model_name": model_name,
                        "policy": policy,
                        "status": "model_not_found_in_out_of_time_leaderboard",
                        "notes": "recommended model is missing from out-of-time leaderboard",
                        "baseline_threshold": baseline_threshold,
                        "policy_threshold": None,
                        "baseline_f1": baseline_f1,
                        "out_of_time_f1": None,
                        "delta_f1": None,
                        "baseline_ece": baseline_ece,
                        "out_of_time_ece": None,
                        "best_in_time_f1": best_in_time_f1,
                        "in_time_regression_from_best_f1": in_time_regression,
                        "ece_gate_pass": False,
                        "temporal_gate_pass": False,
                        "in_time_regression_pass": bool(
                            in_time_regression is not None
                            and float(in_time_regression) <= float(max_in_time_regression_from_best_f1)
                        ),
                        "combined_pass": False,
                        "out_of_time_leaderboard_csv_path": str(oot_leaderboard_path),
                        "out_of_time_predictions_csv_path": str(oot_predictions_path),
                    }
                )
            continue

        oot_model_row = oot_model_rows[0]
        oot_val_threshold = _safe_float(oot_model_row.get("threshold"))
        oot_ece = _safe_float(oot_model_row.get("ece"))
        labels, scores = _load_scores_and_labels(predictions_csv_path=oot_predictions_path, model_name=model_name)
        if not labels:
            for policy in ["oot_val_tuned", "fixed_baseline_threshold", "oot_oracle_threshold"]:
                if policy == "oot_oracle_threshold" and not include_oracle_policy:
                    continue
                detail_rows.append(
                    {
                        "region": region,
                        "dataset": dataset,
                        "model_name": model_name,
                        "policy": policy,
                        "status": "missing_prediction_rows",
                        "notes": "out-of-time prediction rows for the model are empty",
                        "baseline_threshold": baseline_threshold,
                        "policy_threshold": None,
                        "baseline_f1": baseline_f1,
                        "out_of_time_f1": None,
                        "delta_f1": None,
                        "baseline_ece": baseline_ece,
                        "out_of_time_ece": oot_ece,
                        "best_in_time_f1": best_in_time_f1,
                        "in_time_regression_from_best_f1": in_time_regression,
                        "ece_gate_pass": False,
                        "temporal_gate_pass": False,
                        "in_time_regression_pass": bool(
                            in_time_regression is not None
                            and float(in_time_regression) <= float(max_in_time_regression_from_best_f1)
                        ),
                        "combined_pass": False,
                        "out_of_time_leaderboard_csv_path": str(oot_leaderboard_path),
                        "out_of_time_predictions_csv_path": str(oot_predictions_path),
                    }
                )
            continue

        policy_specs: list[tuple[str, float | None, str]] = [
            ("oot_val_tuned", oot_val_threshold, ""),
            ("fixed_baseline_threshold", baseline_threshold, ""),
        ]
        if include_oracle_policy:
            oracle_threshold, _ = _best_threshold(labels=labels, scores=scores, threshold_grid=threshold_grid)
            policy_specs.append(("oot_oracle_threshold", oracle_threshold, "oracle upper-bound on out-of-time test labels"))

        for policy_name, threshold_value, notes in policy_specs:
            if threshold_value is None:
                detail_rows.append(
                    {
                        "region": region,
                        "dataset": dataset,
                        "model_name": model_name,
                        "policy": policy_name,
                        "status": "missing_threshold",
                        "notes": "policy threshold is missing",
                        "baseline_threshold": baseline_threshold,
                        "policy_threshold": threshold_value,
                        "baseline_f1": baseline_f1,
                        "out_of_time_f1": None,
                        "delta_f1": None,
                        "baseline_ece": baseline_ece,
                        "out_of_time_ece": oot_ece,
                        "best_in_time_f1": best_in_time_f1,
                        "in_time_regression_from_best_f1": in_time_regression,
                        "ece_gate_pass": False,
                        "temporal_gate_pass": False,
                        "in_time_regression_pass": bool(
                            in_time_regression is not None
                            and float(in_time_regression) <= float(max_in_time_regression_from_best_f1)
                        ),
                        "combined_pass": False,
                        "out_of_time_leaderboard_csv_path": str(oot_leaderboard_path),
                        "out_of_time_predictions_csv_path": str(oot_predictions_path),
                    }
                )
                continue

            out_of_time_f1 = _f1_at_threshold(labels=labels, scores=scores, threshold=float(threshold_value))
            delta_f1 = (float(out_of_time_f1) - float(baseline_f1)) if baseline_f1 is not None else None
            ece_gate_pass = bool(oot_ece is not None and float(oot_ece) <= float(max_out_of_time_ece))
            temporal_gate_pass = bool(delta_f1 is not None and float(delta_f1) >= float(min_out_of_time_delta_f1))
            in_time_regression_pass = bool(
                in_time_regression is not None and float(in_time_regression) <= float(max_in_time_regression_from_best_f1)
            )
            detail_rows.append(
                {
                    "region": region,
                    "dataset": dataset,
                    "model_name": model_name,
                    "policy": policy_name,
                    "status": "completed",
                    "notes": notes,
                    "baseline_threshold": baseline_threshold,
                    "policy_threshold": float(threshold_value),
                    "baseline_f1": baseline_f1,
                    "out_of_time_f1": float(out_of_time_f1),
                    "delta_f1": float(delta_f1) if delta_f1 is not None else None,
                    "baseline_ece": baseline_ece,
                    "out_of_time_ece": oot_ece,
                    "best_in_time_f1": best_in_time_f1,
                    "in_time_regression_from_best_f1": in_time_regression,
                    "ece_gate_pass": ece_gate_pass,
                    "temporal_gate_pass": temporal_gate_pass,
                    "in_time_regression_pass": in_time_regression_pass,
                    "combined_pass": bool(ece_gate_pass and temporal_gate_pass and in_time_regression_pass),
                    "out_of_time_leaderboard_csv_path": str(oot_leaderboard_path),
                    "out_of_time_predictions_csv_path": str(oot_predictions_path),
                }
            )

    summary_rows: list[dict[str, Any]] = []
    by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in detail_rows:
        by_policy[str(row.get("policy", ""))].append(row)

    for policy in sorted(by_policy.keys()):
        rows = by_policy[policy]
        completed = [row for row in rows if str(row.get("status", "")) == "completed"]
        deltas = [float(row["delta_f1"]) for row in completed if row.get("delta_f1") is not None]
        ece_values = [float(row["out_of_time_ece"]) for row in completed if row.get("out_of_time_ece") is not None]
        regressions = [
            float(row["in_time_regression_from_best_f1"])
            for row in completed
            if row.get("in_time_regression_from_best_f1") is not None
        ]
        summary_rows.append(
            {
                "policy": policy,
                "dataset_count": len(rows),
                "completed_count": len(completed),
                "combined_pass_count": sum(1 for row in completed if bool(row.get("combined_pass"))),
                "temporal_pass_count": sum(1 for row in completed if bool(row.get("temporal_gate_pass"))),
                "ece_pass_count": sum(1 for row in completed if bool(row.get("ece_gate_pass"))),
                "in_time_regression_pass_count": sum(
                    1 for row in completed if bool(row.get("in_time_regression_pass"))
                ),
                "mean_delta_f1": float(mean(deltas)) if deltas else None,
                "min_delta_f1": min(deltas) if deltas else None,
                "max_out_of_time_ece": max(ece_values) if ece_values else None,
                "max_in_time_regression_from_best_f1": max(regressions) if regressions else None,
            }
        )

    recommendation_pool = [row for row in summary_rows if str(row.get("policy", "")) != "oot_oracle_threshold"] or summary_rows
    recommendation_pool = sorted(
        recommendation_pool,
        key=lambda row: (
            -int(_safe_float(row.get("combined_pass_count")) or 0),
            -float(_safe_float(row.get("mean_delta_f1")) or -999.0),
            float(_safe_float(row.get("max_out_of_time_ece")) or 999.0),
            str(row.get("policy", "")),
        ),
    )
    recommended_policy = str(recommendation_pool[0]["policy"]) if recommendation_pool else ""

    output_root = Path(output_prefix).resolve()
    detail_csv_path = output_root.with_name(f"{output_root.name}_detail.csv")
    policy_summary_csv_path = output_root.with_name(f"{output_root.name}_policy_summary.csv")
    summary_md_path = output_root.with_suffix(".md")
    summary_json_path = output_root.with_suffix(".json")
    _write_csv(detail_csv_path, detail_rows, DETAIL_FIELDS)
    _write_csv(policy_summary_csv_path, summary_rows, POLICY_SUMMARY_FIELDS)

    houston_rows = [row for row in detail_rows if str(row.get("region", "")) == "houston" and row.get("status") == "completed"]

    lines = [
        "# Out-of-Time Threshold Policy Compare",
        "",
        "## Inputs",
        "",
        f"- recommendation_csv: `{Path(recommendation_csv_path).resolve()}`",
        f"- baseline_leaderboard_csv: `{Path(baseline_leaderboard_csv_path).resolve()}`",
        f"- out_of_time_output_root: `{out_of_time_root}`",
        (
            f"- dataset_prefix_filters: `{', '.join(prefixes)}`"
            if prefixes
            else "- dataset_prefix_filters: `(none)`"
        ),
        f"- threshold_grid_step: `{_fmt(threshold_grid_step)}`",
        f"- max_out_of_time_ece: `{_fmt(max_out_of_time_ece)}`",
        f"- min_out_of_time_delta_f1: `{_fmt(min_out_of_time_delta_f1)}`",
        f"- max_in_time_regression_from_best_f1: `{_fmt(max_in_time_regression_from_best_f1)}`",
        f"- include_oracle_policy: `{bool(include_oracle_policy)}`",
        "",
        "## Policy Summary",
        "",
        "| Policy | Datasets | Completed | Combined Pass | Temporal Pass | ECE Pass | In-Time Regr Pass | Mean ΔF1 | Min ΔF1 | Max OOT ECE | Max In-Time Regr |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {policy} | {datasets} | {completed} | {combined} | {temporal} | {ece} | {regr} | {mean_delta} | {min_delta} | {max_ece} | {max_regr} |".format(
                policy=row.get("policy", ""),
                datasets=row.get("dataset_count", 0),
                completed=row.get("completed_count", 0),
                combined=row.get("combined_pass_count", 0),
                temporal=row.get("temporal_pass_count", 0),
                ece=row.get("ece_pass_count", 0),
                regr=row.get("in_time_regression_pass_count", 0),
                mean_delta=_fmt(row.get("mean_delta_f1")),
                min_delta=_fmt(row.get("min_delta_f1")),
                max_ece=_fmt(row.get("max_out_of_time_ece")),
                max_regr=_fmt(row.get("max_in_time_regression_from_best_f1")),
            )
        )

    lines.extend(
        [
            "",
            "## Houston Detail",
            "",
            "| Policy | Baseline th | Policy th | Baseline F1 | OOT F1 | ΔF1 | OOT ECE | Combined Pass |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in sorted(houston_rows, key=lambda item: str(item.get("policy", ""))):
        lines.append(
            "| {policy} | {tb} | {tp} | {bf1} | {of1} | {df1} | {ece} | {combined} |".format(
                policy=row.get("policy", ""),
                tb=_fmt(row.get("baseline_threshold")),
                tp=_fmt(row.get("policy_threshold")),
                bf1=_fmt(row.get("baseline_f1")),
                of1=_fmt(row.get("out_of_time_f1")),
                df1=_fmt(row.get("delta_f1")),
                ece=_fmt(row.get("out_of_time_ece")),
                combined="yes" if bool(row.get("combined_pass")) else "no",
            )
        )

    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- detail_csv: `{detail_csv_path}`",
            f"- policy_summary_csv: `{policy_summary_csv_path}`",
            f"- summary_md: `{summary_md_path}`",
            f"- summary_json: `{summary_json_path}`",
            "",
        ]
    )
    summary_md_path.write_text("\n".join(lines), encoding="utf-8")

    summary_payload: dict[str, Any] = {
        "status": "completed",
        "recommendation_csv_path": str(Path(recommendation_csv_path).resolve()),
        "baseline_leaderboard_csv_path": str(Path(baseline_leaderboard_csv_path).resolve()),
        "out_of_time_output_root": str(out_of_time_root),
        "dataset_prefix_filters": prefixes,
        "threshold_grid_step": float(threshold_grid_step),
        "max_out_of_time_ece": float(max_out_of_time_ece),
        "min_out_of_time_delta_f1": float(min_out_of_time_delta_f1),
        "max_in_time_regression_from_best_f1": float(max_in_time_regression_from_best_f1),
        "include_oracle_policy": bool(include_oracle_policy),
        "detail_csv_path": str(detail_csv_path),
        "policy_summary_csv_path": str(policy_summary_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
        "detail_row_count": len(detail_rows),
        "policy_row_count": len(summary_rows),
        "recommended_policy_excluding_oracle": recommended_policy,
        "policies": summary_rows,
        "houston_rows": houston_rows,
    }
    summary_json_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    return summary_payload


__all__ = ["run_out_of_time_threshold_policy_compare"]
