from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _escape_xml(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _dataset_to_region(dataset: str) -> str:
    if not dataset:
        return ""
    return dataset.split("_")[0]


@dataclass
class _FamilyBest:
    region: str
    dataset: str
    family: str
    model_name: str
    f1: float
    ece: float
    auroc: float


def _pick_best_by_family(leaderboard_rows: list[dict[str, str]]) -> list[_FamilyBest]:
    families = {"tabular", "regional_raster_cnn"}
    best: dict[tuple[str, str], _FamilyBest] = {}
    for row in leaderboard_rows:
        if row.get("status") != "completed":
            continue
        dataset = str(row.get("dataset", ""))
        family = str(row.get("model_family", ""))
        if family not in families:
            continue
        region = _dataset_to_region(dataset)
        candidate = _FamilyBest(
            region=region,
            dataset=dataset,
            family=family,
            model_name=str(row.get("model_name", "")),
            f1=_to_float(row.get("f1")),
            ece=_to_float(row.get("ece")),
            auroc=_to_float(row.get("auroc")),
        )
        key = (dataset, family)
        prev = best.get(key)
        if prev is None or candidate.f1 > prev.f1:
            best[key] = candidate
    return sorted(best.values(), key=lambda item: (item.dataset, item.family))


def _index_by_dataset_model(leaderboard_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    index: dict[tuple[str, str], dict[str, str]] = {}
    for row in leaderboard_rows:
        if row.get("status") != "completed":
            continue
        key = (str(row.get("dataset", "")), str(row.get("model_name", "")))
        previous = index.get(key)
        if previous is None or _to_float(row.get("f1")) > _to_float(previous.get("f1")):
            index[key] = row
    return index


def _render_grouped_bar_svg(rows: list[_FamilyBest], output_path: Path) -> None:
    regions = sorted({row.region for row in rows if row.region})
    if not regions:
        output_path.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='800' height='120'></svg>", encoding="utf-8")
        return
    families = ["tabular", "regional_raster_cnn"]
    color_map = {"tabular": "#2B6CB0", "regional_raster_cnn": "#DD6B20"}
    width = 980
    height = 520
    margin_left = 100
    margin_right = 50
    margin_top = 70
    margin_bottom = 120
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom
    group_w = chart_w / max(len(regions), 1)
    bar_w = min(44.0, group_w / 3.2)
    y_min = 0.35
    y_max = 0.90

    value_map: dict[tuple[str, str], _FamilyBest] = {(r.region, r.family): r for r in rows}

    parts: list[str] = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Arial,sans-serif;fill:#1A202C} .small{font-size:12px} .axis{font-size:11px;fill:#4A5568} .title{font-size:20px;font-weight:700} .subtitle{font-size:12px;fill:#4A5568}</style>",
        f"<text x='{margin_left}' y='34' class='title'>Figure 1. Region-wise Best Model Family Comparison (F1)</text>",
        f"<text x='{margin_left}' y='54' class='subtitle'>Best tabular vs best raster-CNN per region, using all_models_multiarea_leaderboard.csv</text>",
    ]

    for tick in [0.40, 0.50, 0.60, 0.70, 0.80, 0.90]:
        y = margin_top + chart_h * (1 - ((tick - y_min) / (y_max - y_min)))
        parts.append(f"<line x1='{margin_left}' y1='{y:.2f}' x2='{margin_left + chart_w}' y2='{y:.2f}' stroke='#E2E8F0' stroke-width='1'/>")
        parts.append(f"<text x='{margin_left - 10}' y='{y + 4:.2f}' class='axis' text-anchor='end'>{tick:.2f}</text>")

    parts.append(
        f"<rect x='{margin_left}' y='{margin_top}' width='{chart_w}' height='{chart_h}' fill='none' stroke='#A0AEC0' stroke-width='1'/>"
    )

    for i, region in enumerate(regions):
        gx = margin_left + i * group_w + group_w / 2
        for j, family in enumerate(families):
            row = value_map.get((region, family))
            value = row.f1 if row else y_min
            normalized = max(0.0, min(1.0, (value - y_min) / (y_max - y_min)))
            bar_h = chart_h * normalized
            x = gx + (j - 0.5) * (bar_w + 10) - bar_w / 2
            y = margin_top + chart_h - bar_h
            color = color_map[family]
            parts.append(f"<rect x='{x:.2f}' y='{y:.2f}' width='{bar_w:.2f}' height='{bar_h:.2f}' fill='{color}' rx='3'/>")
            if row:
                label = f"{row.f1:.3f}"
                parts.append(f"<text x='{x + bar_w/2:.2f}' y='{y - 6:.2f}' class='small' text-anchor='middle'>{label}</text>")
        parts.append(f"<text x='{gx:.2f}' y='{margin_top + chart_h + 24}' class='small' text-anchor='middle'>{_escape_xml(region)}</text>")

    legend_x = margin_left + chart_w - 240
    legend_y = margin_top + 10
    parts.append(f"<rect x='{legend_x}' y='{legend_y}' width='14' height='14' fill='{color_map['tabular']}'/>")
    parts.append(f"<text x='{legend_x + 22}' y='{legend_y + 12}' class='small'>tabular (best)</text>")
    parts.append(f"<rect x='{legend_x}' y='{legend_y + 22}' width='14' height='14' fill='{color_map['regional_raster_cnn']}'/>")
    parts.append(f"<text x='{legend_x + 22}' y='{legend_y + 34}' class='small'>regional_raster_cnn (best)</text>")

    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def _delta_to_color(delta: float) -> str:
    if delta < -0.15:
        return "#C53030"
    if delta < -0.05:
        return "#E53E3E"
    if delta < 0.0:
        return "#FC8181"
    if delta < 0.05:
        return "#BEE3F8"
    if delta < 0.15:
        return "#63B3ED"
    return "#2B6CB0"


def _render_transfer_heatmap_svg(
    transfer_rows: list[dict[str, str]],
    output_path: Path,
) -> None:
    regions = sorted(
        {
            str(row.get("source_region", "")).strip()
            for row in transfer_rows
            if str(row.get("source_region", "")).strip()
        }
        | {
            str(row.get("target_region", "")).strip()
            for row in transfer_rows
            if str(row.get("target_region", "")).strip()
        }
    )
    if not regions:
        output_path.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='800' height='120'></svg>", encoding="utf-8")
        return
    value_map: dict[tuple[str, str], float] = {}
    for row in transfer_rows:
        src = str(row.get("source_region", "")).strip()
        dst = str(row.get("target_region", "")).strip()
        if not src or not dst:
            continue
        value_map[(src, dst)] = _to_float(row.get("delta_f1"))

    width = 760
    height = 540
    margin_left = 170
    margin_top = 120
    cell = 120

    parts: list[str] = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Arial,sans-serif;fill:#1A202C}.small{font-size:12px}.title{font-size:20px;font-weight:700}.subtitle{font-size:12px;fill:#4A5568}</style>",
        "<text x='20' y='34' class='title'>Figure 2. Cross-Region Transfer ΔF1 Heatmap</text>",
        "<text x='20' y='54' class='subtitle'>Rows = source region, columns = target region (recommended model transfer)</text>",
    ]

    for i, src in enumerate(regions):
        y = margin_top + i * cell
        parts.append(f"<text x='{margin_left - 14}' y='{y + cell/2 + 4:.2f}' class='small' text-anchor='end'>{_escape_xml(src)}</text>")
    for j, dst in enumerate(regions):
        x = margin_left + j * cell
        parts.append(
            f"<text x='{x + cell/2:.2f}' y='{margin_top - 16}' class='small' text-anchor='middle'>{_escape_xml(dst)}</text>"
        )

    for i, src in enumerate(regions):
        for j, dst in enumerate(regions):
            x = margin_left + j * cell
            y = margin_top + i * cell
            if src == dst:
                color = "#EDF2F7"
                text = "-"
            else:
                value = value_map.get((src, dst), 0.0)
                color = _delta_to_color(value)
                text = f"{value:+.3f}"
            parts.append(f"<rect x='{x}' y='{y}' width='{cell}' height='{cell}' fill='{color}' stroke='white' stroke-width='2'/>")
            parts.append(f"<text x='{x + cell/2:.2f}' y='{y + cell/2 + 4:.2f}' class='small' text-anchor='middle'>{text}</text>")

    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def _render_pipeline_svg(output_path: Path) -> None:
    width = 1060
    height = 340
    boxes = [
        ("AIS Raw/Curated Data", 40, 90, "#2D3748"),
        ("Feature & Pairwise Dataset", 250, 90, "#2B6CB0"),
        ("Multi-Model Training", 500, 90, "#2F855A"),
        ("In/Out-of-Time + Transfer Eval", 730, 90, "#DD6B20"),
        ("Governance + Manuscript Assets", 930, 90, "#6B46C1"),
    ]
    parts: list[str] = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Arial,sans-serif;fill:#1A202C}.title{font-size:20px;font-weight:700}.small{font-size:12px}</style>",
        "<text x='30' y='34' class='title'>Figure 3. End-to-End Research Pipeline</text>",
    ]
    for label, x, y, color in boxes:
        parts.append(f"<rect x='{x}' y='{y}' width='170' height='88' rx='10' fill='{color}'/>")
        parts.append(
            f"<text x='{x + 85}' y='{y + 36}' text-anchor='middle' class='small' fill='white'>{_escape_xml(label)}</text>"
        )
    for i in range(len(boxes) - 1):
        x1 = boxes[i][1] + 170
        x2 = boxes[i + 1][1]
        y = 134
        parts.append(f"<line x1='{x1 + 6}' y1='{y}' x2='{x2 - 10}' y2='{y}' stroke='#4A5568' stroke-width='3'/>")
        parts.append(
            f"<polygon points='{x2 - 10},{y - 6} {x2},{y} {x2 - 10},{y + 6}' fill='#4A5568'/>"
        )
    parts.append("<text x='40' y='250' class='small'>Output: model selection, transfer-risk diagnostics, calibrated risk visualization, and manuscript-ready evidence tables.</text>")
    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def _markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join([header, sep, *body])


def _ci95_normal(mean_value: float, std_value: float, sample_size: int) -> tuple[float, float]:
    if sample_size <= 0:
        return mean_value, mean_value
    half_width = 1.96 * std_value / math.sqrt(sample_size)
    return mean_value - half_width, mean_value + half_width


def _detect_label_column(row: dict[str, str]) -> str | None:
    if "label_future_conflict" in row:
        return "label_future_conflict"
    for key in row:
        if "label" in key:
            return key
    return None


def _detect_score_column(row: dict[str, str], model_name: str) -> str | None:
    preferred = f"{model_name}_score"
    if preferred in row:
        return preferred
    for key in row:
        if key.endswith("_score"):
            return key
    return None


def _read_binary_labels_and_scores(
    *,
    predictions_csv_path: Path,
    model_name: str,
) -> tuple[list[int], list[float]]:
    if not predictions_csv_path.exists():
        return [], []
    rows = _read_csv(predictions_csv_path)
    if not rows:
        return [], []
    first = rows[0]
    label_col = _detect_label_column(first)
    score_col = _detect_score_column(first, model_name)
    if label_col is None or score_col is None:
        return [], []

    labels: list[int] = []
    scores: list[float] = []
    for row in rows:
        label_raw = row.get(label_col, "")
        score_raw = row.get(score_col, "")
        try:
            label = int(float(str(label_raw)))
        except (TypeError, ValueError):
            continue
        if label not in (0, 1):
            continue
        score = _to_float(score_raw, default=float("nan"))
        if math.isnan(score):
            continue
        labels.append(label)
        scores.append(score)
    return labels, scores


def _f1_from_labels_predictions(labels: list[int], predictions: list[int]) -> float:
    tp = fp = fn = 0
    for label, pred in zip(labels, predictions):
        if pred == 1 and label == 1:
            tp += 1
        elif pred == 1 and label == 0:
            fp += 1
        elif pred == 0 and label == 1:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision + recall == 0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if q <= 0:
        return sorted_values[0]
    if q >= 1:
        return sorted_values[-1]
    position = q * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _bootstrap_f1_ci95(
    *,
    labels: list[int],
    scores: list[float],
    threshold: float,
    n_bootstrap: int = 300,
    seed: int = 42,
) -> tuple[float, float] | None:
    if not labels or len(labels) != len(scores):
        return None
    n = len(labels)
    if n < 2:
        prediction = [1 if score >= threshold else 0 for score in scores]
        f1 = _f1_from_labels_predictions(labels, prediction)
        return f1, f1

    predictions = [1 if score >= threshold else 0 for score in scores]
    positive_indices = [idx for idx, label in enumerate(labels) if label == 1]
    negative_indices = [idx for idx, label in enumerate(labels) if label == 0]
    rng = random.Random(seed)
    bootstrap_values: list[float] = []
    for _ in range(n_bootstrap):
        sampled_labels: list[int] = []
        sampled_predictions: list[int] = []
        if positive_indices and negative_indices:
            for _ in range(len(positive_indices)):
                idx = positive_indices[rng.randrange(len(positive_indices))]
                sampled_labels.append(labels[idx])
                sampled_predictions.append(predictions[idx])
            for _ in range(len(negative_indices)):
                idx = negative_indices[rng.randrange(len(negative_indices))]
                sampled_labels.append(labels[idx])
                sampled_predictions.append(predictions[idx])
        else:
            for _ in range(n):
                idx = rng.randrange(n)
                sampled_labels.append(labels[idx])
                sampled_predictions.append(predictions[idx])
        bootstrap_values.append(_f1_from_labels_predictions(sampled_labels, sampled_predictions))
    bootstrap_values.sort()
    return _quantile(bootstrap_values, 0.025), _quantile(bootstrap_values, 0.975)


def _estimate_transfer_delta_ci95(
    *,
    transfer_row: dict[str, str],
    n_bootstrap: int = 300,
) -> dict[str, str]:
    model_name = str(transfer_row.get("recommended_model", "")).strip()
    threshold = _to_float(transfer_row.get("threshold"), default=float("nan"))
    if not model_name or math.isnan(threshold):
        return {
            "source_f1_ci95": "n/a",
            "target_f1_ci95": "n/a",
            "delta_f1_ci95": "n/a",
            "ci_method": "not_available",
        }

    target_predictions_value = str(transfer_row.get("target_predictions_csv_path", "")).strip()
    transfer_summary_value = str(transfer_row.get("transfer_summary_json_path", "")).strip()
    if not target_predictions_value or not transfer_summary_value:
        return {
            "source_f1_ci95": "n/a",
            "target_f1_ci95": "n/a",
            "delta_f1_ci95": "n/a",
            "ci_method": "not_available",
        }

    target_predictions_path = Path(target_predictions_value)
    transfer_summary_path = Path(transfer_summary_value)
    if not target_predictions_path.exists() or not transfer_summary_path.exists():
        return {
            "source_f1_ci95": "n/a",
            "target_f1_ci95": "n/a",
            "delta_f1_ci95": "n/a",
            "ci_method": "not_available",
        }

    try:
        summary_json = json.loads(transfer_summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "source_f1_ci95": "n/a",
            "target_f1_ci95": "n/a",
            "delta_f1_ci95": "n/a",
            "ci_method": "not_available",
        }

    source_predictions_value = str(summary_json.get("source_test_predictions_csv_path", "")).strip()
    if not source_predictions_value:
        return {
            "source_f1_ci95": "n/a",
            "target_f1_ci95": "n/a",
            "delta_f1_ci95": "n/a",
            "ci_method": "not_available",
        }
    source_predictions_path = Path(source_predictions_value)
    if not source_predictions_path.exists():
        return {
            "source_f1_ci95": "n/a",
            "target_f1_ci95": "n/a",
            "delta_f1_ci95": "n/a",
            "ci_method": "not_available",
        }

    source_labels, source_scores = _read_binary_labels_and_scores(
        predictions_csv_path=source_predictions_path,
        model_name=model_name,
    )
    target_labels, target_scores = _read_binary_labels_and_scores(
        predictions_csv_path=target_predictions_path,
        model_name=model_name,
    )
    if not source_labels or not target_labels:
        return {
            "source_f1_ci95": "n/a",
            "target_f1_ci95": "n/a",
            "delta_f1_ci95": "n/a",
            "ci_method": "not_available",
        }

    source_ci = _bootstrap_f1_ci95(
        labels=source_labels,
        scores=source_scores,
        threshold=threshold,
        n_bootstrap=n_bootstrap,
        seed=42,
    )
    target_ci = _bootstrap_f1_ci95(
        labels=target_labels,
        scores=target_scores,
        threshold=threshold,
        n_bootstrap=n_bootstrap,
        seed=43,
    )
    if source_ci is None or target_ci is None:
        return {
            "source_f1_ci95": "n/a",
            "target_f1_ci95": "n/a",
            "delta_f1_ci95": "n/a",
            "ci_method": "not_available",
        }
    delta_ci = (target_ci[0] - source_ci[1], target_ci[1] - source_ci[0])
    return {
        "source_f1_ci95": f"[{source_ci[0]:.4f}, {source_ci[1]:.4f}]",
        "target_f1_ci95": f"[{target_ci[0]:.4f}, {target_ci[1]:.4f}]",
        "delta_f1_ci95": f"[{delta_ci[0]:+.4f}, {delta_ci[1]:+.4f}]",
        "ci_method": f"bootstrap(n={n_bootstrap})",
    }


def _interval_width(interval_text: str) -> float | None:
    value = interval_text.strip()
    if not value.startswith("[") or not value.endswith("]"):
        return None
    inner = value[1:-1]
    pieces = [item.strip() for item in inner.split(",")]
    if len(pieces) != 2:
        return None
    try:
        lower = float(pieces[0])
        upper = float(pieces[1])
    except ValueError:
        return None
    return upper - lower


def run_manuscript_enhancement_pack(
    *,
    results_root: Path,
    output_root: Path,
) -> dict[str, str]:
    leaderboard_csv = results_root / "all_models_multiarea_leaderboard.csv"
    recommendation_csv = results_root / "all_models_seed_sweep_recommendation.csv"
    transfer_csv = results_root / "transfer_recommendation_check.csv"
    scenario_csv = results_root / "external_validity_manuscript_assets_2026-04-05_10seed_scenario_panels.csv"

    leaderboard_rows = _read_csv(leaderboard_csv)
    recommendation_rows = _read_csv(recommendation_csv)
    transfer_rows = _read_csv(transfer_csv)
    scenario_rows = _read_csv(scenario_csv)

    family_best_rows = _pick_best_by_family(leaderboard_rows)
    by_dataset_model = _index_by_dataset_model(leaderboard_rows)

    recommended_summary_rows: list[dict[str, object]] = []
    seed_sample_size = 10
    for row in recommendation_rows:
        dataset = str(row.get("dataset", ""))
        model_name = str(row.get("model_name", ""))
        matched = by_dataset_model.get((dataset, model_name), {})
        f1_mean = _to_float(row.get("f1_mean"))
        f1_std = _to_float(row.get("f1_std"))
        ece_mean = _to_float(row.get("ece_mean"))
        ece_std = _to_float(row.get("ece_std"))
        f1_ci_low, f1_ci_high = _ci95_normal(f1_mean, f1_std, seed_sample_size)
        ece_ci_low, ece_ci_high = _ci95_normal(ece_mean, ece_std, seed_sample_size)
        recommended_summary_rows.append(
            {
                "region": _dataset_to_region(dataset),
                "dataset": dataset,
                "model_family": row.get("model_family", ""),
                "model_name": model_name,
                "f1_mean_10seed": f"{f1_mean:.4f}",
                "f1_std_10seed": f"{f1_std:.4f}",
                "f1_ci95_low_10seed": f"{f1_ci_low:.4f}",
                "f1_ci95_high_10seed": f"{f1_ci_high:.4f}",
                "ece_mean_10seed": f"{ece_mean:.4f}",
                "ece_std_10seed": f"{ece_std:.4f}",
                "ece_ci95_low_10seed": f"{ece_ci_low:.4f}",
                "ece_ci95_high_10seed": f"{ece_ci_high:.4f}",
                "f1_single_eval": f"{_to_float(matched.get('f1')):.4f}",
                "ece_single_eval": f"{_to_float(matched.get('ece')):.4f}",
                "auroc_single_eval": f"{_to_float(matched.get('auroc')):.4f}",
                "selection_rule": row.get("selection_rule", ""),
            }
        )

    family_rows_for_table = [
        {
            "region": row.region,
            "dataset": row.dataset,
            "model_family": row.family,
            "model_name": row.model_name,
            "f1": f"{row.f1:.4f}",
            "ece": f"{row.ece:.4f}",
            "auroc": f"{row.auroc:.4f}",
        }
        for row in family_best_rows
    ]

    transfer_rows_for_table: list[dict[str, object]] = []
    transfer_uncertainty_rows: list[dict[str, object]] = []
    for row in transfer_rows:
        ci = _estimate_transfer_delta_ci95(transfer_row=row, n_bootstrap=300)
        transfer_rows_for_table.append(
            {
                "source_region": row.get("source_region", ""),
                "target_region": row.get("target_region", ""),
                "recommended_model": row.get("recommended_model", ""),
                "delta_f1": f"{_to_float(row.get('delta_f1')):+.4f}",
                "delta_f1_ci95": ci["delta_f1_ci95"],
                "target_ece": f"{_to_float(row.get('target_ece')):.4f}",
                "target_auroc": f"{_to_float(row.get('target_auroc')):.4f}",
            }
        )
        transfer_uncertainty_rows.append(
            {
                "source_region": row.get("source_region", ""),
                "target_region": row.get("target_region", ""),
                "recommended_model": row.get("recommended_model", ""),
                "source_f1_ci95": ci["source_f1_ci95"],
                "target_f1_ci95": ci["target_f1_ci95"],
                "delta_f1_ci95": ci["delta_f1_ci95"],
                "ci_method": ci["ci_method"],
            }
        )

    high_uncertainty_routes: list[tuple[str, str, float]] = []
    for row in transfer_uncertainty_rows:
        width = _interval_width(str(row.get("delta_f1_ci95", "")))
        if width is None:
            continue
        if width >= 0.8:
            high_uncertainty_routes.append(
                (
                    str(row.get("source_region", "")),
                    str(row.get("target_region", "")),
                    width,
                )
            )
    transfer_uncertainty_note_ko = "고불확실성 경로 없음."
    transfer_uncertainty_note_en = "No high-uncertainty transfer route detected."
    if high_uncertainty_routes:
        transfer_uncertainty_note_ko = "; ".join(
            [f"{src}->{dst} (CI 폭={width:.4f})" for src, dst, width in high_uncertainty_routes]
        )
        transfer_uncertainty_note_en = "; ".join(
            [f"{src}->{dst} (CI width={width:.4f})" for src, dst, width in high_uncertainty_routes]
        )

    family_by_region_family: dict[tuple[str, str], _FamilyBest] = {
        (row.region, row.family): row for row in family_best_rows
    }
    ablation_rows: list[dict[str, object]] = []
    for region in sorted({row.region for row in family_best_rows if row.region}):
        tabular_row = family_by_region_family.get((region, "tabular"))
        cnn_row = family_by_region_family.get((region, "regional_raster_cnn"))
        if tabular_row is None or cnn_row is None:
            continue
        delta_f1 = tabular_row.f1 - cnn_row.f1
        delta_ece = tabular_row.ece - cnn_row.ece
        if delta_f1 >= 0.03 and delta_ece <= -0.03:
            note = "tabular dominates both discrimination and calibration"
        elif delta_f1 <= -0.03 and delta_ece >= 0.03:
            note = "raster-CNN dominates both discrimination and calibration"
        else:
            note = "trade-off or near-tie between families"
        ablation_rows.append(
            {
                "region": region,
                "tabular_model": tabular_row.model_name,
                "tabular_f1": f"{tabular_row.f1:.4f}",
                "tabular_ece": f"{tabular_row.ece:.4f}",
                "raster_cnn_model": cnn_row.model_name,
                "raster_cnn_f1": f"{cnn_row.f1:.4f}",
                "raster_cnn_ece": f"{cnn_row.ece:.4f}",
                "delta_f1_tabular_minus_cnn": f"{delta_f1:+.4f}",
                "delta_ece_tabular_minus_cnn": f"{delta_ece:+.4f}",
                "interpretation": note,
            }
        )

    output_root.mkdir(parents=True, exist_ok=True)

    recommended_csv_path = output_root / "recommended_models_summary.csv"
    family_csv_path = output_root / "best_family_by_region_summary.csv"
    transfer_csv_path = output_root / "transfer_core_summary.csv"
    transfer_uncertainty_csv_path = output_root / "transfer_uncertainty_summary.csv"
    ablation_csv_path = output_root / "ablation_tabular_vs_cnn_summary.csv"

    _write_csv(
        recommended_csv_path,
        recommended_summary_rows,
        [
            "region",
            "dataset",
            "model_family",
            "model_name",
            "f1_mean_10seed",
            "f1_std_10seed",
            "f1_ci95_low_10seed",
            "f1_ci95_high_10seed",
            "ece_mean_10seed",
            "ece_std_10seed",
            "ece_ci95_low_10seed",
            "ece_ci95_high_10seed",
            "f1_single_eval",
            "ece_single_eval",
            "auroc_single_eval",
            "selection_rule",
        ],
    )
    _write_csv(
        family_csv_path,
        family_rows_for_table,
        ["region", "dataset", "model_family", "model_name", "f1", "ece", "auroc"],
    )
    _write_csv(
        transfer_csv_path,
        transfer_rows_for_table,
        [
            "source_region",
            "target_region",
            "recommended_model",
            "delta_f1",
            "delta_f1_ci95",
            "target_ece",
            "target_auroc",
        ],
    )
    _write_csv(
        transfer_uncertainty_csv_path,
        transfer_uncertainty_rows,
        [
            "source_region",
            "target_region",
            "recommended_model",
            "source_f1_ci95",
            "target_f1_ci95",
            "delta_f1_ci95",
            "ci_method",
        ],
    )
    _write_csv(
        ablation_csv_path,
        ablation_rows,
        [
            "region",
            "tabular_model",
            "tabular_f1",
            "tabular_ece",
            "raster_cnn_model",
            "raster_cnn_f1",
            "raster_cnn_ece",
            "delta_f1_tabular_minus_cnn",
            "delta_ece_tabular_minus_cnn",
            "interpretation",
        ],
    )

    fig_model_family = output_root / "figure_1_model_family_comparison.svg"
    fig_transfer_heatmap = output_root / "figure_2_transfer_delta_f1_heatmap.svg"
    fig_pipeline = output_root / "figure_3_pipeline_overview.svg"

    _render_grouped_bar_svg(family_best_rows, fig_model_family)
    _render_transfer_heatmap_svg(transfer_rows, fig_transfer_heatmap)
    _render_pipeline_svg(fig_pipeline)

    scenario_columns = [
        "region",
        "model_name",
        "f1_mean",
        "ece",
        "fp",
        "fn",
        "reliability_figure_path",
        "heatmap_contour_figure_svg_path",
        "calibration_note",
        "error_note",
    ]
    scenario_md_table = _markdown_table(
        [{key: row.get(key, "") for key in scenario_columns} for row in scenario_rows],
        scenario_columns,
    )

    figure_index_path = output_root / "figure_index.md"
    figure_index_path.write_text(
        "\n".join(
            [
                "# Figure Index (Paper Upgrade)",
                "",
                f"- Figure 1: `./{fig_model_family.name}`",
                f"- Figure 2: `./{fig_transfer_heatmap.name}`",
                f"- Figure 3: `./{fig_pipeline.name}`",
                "- Quantitative appendix tables:",
                f"  - `./{recommended_csv_path.name}`",
                f"  - `./{transfer_csv_path.name}`",
                f"  - `./{transfer_uncertainty_csv_path.name}`",
                f"  - `./{ablation_csv_path.name}`",
                "- Existing scenario visuals:",
                "  - `../../results/2026-04-04-expanded-10seed/houston_report_figure.svg`",
                "  - `../../results/2026-04-04-expanded-10seed/nola_report_figure.svg`",
                "  - `../../results/2026-04-04-expanded-10seed/seattle_report_figure.svg`",
                "",
                "## Scenario Panel Table",
                "",
                scenario_md_table,
                "",
            ]
        ),
        encoding="utf-8",
    )

    recommended_md_table = _markdown_table(
        recommended_summary_rows,
        [
            "region",
            "model_family",
            "model_name",
            "f1_mean_10seed",
            "ece_mean_10seed",
            "f1_single_eval",
            "ece_single_eval",
        ],
    )
    recommended_uncertainty_md_table = _markdown_table(
        recommended_summary_rows,
        [
            "region",
            "model_name",
            "f1_mean_10seed",
            "f1_std_10seed",
            "f1_ci95_low_10seed",
            "f1_ci95_high_10seed",
            "ece_mean_10seed",
            "ece_std_10seed",
            "ece_ci95_low_10seed",
            "ece_ci95_high_10seed",
        ],
    )
    transfer_md_table = _markdown_table(
        transfer_rows_for_table,
        ["source_region", "target_region", "recommended_model", "delta_f1", "delta_f1_ci95", "target_ece"],
    )
    transfer_uncertainty_md_table = _markdown_table(
        transfer_uncertainty_rows,
        ["source_region", "target_region", "recommended_model", "source_f1_ci95", "target_f1_ci95", "delta_f1_ci95", "ci_method"],
    )
    ablation_md_table = _markdown_table(
        ablation_rows,
        [
            "region",
            "tabular_model",
            "tabular_f1",
            "raster_cnn_model",
            "raster_cnn_f1",
            "delta_f1_tabular_minus_cnn",
            "tabular_ece",
            "raster_cnn_ece",
            "delta_ece_tabular_minus_cnn",
            "interpretation",
        ],
    )

    ablation_ko_lines: list[str] = []
    ablation_en_lines: list[str] = []
    for row in ablation_rows:
        region = str(row.get("region", ""))
        delta_f1_value = _to_float(row.get("delta_f1_tabular_minus_cnn"), default=0.0)
        delta_ece_value = _to_float(row.get("delta_ece_tabular_minus_cnn"), default=0.0)
        if delta_f1_value > 0:
            f1_phrase_ko = "tabular 우세"
            f1_phrase_en = "tabular is higher"
        elif delta_f1_value < 0:
            f1_phrase_ko = "raster-CNN 우세"
            f1_phrase_en = "raster-CNN is higher"
        else:
            f1_phrase_ko = "동률"
            f1_phrase_en = "near tie"
        if delta_ece_value < 0:
            ece_phrase_ko = "tabular 보정 우세"
            ece_phrase_en = "tabular shows better calibration"
        elif delta_ece_value > 0:
            ece_phrase_ko = "raster-CNN 보정 우세"
            ece_phrase_en = "raster-CNN shows better calibration"
        else:
            ece_phrase_ko = "보정 동률"
            ece_phrase_en = "calibration tie"
        ablation_ko_lines.append(
            f"- {region}: ΔF1(tabular-cnn)={delta_f1_value:+.4f} ({f1_phrase_ko}), "
            f"ΔECE(tabular-cnn)={delta_ece_value:+.4f} ({ece_phrase_ko})."
        )
        ablation_en_lines.append(
            f"- {region}: ΔF1(tabular-cnn)={delta_f1_value:+.4f} ({f1_phrase_en}), "
            f"ΔECE(tabular-cnn)={delta_ece_value:+.4f} ({ece_phrase_en})."
        )

    manuscript_draft_ko_path = output_root / "manuscript_draft_v0.2_2026-04-09_ko.md"
    manuscript_draft_en_path = output_root / "manuscript_draft_v0.2_2026-04-09_en.md"
    manuscript_draft_path = output_root / "manuscript_draft_v0.2_2026-04-09.md"
    manuscript_todo_path = output_root / "manuscript_todo_v0.2_2026-04-09.md"
    terminology_mapping_path = output_root / "terminology_mapping_v0.2_2026-04-09.md"
    figure_captions_path = output_root / "figure_captions_bilingual_v0.2_2026-04-09.md"

    terminology_rows = [
        {
            "concept": "Collision Risk Heatmap",
            "korean_term": "충돌위험 히트맵",
            "english_term": "collision-risk heatmap",
            "usage_note_ko": "공간 격자에서 상대 위험도를 색상 강도로 표현한 지도",
            "usage_note_en": "A map that encodes relative risk intensity over spatial grids.",
        },
        {
            "concept": "Safety Contour",
            "korean_term": "안전도 등고선",
            "english_term": "safety contour",
            "usage_note_ko": "동일 위험 임계값을 연결한 곡선; 의사결정 경계로 사용",
            "usage_note_en": "A curve connecting equal-risk thresholds for decision boundaries.",
        },
        {
            "concept": "Cross-Region Transfer",
            "korean_term": "교차 해역 전이",
            "english_term": "cross-region transfer",
            "usage_note_ko": "source 해역 학습모델을 target 해역에 적용한 일반화 성능 평가",
            "usage_note_en": "Generalization test applying a source-region-trained model to a target region.",
        },
        {
            "concept": "Domain Shift",
            "korean_term": "도메인 시프트",
            "english_term": "domain shift",
            "usage_note_ko": "학습/적용 해역 분포 차이로 성능이 변하는 현상",
            "usage_note_en": "Performance drift caused by source-target distribution mismatch.",
        },
        {
            "concept": "Expected Calibration Error",
            "korean_term": "기대 보정 오차",
            "english_term": "expected calibration error (ECE)",
            "usage_note_ko": "예측 확률과 실제 빈도의 불일치 정도; 낮을수록 바람직",
            "usage_note_en": "Mismatch between predicted confidence and empirical frequency; lower is better.",
        },
        {
            "concept": "Threshold Governance",
            "korean_term": "임계값 거버넌스",
            "english_term": "threshold governance",
            "usage_note_ko": "운영 임계값 변경 시 근거/승인/추적 규칙",
            "usage_note_en": "Policy for rationale, approval, and traceability of threshold changes.",
        },
        {
            "concept": "Own Ship",
            "korean_term": "자선(own ship)",
            "english_term": "own ship",
            "usage_note_ko": "분석 기준 선박. 최초 등장 시 자선(own ship)으로 병기",
            "usage_note_en": "Reference vessel in analysis; write as 자선(own ship) on first Korean mention.",
        },
        {
            "concept": "Rule Baseline",
            "korean_term": "규칙 기반 기준선",
            "english_term": "rule baseline",
            "usage_note_ko": "모델 성능 비교를 위한 비학습 규칙 기반 참조선",
            "usage_note_en": "Non-learning reference baseline for model-comparison benchmarking.",
        },
    ]
    terminology_md_table = _markdown_table(
        terminology_rows,
        ["concept", "korean_term", "english_term", "usage_note_ko", "usage_note_en"],
    )

    ko_text = "\n".join(
        [
            "# AIS 기반 충돌위험 히트맵 논문 초안 v0.2 (Korean)",
            "",
            "## 1. 연구 목적",
            "본 연구는 AIS 시계열 기반 모델 학습을 통해 해역별 충돌위험도를 추정하고, 이를 heatmap+contour 형태로 시각화하여 운항 의사결정에 활용 가능한지를 검증한다.",
            "",
            "## 2. 데이터/실험 설정 및 운영 프로토콜",
            "- 데이터셋: Houston, NOLA, Seattle pooled pairwise",
            "- 모델군: tabular + regional_raster_cnn + rule baseline",
            "- 검증축: in-time, out-of-time, cross-region transfer, calibration(ECE)",
            "- seed 기준: 10-seed 통계를 기본 보고 단위로 사용",
            "",
            "### 2.1 데이터 필터링 정책",
            "- `PP-01`: `mmsi + timestamp` 중복 제거",
            "- `PP-02`: 위경도 범위 오류 제거",
            "- `PP-03`: `sog < 0` 제거 및 비현실적 속력 이상치 점검",
            "- `PP-04`: `heading` 결측 시 `cog` fallback",
            "- `PP-05~PP-07`: MMSI별 정렬 후 gap segment 분리 및 소구간 보간",
            "",
            "### 2.2 split 정책",
            "- timestamp split으로 기본 시간 분리 성능을 측정한다.",
            "- own-ship split/LOO로 기준 선박 일반화 성능을 분리 점검한다.",
            "- own-ship case repeat로 반복 안정성(F1 std, CI 폭)을 함께 관리한다.",
            "",
            "### 2.3 임계값 거버넌스",
            "- 모델 선택은 `ECE gate(<=0.1)` 통과 후보 내에서 `F1 우선 + 분산 보조` 규칙을 적용한다.",
            "- transfer 평가는 source에서 고정된 threshold를 target에 그대로 적용한다.",
            "- threshold 변경 시 변경 근거, 승인, 영향(성능/보정)을 실험 로그에 함께 기록한다.",
            "",
            "## 3. 모델 선택 결과 (10-seed 기준)",
            "",
            recommended_md_table,
            "",
            "해석: 3개 지역 모두 ECE gate를 만족한 후보 중 성능과 분산을 고려해 최종 모델이 선택되었고, Houston/NOLA는 `hgbt`, Seattle은 `extra_trees`가 채택됐다.",
            "",
            "### 3.1 불확실성(95% CI)",
            recommended_uncertainty_md_table,
            "",
            "- 해석 주의: CI는 `f1_std/ece_std` 기반 정규근사(95%)이며 `n=10 seed` 가정을 사용했다.",
            "",
            "## 4. 전이 성능 핵심 결과",
            "",
            transfer_md_table,
            "",
            "해석: Houston source 전이는 음수 ΔF1이 관찰되며(domain shift), NOLA/Seattle source에서는 양수 또는 완만한 결과가 나타난다.",
            "",
            "### 4.1 전이 불확실성(bootstrap 95% CI)",
            transfer_uncertainty_md_table,
            "",
            "- 해석 주의: transfer CI는 source/target prediction CSV 기반 bootstrap 추정치다.",
            f"- 추가 주의(고불확실성 경로): {transfer_uncertainty_note_ko}",
            "",
            "## 5. 절제분석: tabular vs raster-CNN",
            "",
            ablation_md_table,
            "",
            "요약 해석:",
            *ablation_ko_lines,
            "",
            "## 6. 그림 도식 구성",
            f"- Figure 1: ![model-family]({fig_model_family.name})",
            f"- Figure 2: ![transfer-heatmap]({fig_transfer_heatmap.name})",
            f"- Figure 3: ![pipeline]({fig_pipeline.name})",
            "",
            "## 7. 용어 매핑 (KOR/ENG)",
            "",
            terminology_md_table,
            "",
            f"상세 용어 가이드는 `{terminology_mapping_path.name}`를 따른다.",
            "",
            "## 8. 이중언어 그림 캡션",
            f"- KOR/ENG 캡션 세트: `{figure_captions_path.name}`",
            "",
            "## 9. 시나리오 시각화 근거",
            "- Houston scenario: `../../results/2026-04-04-expanded-10seed/houston_report_figure.svg`",
            "- NOLA scenario: `../../results/2026-04-04-expanded-10seed/nola_report_figure.svg`",
            "- Seattle scenario: `../../results/2026-04-04-expanded-10seed/seattle_report_figure.svg`",
            "",
            "## 10. 제출 포맷 메모",
            "- 현 단계에서는 `docs`에 원고를 작성/버전관리하는 방식이 적합하다.",
            "- 최종 제출은 저널/학회 템플릿(Word/LaTeX)으로 변환하되, 내용 원천은 `docs/manuscript`를 single source로 유지한다.",
            "",
        ]
    )

    en_text = "\n".join(
        [
            "# AIS Collision-Risk Heatmap Manuscript Draft v0.2 (English)",
            "",
            "## 1. Objective",
            "This study evaluates whether AIS-based model training can estimate area-level collision risk and support navigation decisions through heatmap + contour visualization.",
            "",
            "## 2. Data, Evaluation Setup, and Governance Protocol",
            "- Datasets: Houston, NOLA, Seattle pooled pairwise",
            "- Model families: tabular + regional_raster_cnn + rule baseline",
            "- Validation axes: in-time, out-of-time, cross-region transfer, and calibration (ECE)",
            "- Seed policy: 10-seed summaries are treated as the default reporting unit",
            "",
            "### 2.1 Data Filtering Policy",
            "- `PP-01`: deduplicate by `mmsi + timestamp`",
            "- `PP-02`: remove invalid latitude/longitude range records",
            "- `PP-03`: remove `sog < 0` and screen unrealistic speed outliers",
            "- `PP-04`: fallback from missing `heading` to `cog`",
            "- `PP-05~PP-07`: sort by MMSI timestamp, split long gaps, and interpolate only small gaps",
            "",
            "### 2.2 Split Policy",
            "- Timestamp split is the baseline temporal generalization check.",
            "- Own-ship split/LOO evaluates vessel-conditioned generalization.",
            "- Own-ship case repeat tracks repeatability (F1 std and CI width).",
            "",
            "### 2.3 Threshold Governance",
            "- Model selection uses `ECE gate(<=0.1)` then `F1-first with variance tie-break` policy.",
            "- Transfer evaluation applies the source-selected threshold unchanged on target region.",
            "- Every threshold change is logged with rationale, approval, and performance/calibration impact.",
            "",
            "## 3. Final Model Selection (10-seed)",
            "",
            recommended_md_table,
            "",
            "Interpretation: all three regions satisfy the ECE gate, and the final model is chosen by performance/variance tradeoff. `hgbt` is selected for Houston and NOLA, while `extra_trees` is selected for Seattle.",
            "",
            "### 3.1 Uncertainty (95% CI)",
            recommended_uncertainty_md_table,
            "",
            "- Note: CIs use normal approximation from `f1_std/ece_std` with `n=10 seeds` assumption.",
            "",
            "## 4. Core Transfer Performance",
            "",
            transfer_md_table,
            "",
            "Interpretation: Houston as source shows negative ΔF1 (domain-shift stress), while NOLA/Seattle sources show positive or near-neutral transfer outcomes.",
            "",
            "### 4.1 Transfer Uncertainty (bootstrap 95% CI)",
            transfer_uncertainty_md_table,
            "",
            "- Note: transfer CIs are bootstrap estimates from source/target prediction CSVs.",
            f"- Additional caution (high-uncertainty routes): {transfer_uncertainty_note_en}",
            "",
            "## 5. Ablation: tabular vs raster-CNN",
            "",
            ablation_md_table,
            "",
            "Summary interpretation:",
            *ablation_en_lines,
            "",
            "## 6. Figure Set",
            f"- Figure 1: ![model-family]({fig_model_family.name})",
            f"- Figure 2: ![transfer-heatmap]({fig_transfer_heatmap.name})",
            f"- Figure 3: ![pipeline]({fig_pipeline.name})",
            "",
            "## 7. Terminology Mapping (KOR/ENG)",
            "",
            terminology_md_table,
            "",
            f"Detailed terminology guidance is provided in `{terminology_mapping_path.name}`.",
            "",
            "## 8. Bilingual Figure Captions",
            f"- KOR/ENG caption set: `{figure_captions_path.name}`",
            "",
            "## 9. Scenario Visualization Evidence",
            "- Houston scenario: `../../results/2026-04-04-expanded-10seed/houston_report_figure.svg`",
            "- NOLA scenario: `../../results/2026-04-04-expanded-10seed/nola_report_figure.svg`",
            "- Seattle scenario: `../../results/2026-04-04-expanded-10seed/seattle_report_figure.svg`",
            "",
            "## 10. Submission Format Note",
            "- At this stage, authoring in `docs` is practical and reproducible.",
            "- For venue submission, convert to the target template (Word/LaTeX) while keeping `docs/manuscript` as the single source of truth.",
            "",
        ]
    )

    manuscript_draft_ko_path.write_text(ko_text, encoding="utf-8")
    manuscript_draft_en_path.write_text(en_text, encoding="utf-8")
    manuscript_draft_path.write_text(ko_text, encoding="utf-8")
    terminology_mapping_path.write_text(
        "\n".join(
            [
                "# Terminology Mapping v0.2 (KOR/ENG)",
                "",
                "This glossary standardizes manuscript wording across Korean and English drafts.",
                "",
                terminology_md_table,
                "",
                "## Style Rules",
                "- First mention in Korean draft: write `자선(own ship)` and then use `자선` consistently.",
                "- Use `ECE` with expanded form at first mention: `expected calibration error (ECE)`.",
                "- Use `교차 해역 전이` as the default Korean label for transfer analysis sections.",
                "- Keep `domain shift` untranslated when emphasizing distribution mismatch mechanism.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    figure_captions_path.write_text(
        "\n".join(
            [
                "# Figure Captions v0.2 (KOR/ENG)",
                "",
                "## Figure 1",
                f"- Path: `./{fig_model_family.name}`",
                "- KOR: 해역별 최고 성능 모델 패밀리(F1) 비교. 각 해역에서 tabular과 regional_raster_cnn의 최고 성능 모델을 비교해 기준 모델 채택 근거를 제시한다.",
                "- ENG: Region-wise comparison of best-performing model families (F1). For each region, the best tabular and best regional_raster_cnn candidates are contrasted to justify final model-family selection.",
                "",
                "## Figure 2",
                f"- Path: `./{fig_transfer_heatmap.name}`",
                "- KOR: 교차 해역 전이 ΔF1 히트맵. 행은 source, 열은 target이며 음수 구간은 도메인 시프트 취약 구간을 의미한다.",
                "- ENG: Cross-region transfer ΔF1 heatmap. Rows indicate source regions and columns indicate target regions; negative cells indicate domain-shift-sensitive transfer routes.",
                "",
                "## Figure 3",
                f"- Path: `./{fig_pipeline.name}`",
                "- KOR: 데이터 수집부터 모델 학습, 전이 검증, 원고 산출물 생성까지의 엔드투엔드 연구 파이프라인.",
                "- ENG: End-to-end research pipeline from data curation to model training, transfer evaluation, and manuscript-ready asset generation.",
                "",
                "## Scenario Visuals (Existing)",
                "- Houston KOR: Houston 시나리오 위험도 히트맵/등고선 결과로 고위험 구역의 공간 집중을 보여준다.",
                "- Houston ENG: Houston scenario heatmap/contour output showing spatial concentration of high-risk zones.",
                "- NOLA KOR: NOLA 시나리오에서 전이 적용 후 위험도 분포 변화를 비교한다.",
                "- NOLA ENG: NOLA scenario visualization comparing risk distribution shifts under transferred models.",
                "- Seattle KOR: Seattle 시나리오의 경계 조건에서 모델 보정 품질과 위험도 표현 일관성을 점검한다.",
                "- Seattle ENG: Seattle scenario used to inspect calibration quality and consistency of risk representation under boundary conditions.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    manuscript_todo_path.write_text(
        "\n".join(
            [
                "# Manuscript TODO v0.2 (2026-04-09)",
                "",
                "## A. Bilingual Draft Preparation",
                "- [x] Prepare Korean manuscript draft file (`*_ko.md`).",
                "- [x] Prepare English manuscript draft file (`*_en.md`).",
                f"- [x] Harmonize terminology mapping (KOR/ENG) for risk, transfer, and calibration terms (`{terminology_mapping_path.name}`).",
                f"- [x] Build bilingual figure-caption pairs (KOR/ENG) for all core figures (`{figure_captions_path.name}`).",
                "",
                "## B. Scientific Strengthening",
                "- [x] Expand Methods section with data filtering, split policy, and threshold governance protocol (Section 2 in KO/EN drafts).",
                "- [x] Add explicit uncertainty/confidence interval sentences next to key quantitative claims (Sections 3.1 and 4.1, plus transfer uncertainty table).",
                "- [x] Add ablation-focused paragraph for tabular vs raster-CNN behavior by region (Section 5 + ablation summary CSV).",
                "",
                "## C. Submission Readiness",
                "- [ ] Transform markdown draft to target venue template (Word/LaTeX).",
                "- [ ] Final consistency pass between tables, figures, and manuscript claims.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "recommended_summary_csv_path": str(recommended_csv_path),
        "family_summary_csv_path": str(family_csv_path),
        "transfer_summary_csv_path": str(transfer_csv_path),
        "transfer_uncertainty_summary_csv_path": str(transfer_uncertainty_csv_path),
        "ablation_tabular_vs_cnn_csv_path": str(ablation_csv_path),
        "figure_1_model_family_comparison_svg_path": str(fig_model_family),
        "figure_2_transfer_delta_f1_heatmap_svg_path": str(fig_transfer_heatmap),
        "figure_3_pipeline_overview_svg_path": str(fig_pipeline),
        "figure_index_md_path": str(figure_index_path),
        "manuscript_draft_ko_md_path": str(manuscript_draft_ko_path),
        "manuscript_draft_en_md_path": str(manuscript_draft_en_path),
        "manuscript_draft_md_path": str(manuscript_draft_path),
        "manuscript_todo_md_path": str(manuscript_todo_path),
        "terminology_mapping_md_path": str(terminology_mapping_path),
        "figure_captions_bilingual_md_path": str(figure_captions_path),
    }
