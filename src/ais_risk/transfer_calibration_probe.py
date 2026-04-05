from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score


DETAIL_FIELDS = [
    "source_region",
    "target_region",
    "model_name",
    "method",
    "status",
    "notes",
    "threshold",
    "source_rows",
    "source_positives",
    "target_rows",
    "target_positives",
    "source_f1_fixed",
    "target_f1_fixed",
    "delta_f1_fixed",
    "target_best_threshold",
    "target_best_f1",
    "target_retune_gain_f1",
    "delta_f1_retuned",
    "target_ece",
    "target_brier",
    "ece_gate_pass",
    "transfer_summary_json_path",
]

SUMMARY_FIELDS = [
    "source_region",
    "model_name",
    "method",
    "pair_count",
    "completed_pair_count",
    "negative_fixed_count",
    "negative_retuned_count",
    "mean_delta_f1_fixed",
    "mean_delta_f1_retuned",
    "mean_target_ece",
    "max_target_ece",
    "all_targets_ece_leq_max",
    "meets_negative_fixed_budget",
    "meets_negative_retuned_budget",
    "combined_pass_fixed",
    "combined_pass_retuned",
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


def _build_threshold_grid(step: float = 0.01, minimum: float = 0.01, maximum: float = 0.99) -> list[float]:
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


def _choose_threshold(labels: list[int], scores: list[float], threshold_grid: list[float]) -> float:
    if not labels or not scores or len(labels) != len(scores):
        raise ValueError("labels/scores must be non-empty and aligned.")
    best_threshold = float(threshold_grid[0])
    best_f1 = -1.0
    y_true = np.asarray(labels, dtype=int)
    y_score = np.asarray(scores, dtype=float)
    for threshold in threshold_grid:
        y_pred = (y_score >= float(threshold)).astype(int)
        current_f1 = float(f1_score(y_true, y_pred, zero_division=0))
        if current_f1 > best_f1:
            best_f1 = current_f1
            best_threshold = float(threshold)
    return float(best_threshold)


def _f1_at_threshold(labels: list[int], scores: list[float], threshold: float) -> float:
    y_true = np.asarray(labels, dtype=int)
    y_score = np.asarray(scores, dtype=float)
    y_pred = (y_score >= float(threshold)).astype(int)
    return float(f1_score(y_true, y_pred, zero_division=0))


def _best_target_threshold(labels: list[int], scores: list[float], threshold_grid: list[float]) -> tuple[float, float]:
    best_threshold = float(threshold_grid[0])
    best_f1 = -1.0
    for threshold in threshold_grid:
        current = _f1_at_threshold(labels=labels, scores=scores, threshold=float(threshold))
        if current > best_f1:
            best_f1 = current
            best_threshold = float(threshold)
    return best_threshold, float(best_f1)


def _ece(labels: list[int], scores: list[float], num_bins: int = 10) -> float:
    if not labels:
        return 0.0
    bins = [{"count": 0, "score_sum": 0.0, "label_sum": 0.0} for _ in range(int(num_bins))]
    for label, score in zip(labels, scores):
        bounded = min(1.0, max(0.0, float(score)))
        if bounded <= 0.0:
            index = 0
        elif bounded >= 1.0:
            index = int(num_bins) - 1
        else:
            index = min(int(num_bins) - 1, int(bounded * int(num_bins)))
        bucket = bins[index]
        bucket["count"] += 1
        bucket["score_sum"] += bounded
        bucket["label_sum"] += int(label)
    weighted_gap = 0.0
    sample_count = len(labels)
    for bucket in bins:
        count = int(bucket["count"])
        if count <= 0:
            continue
        avg_score = bucket["score_sum"] / count
        empirical = bucket["label_sum"] / count
        weighted_gap += (count / sample_count) * abs(empirical - avg_score)
    return float(weighted_gap)


def _brier(labels: list[int], scores: list[float]) -> float:
    if not labels:
        return 0.0
    total = 0.0
    for label, score in zip(labels, scores):
        diff = float(score) - float(label)
        total += diff * diff
    return float(total / len(labels))


def _transform_scores(
    method: str,
    val_labels: list[int],
    val_scores: list[float],
    source_test_scores: list[float],
    target_scores: list[float],
    random_seed: int,
) -> tuple[str, str, list[float], list[float], list[float]]:
    method_value = str(method).strip().lower()
    if method_value == "none":
        return (
            "completed",
            "",
            list(val_scores),
            list(source_test_scores),
            list(target_scores),
        )

    labels_unique = sorted(set(int(label) for label in val_labels))
    if labels_unique != [0, 1]:
        return "skipped", "validation labels must contain both classes for calibration fit", [], [], []

    x_val = np.asarray(val_scores, dtype=float).reshape(-1, 1)
    x_source = np.asarray(source_test_scores, dtype=float).reshape(-1, 1)
    x_target = np.asarray(target_scores, dtype=float).reshape(-1, 1)
    y_val = np.asarray(val_labels, dtype=int)

    if method_value == "platt":
        model = LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            random_state=int(random_seed),
        )
        model.fit(x_val, y_val)
        val_cal = model.predict_proba(x_val)[:, 1]
        source_cal = model.predict_proba(x_source)[:, 1]
        target_cal = model.predict_proba(x_target)[:, 1]
        return (
            "completed",
            "",
            [float(min(1.0, max(0.0, value))) for value in val_cal],
            [float(min(1.0, max(0.0, value))) for value in source_cal],
            [float(min(1.0, max(0.0, value))) for value in target_cal],
        )

    if method_value == "isotonic":
        unique_scores = len(set(round(float(score), 8) for score in val_scores))
        if unique_scores < 2:
            return "skipped", "validation scores require at least two unique values for isotonic fit", [], [], []
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(np.asarray(val_scores, dtype=float), y_val)
        val_cal = iso.transform(np.asarray(val_scores, dtype=float))
        source_cal = iso.transform(np.asarray(source_test_scores, dtype=float))
        target_cal = iso.transform(np.asarray(target_scores, dtype=float))
        return (
            "completed",
            "",
            [float(min(1.0, max(0.0, value))) for value in val_cal],
            [float(min(1.0, max(0.0, value))) for value in source_cal],
            [float(min(1.0, max(0.0, value))) for value in target_cal],
        )

    raise ValueError(f"Unsupported calibration method: {method}")


def _parse_methods(raw_methods: list[str] | None) -> list[str]:
    if not raw_methods:
        return ["none", "platt", "isotonic"]
    values = [str(method).strip().lower() for method in raw_methods if str(method).strip()]
    if not values:
        return ["none", "platt", "isotonic"]
    allowed = {"none", "platt", "isotonic"}
    invalid = sorted(set(values) - allowed)
    if invalid:
        raise ValueError(f"Unsupported calibration methods: {', '.join(invalid)}")
    deduped: list[str] = []
    for method in values:
        if method not in deduped:
            deduped.append(method)
    return deduped


def run_transfer_calibration_probe(
    transfer_scan_detail_csv_path: str | Path,
    output_prefix: str | Path,
    source_region_filter: str = "",
    model_names: list[str] | None = None,
    methods: list[str] | None = None,
    threshold_grid_step: float = 0.01,
    ece_gate_max: float = 0.10,
    max_negative_pairs_allowed: int = 1,
    random_seed: int = 42,
) -> dict[str, Any]:
    methods_resolved = _parse_methods(methods)
    model_name_filter = {token.strip() for token in (model_names or []) if token.strip()}
    source_filter_value = str(source_region_filter).strip().lower()
    threshold_grid = _build_threshold_grid(step=float(threshold_grid_step))

    input_rows = _parse_csv_rows(transfer_scan_detail_csv_path)
    candidate_rows = [
        row
        for row in input_rows
        if str(row.get("status", "")).strip() == "completed"
        and str(row.get("transfer_summary_json_path", "")).strip()
        and (not source_filter_value or str(row.get("source_region", "")).strip().lower() == source_filter_value)
        and (not model_name_filter or str(row.get("model_name", "")).strip() in model_name_filter)
    ]
    if not candidate_rows:
        raise ValueError("No completed transfer rows matched the given filters.")

    detail_rows: list[dict[str, Any]] = []
    for row in candidate_rows:
        source_region = str(row.get("source_region", "")).strip()
        target_region = str(row.get("target_region", "")).strip()
        model_name = str(row.get("model_name", "")).strip()
        transfer_summary_json_path = str(row.get("transfer_summary_json_path", "")).strip()
        transfer_summary = json.loads(Path(transfer_summary_json_path).read_text(encoding="utf-8"))

        source_val_predictions_path = transfer_summary.get("source_val_predictions_csv_path")
        source_test_predictions_path = transfer_summary.get("source_test_predictions_csv_path")
        target_predictions_path = transfer_summary.get("target_predictions_csv_path")
        if not source_val_predictions_path or not source_test_predictions_path or not target_predictions_path:
            for method in methods_resolved:
                detail_rows.append(
                    {
                        "source_region": source_region,
                        "target_region": target_region,
                        "model_name": model_name,
                        "method": method,
                        "status": "skipped",
                        "notes": "transfer summary is missing prediction csv paths",
                        "threshold": None,
                        "source_rows": 0,
                        "source_positives": 0,
                        "target_rows": 0,
                        "target_positives": 0,
                        "source_f1_fixed": None,
                        "target_f1_fixed": None,
                        "delta_f1_fixed": None,
                        "target_best_threshold": None,
                        "target_best_f1": None,
                        "target_retune_gain_f1": None,
                        "delta_f1_retuned": None,
                        "target_ece": None,
                        "target_brier": None,
                        "ece_gate_pass": False,
                        "transfer_summary_json_path": transfer_summary_json_path,
                    }
                )
            continue

        val_labels, val_scores = _load_scores_and_labels(source_val_predictions_path, model_name=model_name)
        source_labels, source_scores = _load_scores_and_labels(source_test_predictions_path, model_name=model_name)
        target_labels, target_scores = _load_scores_and_labels(target_predictions_path, model_name=model_name)
        if not val_labels or not source_labels or not target_labels:
            for method in methods_resolved:
                detail_rows.append(
                    {
                        "source_region": source_region,
                        "target_region": target_region,
                        "model_name": model_name,
                        "method": method,
                        "status": "skipped",
                        "notes": "missing score/label pairs in one or more prediction files",
                        "threshold": None,
                        "source_rows": len(source_labels),
                        "source_positives": int(sum(source_labels)),
                        "target_rows": len(target_labels),
                        "target_positives": int(sum(target_labels)),
                        "source_f1_fixed": None,
                        "target_f1_fixed": None,
                        "delta_f1_fixed": None,
                        "target_best_threshold": None,
                        "target_best_f1": None,
                        "target_retune_gain_f1": None,
                        "delta_f1_retuned": None,
                        "target_ece": None,
                        "target_brier": None,
                        "ece_gate_pass": False,
                        "transfer_summary_json_path": transfer_summary_json_path,
                    }
                )
            continue

        for method in methods_resolved:
            status, notes, val_cal, source_cal, target_cal = _transform_scores(
                method=method,
                val_labels=val_labels,
                val_scores=val_scores,
                source_test_scores=source_scores,
                target_scores=target_scores,
                random_seed=int(random_seed),
            )
            if status != "completed":
                detail_rows.append(
                    {
                        "source_region": source_region,
                        "target_region": target_region,
                        "model_name": model_name,
                        "method": method,
                        "status": status,
                        "notes": notes,
                        "threshold": None,
                        "source_rows": len(source_labels),
                        "source_positives": int(sum(source_labels)),
                        "target_rows": len(target_labels),
                        "target_positives": int(sum(target_labels)),
                        "source_f1_fixed": None,
                        "target_f1_fixed": None,
                        "delta_f1_fixed": None,
                        "target_best_threshold": None,
                        "target_best_f1": None,
                        "target_retune_gain_f1": None,
                        "delta_f1_retuned": None,
                        "target_ece": None,
                        "target_brier": None,
                        "ece_gate_pass": False,
                        "transfer_summary_json_path": transfer_summary_json_path,
                    }
                )
                continue

            threshold = _choose_threshold(labels=val_labels, scores=val_cal, threshold_grid=threshold_grid)
            source_f1 = _f1_at_threshold(labels=source_labels, scores=source_cal, threshold=threshold)
            target_f1 = _f1_at_threshold(labels=target_labels, scores=target_cal, threshold=threshold)
            target_best_threshold, target_best_f1 = _best_target_threshold(
                labels=target_labels,
                scores=target_cal,
                threshold_grid=threshold_grid,
            )
            delta_f1_fixed = float(target_f1 - source_f1)
            target_retune_gain = float(target_best_f1 - target_f1)
            delta_f1_retuned = float(target_best_f1 - source_f1)
            target_ece = _ece(labels=target_labels, scores=target_cal, num_bins=10)
            target_brier = _brier(labels=target_labels, scores=target_cal)
            detail_rows.append(
                {
                    "source_region": source_region,
                    "target_region": target_region,
                    "model_name": model_name,
                    "method": method,
                    "status": "completed",
                    "notes": "",
                    "threshold": float(threshold),
                    "source_rows": len(source_labels),
                    "source_positives": int(sum(source_labels)),
                    "target_rows": len(target_labels),
                    "target_positives": int(sum(target_labels)),
                    "source_f1_fixed": float(source_f1),
                    "target_f1_fixed": float(target_f1),
                    "delta_f1_fixed": float(delta_f1_fixed),
                    "target_best_threshold": float(target_best_threshold),
                    "target_best_f1": float(target_best_f1),
                    "target_retune_gain_f1": float(target_retune_gain),
                    "delta_f1_retuned": float(delta_f1_retuned),
                    "target_ece": float(target_ece),
                    "target_brier": float(target_brier),
                    "ece_gate_pass": bool(target_ece <= float(ece_gate_max)),
                    "transfer_summary_json_path": transfer_summary_json_path,
                }
            )

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in detail_rows:
        key = (
            str(row.get("source_region", "")),
            str(row.get("model_name", "")),
            str(row.get("method", "")),
        )
        grouped[key].append(row)

    summary_rows: list[dict[str, Any]] = []
    for key in sorted(grouped.keys()):
        source_region, model_name, method = key
        rows = grouped[key]
        completed = [row for row in rows if str(row.get("status", "")) == "completed"]
        delta_fixed_values = [float(row["delta_f1_fixed"]) for row in completed if row.get("delta_f1_fixed") is not None]
        delta_retuned_values = [float(row["delta_f1_retuned"]) for row in completed if row.get("delta_f1_retuned") is not None]
        target_ece_values = [float(row["target_ece"]) for row in completed if row.get("target_ece") is not None]
        negative_fixed_count = sum(1 for value in delta_fixed_values if value < 0.0)
        negative_retuned_count = sum(1 for value in delta_retuned_values if value < 0.0)
        all_targets_ece_leq_max = bool(target_ece_values) and all(value <= float(ece_gate_max) for value in target_ece_values)
        meets_negative_fixed_budget = bool(completed) and negative_fixed_count <= int(max_negative_pairs_allowed)
        meets_negative_retuned_budget = bool(completed) and negative_retuned_count <= int(max_negative_pairs_allowed)
        summary_rows.append(
            {
                "source_region": source_region,
                "model_name": model_name,
                "method": method,
                "pair_count": len(rows),
                "completed_pair_count": len(completed),
                "negative_fixed_count": int(negative_fixed_count),
                "negative_retuned_count": int(negative_retuned_count),
                "mean_delta_f1_fixed": float(mean(delta_fixed_values)) if delta_fixed_values else None,
                "mean_delta_f1_retuned": float(mean(delta_retuned_values)) if delta_retuned_values else None,
                "mean_target_ece": float(mean(target_ece_values)) if target_ece_values else None,
                "max_target_ece": max(target_ece_values) if target_ece_values else None,
                "all_targets_ece_leq_max": bool(all_targets_ece_leq_max),
                "meets_negative_fixed_budget": bool(meets_negative_fixed_budget),
                "meets_negative_retuned_budget": bool(meets_negative_retuned_budget),
                "combined_pass_fixed": bool(all_targets_ece_leq_max and meets_negative_fixed_budget),
                "combined_pass_retuned": bool(all_targets_ece_leq_max and meets_negative_retuned_budget),
            }
        )

    combined_pass_fixed = [row for row in summary_rows if bool(row.get("combined_pass_fixed"))]
    combined_pass_retuned = [row for row in summary_rows if bool(row.get("combined_pass_retuned"))]

    def _rank_key(row: dict[str, Any]) -> tuple[float, float, float, str, str]:
        return (
            -float(row.get("mean_delta_f1_fixed") or -999.0),
            float(row.get("max_target_ece") or 999.0),
            float(row.get("negative_fixed_count") or 999.0),
            str(row.get("model_name", "")),
            str(row.get("method", "")),
        )

    best_fixed = sorted(combined_pass_fixed, key=_rank_key)[:5]
    best_retuned = sorted(
        combined_pass_retuned,
        key=lambda row: (
            -float(row.get("mean_delta_f1_retuned") or -999.0),
            float(row.get("max_target_ece") or 999.0),
            float(row.get("negative_retuned_count") or 999.0),
            str(row.get("model_name", "")),
            str(row.get("method", "")),
        ),
    )[:5]

    output_prefix_path = Path(output_prefix).resolve()
    output_prefix_path.parent.mkdir(parents=True, exist_ok=True)
    detail_csv_path = output_prefix_path.with_name(f"{output_prefix_path.name}_detail").with_suffix(".csv")
    summary_csv_path = output_prefix_path.with_name(f"{output_prefix_path.name}_model_method_summary").with_suffix(".csv")
    summary_md_path = output_prefix_path.with_suffix(".md")
    summary_json_path = output_prefix_path.with_suffix(".json")

    _write_csv(detail_csv_path, detail_rows, DETAIL_FIELDS)
    _write_csv(summary_csv_path, summary_rows, SUMMARY_FIELDS)

    md_lines = [
        "# Transfer Calibration Probe",
        "",
        "## Inputs",
        "",
        f"- transfer_scan_detail_csv: `{Path(transfer_scan_detail_csv_path).resolve()}`",
        f"- source_region_filter: `{source_filter_value or 'all'}`",
        f"- model_filter: `{', '.join(sorted(model_name_filter)) if model_name_filter else 'all'}`",
        f"- methods: `{', '.join(methods_resolved)}`",
        f"- threshold_grid_step: `{_fmt(threshold_grid_step)}`",
        f"- ece_gate_max: `{_fmt(ece_gate_max)}`",
        f"- max_negative_pairs_allowed: `{int(max_negative_pairs_allowed)}`",
        "",
        "## Model x Method Summary",
        "",
        "| Model | Method | Completed | Neg(Fixed) | Neg(Retuned) | Mean ΔF1 Fixed | Mean ΔF1 Retuned | Max Target ECE | CombinedPass(Fixed/Retuned) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary_rows:
        md_lines.append(
            "| {model} | {method} | {completed}/{pairs} | {neg_fixed} | {neg_retuned} | {d_fixed} | {d_retuned} | {max_ece} | {pass_fixed}/{pass_retuned} |".format(
                model=row.get("model_name", ""),
                method=row.get("method", ""),
                completed=row.get("completed_pair_count", 0),
                pairs=row.get("pair_count", 0),
                neg_fixed=row.get("negative_fixed_count", 0),
                neg_retuned=row.get("negative_retuned_count", 0),
                d_fixed=_fmt(row.get("mean_delta_f1_fixed")),
                d_retuned=_fmt(row.get("mean_delta_f1_retuned")),
                max_ece=_fmt(row.get("max_target_ece")),
                pass_fixed="yes" if bool(row.get("combined_pass_fixed")) else "no",
                pass_retuned="yes" if bool(row.get("combined_pass_retuned")) else "no",
            )
        )
    md_lines.extend(
        [
            "",
            "## Top Combined-Pass Candidates",
            "",
            f"- fixed-threshold pass count: `{len(combined_pass_fixed)}`",
            f"- retuned-threshold pass count: `{len(combined_pass_retuned)}`",
            "",
            "### Fixed",
            "",
        ]
    )
    if best_fixed:
        for row in best_fixed:
            md_lines.append(
                (
                    "- `{model}/{method}`: mean ΔF1 fixed `{delta}`, max target ECE `{ece}`, "
                    "negative fixed `{neg}`"
                ).format(
                    model=row.get("model_name", ""),
                    method=row.get("method", ""),
                    delta=_fmt(row.get("mean_delta_f1_fixed")),
                    ece=_fmt(row.get("max_target_ece")),
                    neg=row.get("negative_fixed_count", 0),
                )
            )
    else:
        md_lines.append("- none")
    md_lines.extend(["", "### Retuned", ""])
    if best_retuned:
        for row in best_retuned:
            md_lines.append(
                (
                    "- `{model}/{method}`: mean ΔF1 retuned `{delta}`, max target ECE `{ece}`, "
                    "negative retuned `{neg}`"
                ).format(
                    model=row.get("model_name", ""),
                    method=row.get("method", ""),
                    delta=_fmt(row.get("mean_delta_f1_retuned")),
                    ece=_fmt(row.get("max_target_ece")),
                    neg=row.get("negative_retuned_count", 0),
                )
            )
    else:
        md_lines.append("- none")
    md_lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- detail_csv: `{detail_csv_path}`",
            f"- model_method_summary_csv: `{summary_csv_path}`",
            f"- summary_md: `{summary_md_path}`",
            f"- summary_json: `{summary_json_path}`",
            "",
        ]
    )
    summary_md_path.write_text("\n".join(md_lines), encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "completed",
        "transfer_scan_detail_csv_path": str(Path(transfer_scan_detail_csv_path).resolve()),
        "source_region_filter": source_filter_value,
        "model_filter": sorted(model_name_filter),
        "methods": methods_resolved,
        "threshold_grid_step": float(threshold_grid_step),
        "ece_gate_max": float(ece_gate_max),
        "max_negative_pairs_allowed": int(max_negative_pairs_allowed),
        "detail_csv_path": str(detail_csv_path),
        "model_method_summary_csv_path": str(summary_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
        "detail_row_count": len(detail_rows),
        "model_method_row_count": len(summary_rows),
        "combined_pass_fixed_count": len(combined_pass_fixed),
        "combined_pass_retuned_count": len(combined_pass_retuned),
        "top_combined_pass_fixed": best_fixed,
        "top_combined_pass_retuned": best_retuned,
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


__all__ = ["run_transfer_calibration_probe"]

