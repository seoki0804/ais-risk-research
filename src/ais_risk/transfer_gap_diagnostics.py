from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any

from sklearn.metrics import f1_score


DETAIL_FIELDS = [
    "source_region",
    "target_region",
    "model_name",
    "status",
    "transfer_threshold",
    "source_rows",
    "source_positives",
    "target_rows",
    "target_positives",
    "source_f1_at_transfer_threshold",
    "target_f1_at_transfer_threshold",
    "delta_f1_fixed_threshold",
    "target_best_threshold",
    "target_best_f1",
    "target_retune_gain_f1",
    "delta_f1_if_target_retuned",
    "delta_f1_bootstrap_ci_low",
    "delta_f1_bootstrap_ci_high",
    "delta_f1_ci_excludes_zero_negative",
    "transfer_summary_json_path",
]

SUMMARY_FIELDS = [
    "pair_count",
    "completed_pair_count",
    "negative_delta_pair_count",
    "negative_delta_ci_pair_count",
    "pairs_with_target_retune_gain_ge_0_05",
    "max_target_retune_gain",
    "max_target_retune_gain_pair",
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
        raise ValueError("threshold_grid_step must be > 0")
    lower = max(0.0, float(minimum))
    upper = min(1.0, float(maximum))
    points: list[float] = []
    current = lower
    while current <= upper + (float(step) * 0.5):
        points.append(round(float(current), 6))
        current += float(step)
    return sorted({value for value in points if 0.0 <= value <= 1.0})


def _load_scores_labels(path: str | Path, model_name: str) -> tuple[list[float], list[int]]:
    score_key = f"{model_name}_score"
    scores: list[float] = []
    labels: list[int] = []
    for row in _parse_csv_rows(path):
        score = _safe_float(row.get(score_key))
        label = _safe_float(row.get("label_future_conflict"))
        if score is None or label not in (0.0, 1.0):
            continue
        scores.append(float(score))
        labels.append(int(label))
    return scores, labels


def _f1_at_threshold(scores: list[float], labels: list[int], threshold: float) -> float:
    preds = [1 if score >= float(threshold) else 0 for score in scores]
    return float(f1_score(labels, preds, zero_division=0))


def _best_threshold(scores: list[float], labels: list[int], threshold_grid: list[float]) -> tuple[float, float]:
    best_threshold = float(threshold_grid[0])
    best_f1 = -1.0
    for threshold in threshold_grid:
        current_f1 = _f1_at_threshold(scores, labels, threshold=threshold)
        if current_f1 > best_f1:
            best_f1 = current_f1
            best_threshold = float(threshold)
    return best_threshold, float(best_f1)


def _bootstrap_delta_f1_ci(
    source_scores: list[float],
    source_labels: list[int],
    target_scores: list[float],
    target_labels: list[int],
    threshold: float,
    bootstrap_samples: int = 500,
    random_seed: int = 42,
) -> tuple[float, float]:
    if not source_scores or not target_scores:
        return 0.0, 0.0
    rng = random.Random(int(random_seed))
    src_n = len(source_scores)
    tgt_n = len(target_scores)
    deltas: list[float] = []
    for _ in range(int(bootstrap_samples)):
        src_indices = [rng.randrange(src_n) for _ in range(src_n)]
        tgt_indices = [rng.randrange(tgt_n) for _ in range(tgt_n)]
        src_scores_boot = [source_scores[index] for index in src_indices]
        src_labels_boot = [source_labels[index] for index in src_indices]
        tgt_scores_boot = [target_scores[index] for index in tgt_indices]
        tgt_labels_boot = [target_labels[index] for index in tgt_indices]
        src_f1 = _f1_at_threshold(src_scores_boot, src_labels_boot, threshold=threshold)
        tgt_f1 = _f1_at_threshold(tgt_scores_boot, tgt_labels_boot, threshold=threshold)
        deltas.append(float(tgt_f1 - src_f1))
    if not deltas:
        return 0.0, 0.0
    deltas.sort()
    low_index = max(0, int(round(0.025 * (len(deltas) - 1))))
    high_index = min(len(deltas) - 1, int(round(0.975 * (len(deltas) - 1))))
    return float(deltas[low_index]), float(deltas[high_index])


def run_transfer_gap_diagnostics(
    transfer_check_csv_path: str | Path,
    output_prefix: str | Path,
    threshold_grid_step: float = 0.01,
    bootstrap_samples: int = 500,
    random_seed: int = 42,
) -> dict[str, Any]:
    rows = _parse_csv_rows(transfer_check_csv_path)
    grid = _build_threshold_grid(step=float(threshold_grid_step))
    detail_rows: list[dict[str, Any]] = []

    for row in rows:
        status = str(row.get("status", "")).strip()
        model_name = str(row.get("recommended_model", "")).strip()
        summary_json = str(row.get("transfer_summary_json_path", "")).strip()
        transfer_threshold = _safe_float(row.get("threshold"))
        payload: dict[str, Any] = {
            "source_region": str(row.get("source_region", "")),
            "target_region": str(row.get("target_region", "")),
            "model_name": model_name,
            "status": status,
            "transfer_threshold": transfer_threshold,
            "source_rows": 0,
            "source_positives": 0,
            "target_rows": 0,
            "target_positives": 0,
            "source_f1_at_transfer_threshold": None,
            "target_f1_at_transfer_threshold": None,
            "delta_f1_fixed_threshold": None,
            "target_best_threshold": None,
            "target_best_f1": None,
            "target_retune_gain_f1": None,
            "delta_f1_if_target_retuned": None,
            "delta_f1_bootstrap_ci_low": None,
            "delta_f1_bootstrap_ci_high": None,
            "delta_f1_ci_excludes_zero_negative": False,
            "transfer_summary_json_path": summary_json,
        }
        if status != "completed" or not model_name or not summary_json or transfer_threshold is None:
            detail_rows.append(payload)
            continue

        summary = json.loads(Path(summary_json).read_text(encoding="utf-8"))
        source_predictions_csv = summary.get("source_test_predictions_csv_path")
        target_predictions_csv = summary.get("target_predictions_csv_path")
        if not source_predictions_csv or not target_predictions_csv:
            detail_rows.append(payload)
            continue

        source_scores, source_labels = _load_scores_labels(source_predictions_csv, model_name=model_name)
        target_scores, target_labels = _load_scores_labels(target_predictions_csv, model_name=model_name)
        payload["source_rows"] = len(source_scores)
        payload["source_positives"] = int(sum(source_labels))
        payload["target_rows"] = len(target_scores)
        payload["target_positives"] = int(sum(target_labels))
        if not source_scores or not target_scores:
            detail_rows.append(payload)
            continue

        source_f1 = _f1_at_threshold(source_scores, source_labels, threshold=float(transfer_threshold))
        target_f1 = _f1_at_threshold(target_scores, target_labels, threshold=float(transfer_threshold))
        target_best_threshold, target_best_f1 = _best_threshold(target_scores, target_labels, threshold_grid=grid)
        delta_low, delta_high = _bootstrap_delta_f1_ci(
            source_scores=source_scores,
            source_labels=source_labels,
            target_scores=target_scores,
            target_labels=target_labels,
            threshold=float(transfer_threshold),
            bootstrap_samples=int(bootstrap_samples),
            random_seed=int(random_seed),
        )

        delta_f1_fixed = float(target_f1 - source_f1)
        payload.update(
            {
                "source_f1_at_transfer_threshold": source_f1,
                "target_f1_at_transfer_threshold": target_f1,
                "delta_f1_fixed_threshold": delta_f1_fixed,
                "target_best_threshold": target_best_threshold,
                "target_best_f1": target_best_f1,
                "target_retune_gain_f1": float(target_best_f1 - target_f1),
                "delta_f1_if_target_retuned": float(target_best_f1 - source_f1),
                "delta_f1_bootstrap_ci_low": delta_low,
                "delta_f1_bootstrap_ci_high": delta_high,
                "delta_f1_ci_excludes_zero_negative": bool(delta_high < 0.0),
            }
        )
        detail_rows.append(payload)

    completed_rows = [row for row in detail_rows if str(row.get("status", "")) == "completed"]
    negative_rows = [row for row in completed_rows if (row.get("delta_f1_fixed_threshold") is not None and float(row["delta_f1_fixed_threshold"]) < 0.0)]
    negative_ci_rows = [row for row in completed_rows if bool(row.get("delta_f1_ci_excludes_zero_negative"))]
    retune_rows = [
        row
        for row in completed_rows
        if row.get("target_retune_gain_f1") is not None and float(row["target_retune_gain_f1"]) >= 0.05
    ]
    max_gain_row = None
    for row in completed_rows:
        gain = _safe_float(row.get("target_retune_gain_f1"))
        if gain is None:
            continue
        if max_gain_row is None or float(gain) > float(max_gain_row["target_retune_gain_f1"]):
            max_gain_row = row

    summary_row = {
        "pair_count": len(detail_rows),
        "completed_pair_count": len(completed_rows),
        "negative_delta_pair_count": len(negative_rows),
        "negative_delta_ci_pair_count": len(negative_ci_rows),
        "pairs_with_target_retune_gain_ge_0_05": len(retune_rows),
        "max_target_retune_gain": float(max_gain_row["target_retune_gain_f1"]) if max_gain_row else None,
        "max_target_retune_gain_pair": (
            f"{max_gain_row['source_region']}->{max_gain_row['target_region']}:{max_gain_row['model_name']}"
            if max_gain_row
            else ""
        ),
    }

    output_root = Path(output_prefix).resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    detail_csv_path = output_root.with_name(output_root.name + "_detail").with_suffix(".csv")
    summary_csv_path = output_root.with_name(output_root.name + "_summary").with_suffix(".csv")
    summary_md_path = output_root.with_suffix(".md")
    summary_json_path = output_root.with_suffix(".json")
    _write_csv(detail_csv_path, detail_rows, DETAIL_FIELDS)
    _write_csv(summary_csv_path, [summary_row], SUMMARY_FIELDS)

    md_lines = [
        "# Transfer Gap Diagnostics",
        "",
        "## Inputs",
        "",
        f"- transfer_check_csv: `{Path(transfer_check_csv_path).resolve()}`",
        f"- threshold_grid_step: `{threshold_grid_step}`",
        f"- bootstrap_samples: `{bootstrap_samples}`",
        f"- random_seed: `{random_seed}`",
        "",
        "## Summary",
        "",
        f"- completed pairs: `{summary_row['completed_pair_count']}/{summary_row['pair_count']}`",
        f"- negative ΔF1 pairs: `{summary_row['negative_delta_pair_count']}`",
        f"- negative ΔF1 pairs with CI upper<0: `{summary_row['negative_delta_ci_pair_count']}`",
        f"- pairs with target retune gain >=0.05 F1: `{summary_row['pairs_with_target_retune_gain_ge_0_05']}`",
        f"- max target retune gain pair: `{summary_row['max_target_retune_gain_pair']}` (`{_fmt(summary_row['max_target_retune_gain'])}`)",
        "",
        "## Detail Snapshot",
        "",
        "| Source | Target | Model | ΔF1 fixed-th | CI95 low/high | Target retune gain | Target best th |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in completed_rows:
        md_lines.append(
            "| {src} | {tgt} | {model} | {delta} | {low}/{high} | {gain} | {best_th} |".format(
                src=row.get("source_region", ""),
                tgt=row.get("target_region", ""),
                model=row.get("model_name", ""),
                delta=_fmt(row.get("delta_f1_fixed_threshold")),
                low=_fmt(row.get("delta_f1_bootstrap_ci_low")),
                high=_fmt(row.get("delta_f1_bootstrap_ci_high")),
                gain=_fmt(row.get("target_retune_gain_f1")),
                best_th=_fmt(row.get("target_best_threshold")),
            )
        )
    md_lines.extend(
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
    summary_md_path.write_text("\n".join(md_lines), encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "completed",
        "transfer_check_csv_path": str(Path(transfer_check_csv_path).resolve()),
        "threshold_grid_step": float(threshold_grid_step),
        "bootstrap_samples": int(bootstrap_samples),
        "random_seed": int(random_seed),
        "detail_csv_path": str(detail_csv_path),
        "summary_csv_path": str(summary_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
        **summary_row,
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
