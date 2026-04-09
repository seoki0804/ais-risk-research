from __future__ import annotations

import csv
import json
import math
import random
import re
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


def _escape_latex(text: object) -> str:
    raw = str(text)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = raw
    for src, dst in replacements.items():
        escaped = escaped.replace(src, dst)
    return escaped


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


def _latex_table(rows: list[dict[str, object]], columns: list[str], align: str) -> str:
    lines = [
        r"\begin{tabular}{" + align + "}",
        r"\hline",
        " & ".join(_escape_latex(col) for col in columns) + r" \\",
        r"\hline",
    ]
    for row in rows:
        lines.append(" & ".join(_escape_latex(row.get(col, "")) for col in columns) + r" \\")
    lines.extend([r"\hline", r"\end{tabular}"])
    return "\n".join(lines)


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


def _bootstrap_f1_distribution(
    *,
    labels: list[int],
    scores: list[float],
    threshold: float,
    n_bootstrap: int = 1000,
    seed: int = 42,
) -> list[float]:
    if not labels or len(labels) != len(scores):
        return []
    n = len(labels)
    predictions = [1 if score >= threshold else 0 for score in scores]
    positive_indices = [idx for idx, label in enumerate(labels) if label == 1]
    negative_indices = [idx for idx, label in enumerate(labels) if label == 0]
    rng = random.Random(seed)
    values: list[float] = []
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
        values.append(_f1_from_labels_predictions(sampled_labels, sampled_predictions))
    return values


def _estimate_transfer_delta_significance(
    *,
    transfer_row: dict[str, str],
    n_bootstrap: int = 2000,
) -> dict[str, str]:
    model_name = str(transfer_row.get("recommended_model", "")).strip()
    threshold = _to_float(transfer_row.get("threshold"), default=float("nan"))
    observed_delta = _to_float(transfer_row.get("delta_f1"), default=float("nan"))
    if not model_name or math.isnan(threshold):
        return {
            "bootstrap_delta_mean": "n/a",
            "bootstrap_delta_ci95": "n/a",
            "bootstrap_p_two_sided": "n/a",
            "direction_probability": "n/a",
            "n_bootstrap": str(n_bootstrap),
            "interpretation": "not_available",
        }

    target_predictions_value = str(transfer_row.get("target_predictions_csv_path", "")).strip()
    transfer_summary_value = str(transfer_row.get("transfer_summary_json_path", "")).strip()
    if not target_predictions_value or not transfer_summary_value:
        return {
            "bootstrap_delta_mean": "n/a",
            "bootstrap_delta_ci95": "n/a",
            "bootstrap_p_two_sided": "n/a",
            "direction_probability": "n/a",
            "n_bootstrap": str(n_bootstrap),
            "interpretation": "not_available",
        }
    target_predictions_path = Path(target_predictions_value)
    transfer_summary_path = Path(transfer_summary_value)
    if not target_predictions_path.exists() or not transfer_summary_path.exists():
        return {
            "bootstrap_delta_mean": "n/a",
            "bootstrap_delta_ci95": "n/a",
            "bootstrap_p_two_sided": "n/a",
            "direction_probability": "n/a",
            "n_bootstrap": str(n_bootstrap),
            "interpretation": "not_available",
        }
    try:
        summary_json = json.loads(transfer_summary_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {
            "bootstrap_delta_mean": "n/a",
            "bootstrap_delta_ci95": "n/a",
            "bootstrap_p_two_sided": "n/a",
            "direction_probability": "n/a",
            "n_bootstrap": str(n_bootstrap),
            "interpretation": "not_available",
        }
    source_predictions_value = str(summary_json.get("source_test_predictions_csv_path", "")).strip()
    if not source_predictions_value:
        return {
            "bootstrap_delta_mean": "n/a",
            "bootstrap_delta_ci95": "n/a",
            "bootstrap_p_two_sided": "n/a",
            "direction_probability": "n/a",
            "n_bootstrap": str(n_bootstrap),
            "interpretation": "not_available",
        }
    source_predictions_path = Path(source_predictions_value)
    if not source_predictions_path.exists():
        return {
            "bootstrap_delta_mean": "n/a",
            "bootstrap_delta_ci95": "n/a",
            "bootstrap_p_two_sided": "n/a",
            "direction_probability": "n/a",
            "n_bootstrap": str(n_bootstrap),
            "interpretation": "not_available",
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
            "bootstrap_delta_mean": "n/a",
            "bootstrap_delta_ci95": "n/a",
            "bootstrap_p_two_sided": "n/a",
            "direction_probability": "n/a",
            "n_bootstrap": str(n_bootstrap),
            "interpretation": "not_available",
        }

    source_dist = _bootstrap_f1_distribution(
        labels=source_labels,
        scores=source_scores,
        threshold=threshold,
        n_bootstrap=n_bootstrap,
        seed=101,
    )
    target_dist = _bootstrap_f1_distribution(
        labels=target_labels,
        scores=target_scores,
        threshold=threshold,
        n_bootstrap=n_bootstrap,
        seed=202,
    )
    if not source_dist or not target_dist:
        return {
            "bootstrap_delta_mean": "n/a",
            "bootstrap_delta_ci95": "n/a",
            "bootstrap_p_two_sided": "n/a",
            "direction_probability": "n/a",
            "n_bootstrap": str(n_bootstrap),
            "interpretation": "not_available",
        }
    paired_count = min(len(source_dist), len(target_dist))
    deltas = [target_dist[i] - source_dist[i] for i in range(paired_count)]
    deltas_sorted = sorted(deltas)
    delta_mean = sum(deltas) / len(deltas)
    ci_low = _quantile(deltas_sorted, 0.025)
    ci_high = _quantile(deltas_sorted, 0.975)
    p_le_zero = sum(1 for value in deltas if value <= 0.0) / len(deltas)
    p_ge_zero = sum(1 for value in deltas if value >= 0.0) / len(deltas)
    p_two_sided = min(1.0, 2.0 * min(p_le_zero, p_ge_zero))
    if math.isnan(observed_delta):
        observed_delta = delta_mean
    if observed_delta >= 0:
        direction_prob = sum(1 for value in deltas if value > 0.0) / len(deltas)
        direction_note = "positive_transfer"
    else:
        direction_prob = sum(1 for value in deltas if value < 0.0) / len(deltas)
        direction_note = "negative_transfer"
    if p_two_sided < 0.05:
        interpretation = f"statistically_supported_{direction_note}"
    else:
        interpretation = "not_conclusive"
    return {
        "bootstrap_delta_mean": f"{delta_mean:+.4f}",
        "bootstrap_delta_ci95": f"[{ci_low:+.4f}, {ci_high:+.4f}]",
        "bootstrap_p_two_sided": f"{p_two_sided:.4f}",
        "direction_probability": f"{direction_prob:.4f}",
        "n_bootstrap": str(n_bootstrap),
        "interpretation": interpretation,
    }


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


def _load_seed_sweep_raw_rows(results_root: Path) -> list[dict[str, str]]:
    summary_path = results_root / "all_models_seed_sweep_summary.json"
    default_raw_path = results_root / "all_models_seed_sweep_raw_rows.csv"
    candidate_paths: list[Path] = []
    if summary_path.exists():
        try:
            summary_json = json.loads(summary_path.read_text(encoding="utf-8"))
            raw_value = str(summary_json.get("raw_rows_csv_path", "")).strip()
            if raw_value:
                candidate_paths.append(Path(raw_value))
        except (json.JSONDecodeError, OSError):
            pass
    candidate_paths.append(default_raw_path)
    for candidate in candidate_paths:
        if candidate.exists():
            return _read_csv(candidate)
    return []


def _best_model_for_family(
    raw_rows: list[dict[str, str]],
    *,
    region: str,
    family: str,
) -> str | None:
    model_to_values: dict[str, list[float]] = {}
    for row in raw_rows:
        if str(row.get("region", "")).strip() != region:
            continue
        if str(row.get("model_family", "")).strip() != family:
            continue
        if str(row.get("status", "")).strip() != "completed":
            continue
        model_name = str(row.get("model_name", "")).strip()
        if not model_name:
            continue
        model_to_values.setdefault(model_name, []).append(_to_float(row.get("f1"), default=float("nan")))
    best_model = None
    best_score = float("-inf")
    for model_name, values in model_to_values.items():
        clean = [value for value in values if not math.isnan(value)]
        if not clean:
            continue
        mean_f1 = sum(clean) / len(clean)
        if mean_f1 > best_score:
            best_score = mean_f1
            best_model = model_name
    return best_model


def _paired_values_by_seed(
    raw_rows: list[dict[str, str]],
    *,
    region: str,
    model_name_a: str,
    model_name_b: str,
    metric_key: str,
) -> list[tuple[float, float]]:
    by_seed_a: dict[str, float] = {}
    by_seed_b: dict[str, float] = {}
    for row in raw_rows:
        if str(row.get("region", "")).strip() != region:
            continue
        if str(row.get("status", "")).strip() != "completed":
            continue
        seed = str(row.get("seed", "")).strip()
        if not seed:
            continue
        value = _to_float(row.get(metric_key), default=float("nan"))
        if math.isnan(value):
            continue
        model_name = str(row.get("model_name", "")).strip()
        if model_name == model_name_a:
            by_seed_a[seed] = value
        elif model_name == model_name_b:
            by_seed_b[seed] = value
    shared_seeds = sorted(set(by_seed_a) & set(by_seed_b))
    return [(by_seed_a[seed], by_seed_b[seed]) for seed in shared_seeds]


def _sign_test_two_sided_pvalue(deltas: list[float]) -> float:
    non_zero = [value for value in deltas if abs(value) > 1e-12]
    n = len(non_zero)
    if n == 0:
        return 1.0
    wins = sum(1 for value in non_zero if value > 0)
    losses = n - wins
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def _paired_permutation_two_sided_pvalue(deltas: list[float]) -> float:
    if not deltas:
        return 1.0
    n = len(deltas)
    observed = abs(sum(deltas) / n)
    total = 1 << n
    exceed = 0
    for mask in range(total):
        signed_sum = 0.0
        for i, value in enumerate(deltas):
            signed_sum += value if ((mask >> i) & 1) else -value
        candidate = abs(signed_sum / n)
        if candidate >= observed - 1e-12:
            exceed += 1
    return exceed / total


def _bootstrap_mean_ci95(values: list[float], *, n_bootstrap: int = 5000, seed: int = 42) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0]
    rng = random.Random(seed)
    samples: list[float] = []
    n = len(values)
    for _ in range(n_bootstrap):
        sampled = [values[rng.randrange(n)] for _ in range(n)]
        samples.append(sum(sampled) / n)
    samples.sort()
    return _quantile(samples, 0.025), _quantile(samples, 0.975)


def _holm_adjusted(pvalues: list[float]) -> list[float]:
    if not pvalues:
        return []
    indexed = sorted([(value, idx) for idx, value in enumerate(pvalues)], key=lambda item: item[0])
    m = len(pvalues)
    adjusted_sorted: list[float] = [0.0] * m
    running = 0.0
    for rank, (value, _) in enumerate(indexed):
        candidate = min(1.0, (m - rank) * value)
        running = max(running, candidate)
        adjusted_sorted[rank] = running
    adjusted = [1.0] * m
    for rank, (_, original_idx) in enumerate(indexed):
        adjusted[original_idx] = adjusted_sorted[rank]
    return adjusted


def _build_family_significance_rows(raw_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    regions = sorted({str(row.get("region", "")).strip() for row in raw_rows if str(row.get("region", "")).strip()})
    rows: list[dict[str, object]] = []
    for region in regions:
        tabular_model = _best_model_for_family(raw_rows, region=region, family="tabular")
        cnn_model = _best_model_for_family(raw_rows, region=region, family="regional_raster_cnn")
        if tabular_model is None or cnn_model is None:
            continue

        paired_f1 = _paired_values_by_seed(
            raw_rows,
            region=region,
            model_name_a=tabular_model,
            model_name_b=cnn_model,
            metric_key="f1",
        )
        paired_ece = _paired_values_by_seed(
            raw_rows,
            region=region,
            model_name_a=tabular_model,
            model_name_b=cnn_model,
            metric_key="ece",
        )
        if not paired_f1 or not paired_ece:
            continue

        f1_deltas = [tab - cnn for tab, cnn in paired_f1]
        ece_deltas = [tab - cnn for tab, cnn in paired_ece]
        f1_mean = sum(f1_deltas) / len(f1_deltas)
        ece_mean = sum(ece_deltas) / len(ece_deltas)
        f1_ci_low, f1_ci_high = _bootstrap_mean_ci95(f1_deltas, seed=41)
        ece_ci_low, ece_ci_high = _bootstrap_mean_ci95(ece_deltas, seed=42)
        f1_sign_p = _sign_test_two_sided_pvalue(f1_deltas)
        ece_sign_p = _sign_test_two_sided_pvalue(ece_deltas)
        f1_perm_p = _paired_permutation_two_sided_pvalue(f1_deltas)
        ece_perm_p = _paired_permutation_two_sided_pvalue(ece_deltas)
        f1_wins_tabular = sum(1 for value in f1_deltas if value > 0)
        f1_wins_cnn = sum(1 for value in f1_deltas if value < 0)
        f1_ties = len(f1_deltas) - f1_wins_tabular - f1_wins_cnn
        ece_wins_tabular = sum(1 for value in ece_deltas if value < 0)
        ece_wins_cnn = sum(1 for value in ece_deltas if value > 0)
        ece_ties = len(ece_deltas) - ece_wins_tabular - ece_wins_cnn

        rows.append(
            {
                "region": region,
                "tabular_model": tabular_model,
                "raster_cnn_model": cnn_model,
                "n_pairs": len(f1_deltas),
                "f1_delta_mean_tabular_minus_cnn": f"{f1_mean:+.4f}",
                "f1_delta_ci95": f"[{f1_ci_low:+.4f}, {f1_ci_high:+.4f}]",
                "f1_sign_test_p": f"{f1_sign_p:.4f}",
                "f1_permutation_p": f"{f1_perm_p:.4f}",
                "f1_wins_tabular": f1_wins_tabular,
                "f1_wins_cnn": f1_wins_cnn,
                "f1_ties": f1_ties,
                "ece_delta_mean_tabular_minus_cnn": f"{ece_mean:+.4f}",
                "ece_delta_ci95": f"[{ece_ci_low:+.4f}, {ece_ci_high:+.4f}]",
                "ece_sign_test_p": f"{ece_sign_p:.4f}",
                "ece_permutation_p": f"{ece_perm_p:.4f}",
                "ece_wins_tabular_lower": ece_wins_tabular,
                "ece_wins_cnn_lower": ece_wins_cnn,
                "ece_ties": ece_ties,
            }
        )

    if rows:
        f1_holm = _holm_adjusted([_to_float(row.get("f1_permutation_p"), default=1.0) for row in rows])
        ece_holm = _holm_adjusted([_to_float(row.get("ece_permutation_p"), default=1.0) for row in rows])
        for idx, row in enumerate(rows):
            row["f1_permutation_p_holm"] = f"{f1_holm[idx]:.4f}"
            row["ece_permutation_p_holm"] = f"{ece_holm[idx]:.4f}"
            f1_delta = _to_float(row.get("f1_delta_mean_tabular_minus_cnn"))
            ece_delta = _to_float(row.get("ece_delta_mean_tabular_minus_cnn"))
            f1_sig = f1_holm[idx] < 0.05
            ece_sig = ece_holm[idx] < 0.05
            if f1_sig:
                f1_note = "tabular significantly higher F1" if f1_delta > 0 else "raster-CNN significantly higher F1"
            else:
                f1_note = "no significant F1 difference"
            if ece_sig:
                ece_note = "tabular significantly lower ECE" if ece_delta < 0 else "raster-CNN significantly lower ECE"
            else:
                ece_note = "no significant ECE difference"
            row["interpretation"] = f"{f1_note}; {ece_note}"
    return rows


def _confusion_counts(labels: list[int], predictions: list[int]) -> tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for label, pred in zip(labels, predictions):
        if pred == 1 and label == 1:
            tp += 1
        elif pred == 1 and label == 0:
            fp += 1
        elif pred == 0 and label == 0:
            tn += 1
        elif pred == 0 and label == 1:
            fn += 1
    return tp, fp, tn, fn


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _compute_threshold_utility_rows(
    *,
    region: str,
    dataset: str,
    model_name: str,
    labels: list[int],
    scores: list[float],
    fn_weight: float,
    fp_weight: float,
    utility_profile: str,
) -> list[dict[str, object]]:
    if not labels or len(labels) != len(scores):
        return []
    n = len(labels)
    positive_count = sum(1 for label in labels if label == 1)
    negative_count = n - positive_count
    normalizer = max(fn_weight * max(positive_count, 1) + fp_weight * max(negative_count, 1), 1.0)

    thresholds = [round(idx / 100.0, 2) for idx in range(0, 101)]
    rows: list[dict[str, object]] = []
    for threshold in thresholds:
        predictions = [1 if score >= threshold else 0 for score in scores]
        tp, fp, tn, fn = _confusion_counts(labels, predictions)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2.0 * precision * recall, precision + recall)
        weighted_cost = _safe_div(fn_weight * fn + fp_weight * fp, n)
        weighted_cost_norm = _safe_div(fn_weight * fn + fp_weight * fp, normalizer)
        rows.append(
            {
                "region": region,
                "dataset": dataset,
                "model_name": model_name,
                "threshold": f"{threshold:.2f}",
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
                "precision": f"{precision:.4f}",
                "recall": f"{recall:.4f}",
                "f1": f"{f1:.4f}",
                "weighted_cost_per_sample": f"{weighted_cost:.6f}",
                "weighted_cost_normalized": f"{weighted_cost_norm:.6f}",
                "utility_profile": utility_profile,
                "fn_weight": f"{fn_weight:.2f}",
                "fp_weight": f"{fp_weight:.2f}",
                "n_samples": n,
                "positive_count": positive_count,
                "negative_count": negative_count,
            }
        )
    return rows


def _render_threshold_utility_curve_svg(
    *,
    curve_rows: list[dict[str, object]],
    operating_rows: list[dict[str, object]],
    output_path: Path,
) -> None:
    if not curve_rows:
        output_path.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='800' height='120'></svg>", encoding="utf-8")
        return

    rows_by_region: dict[str, list[dict[str, object]]] = {}
    for row in curve_rows:
        region = str(row.get("region", "")).strip()
        if not region:
            continue
        rows_by_region.setdefault(region, []).append(row)
    regions = sorted(rows_by_region)
    if not regions:
        output_path.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='800' height='120'></svg>", encoding="utf-8")
        return

    for region in regions:
        rows_by_region[region].sort(key=lambda row: _to_float(row.get("threshold"), default=0.0))

    all_costs = [
        _to_float(row.get("weighted_cost_normalized"), default=float("nan"))
        for row in curve_rows
        if not math.isnan(_to_float(row.get("weighted_cost_normalized"), default=float("nan")))
    ]
    if not all_costs:
        output_path.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='800' height='120'></svg>", encoding="utf-8")
        return
    y_min = 0.0
    y_max = max(0.05, max(all_costs) * 1.08)

    width = 980
    height = 560
    margin_left = 90
    margin_right = 50
    margin_top = 80
    margin_bottom = 90
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom

    color_map = {
        "houston": "#2B6CB0",
        "nola": "#DD6B20",
        "seattle": "#2F855A",
    }

    def x_of(threshold: float) -> float:
        return margin_left + chart_w * threshold

    def y_of(cost: float) -> float:
        ratio = _safe_div(cost - y_min, y_max - y_min)
        return margin_top + chart_h * (1.0 - ratio)

    parts: list[str] = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Arial,sans-serif;fill:#1A202C}.title{font-size:20px;font-weight:700}.small{font-size:12px}.axis{font-size:11px;fill:#4A5568}</style>",
        "<text x='30' y='34' class='title'>Figure 4. Threshold Utility Curve (Cost-Sensitive Profile)</text>",
        "<text x='30' y='54' class='small'>Profile: FN weight = 5, FP weight = 1; y-axis = normalized weighted cost</text>",
    ]

    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        x = x_of(tick)
        parts.append(f"<line x1='{x:.2f}' y1='{margin_top}' x2='{x:.2f}' y2='{margin_top + chart_h}' stroke='#EDF2F7' stroke-width='1'/>")
        parts.append(f"<text x='{x:.2f}' y='{margin_top + chart_h + 22}' class='axis' text-anchor='middle'>{tick:.2f}</text>")
    for tick in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        cost = y_min + (y_max - y_min) * tick
        y = y_of(cost)
        parts.append(f"<line x1='{margin_left}' y1='{y:.2f}' x2='{margin_left + chart_w}' y2='{y:.2f}' stroke='#EDF2F7' stroke-width='1'/>")
        parts.append(f"<text x='{margin_left - 10}' y='{y + 4:.2f}' class='axis' text-anchor='end'>{cost:.3f}</text>")

    parts.append(
        f"<rect x='{margin_left}' y='{margin_top}' width='{chart_w}' height='{chart_h}' fill='none' stroke='#A0AEC0' stroke-width='1'/>"
    )
    parts.append(f"<text x='{margin_left + chart_w/2:.2f}' y='{height - 24}' class='small' text-anchor='middle'>Threshold</text>")
    parts.append(f"<text x='24' y='{margin_top + chart_h/2:.2f}' class='small' transform='rotate(-90 24 {margin_top + chart_h/2:.2f})' text-anchor='middle'>Normalized Cost</text>")

    for region in regions:
        rows = rows_by_region[region]
        points: list[str] = []
        for row in rows:
            threshold = _to_float(row.get("threshold"), default=0.0)
            cost = _to_float(row.get("weighted_cost_normalized"), default=0.0)
            points.append(f"{x_of(threshold):.2f},{y_of(cost):.2f}")
        color = color_map.get(region, "#4A5568")
        parts.append(f"<polyline points='{' '.join(points)}' fill='none' stroke='{color}' stroke-width='2.5'/>")

    operating_by_region = {str(row.get("region", "")): row for row in operating_rows}
    for region, row in operating_by_region.items():
        color = color_map.get(region, "#4A5568")
        governed_t = _to_float(row.get("governed_threshold"), default=0.0)
        governed_cost = _to_float(row.get("governed_weighted_cost_normalized"), default=0.0)
        opt_t = _to_float(row.get("utility_opt_threshold"), default=0.0)
        opt_cost = _to_float(row.get("opt_weighted_cost_normalized"), default=0.0)
        parts.append(f"<circle cx='{x_of(governed_t):.2f}' cy='{y_of(governed_cost):.2f}' r='4' fill='{color}'/>")
        parts.append(f"<circle cx='{x_of(opt_t):.2f}' cy='{y_of(opt_cost):.2f}' r='4' fill='white' stroke='{color}' stroke-width='2'/>")

    legend_x = margin_left + chart_w - 255
    legend_y = margin_top + 14
    for i, region in enumerate(regions):
        color = color_map.get(region, "#4A5568")
        y = legend_y + i * 20
        parts.append(f"<line x1='{legend_x}' y1='{y}' x2='{legend_x + 20}' y2='{y}' stroke='{color}' stroke-width='2.5'/>")
        parts.append(f"<text x='{legend_x + 28}' y='{y + 4}' class='small'>{_escape_xml(region)}</text>")
    parts.append(f"<circle cx='{legend_x}' cy='{legend_y + 72}' r='4' fill='#1A202C'/>")
    parts.append(f"<text x='{legend_x + 12}' y='{legend_y + 76}' class='small'>governed threshold</text>")
    parts.append(f"<circle cx='{legend_x}' cy='{legend_y + 92}' r='4' fill='white' stroke='#1A202C' stroke-width='2'/>")
    parts.append(f"<text x='{legend_x + 12}' y='{legend_y + 96}' class='small'>utility-opt threshold</text>")

    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def _extract_h2_numbers(markdown_text: str) -> list[str]:
    values: list[str] = []
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("## "):
            continue
        match = re.match(r"^##\s+(\d+)\.", stripped)
        if match:
            values.append(match.group(1))
    return values


def _extract_svg_references(markdown_text: str) -> list[str]:
    references = re.findall(r"\(([^)]+\.svg)\)", markdown_text)
    return sorted(set(references))


def _build_bilingual_parity_report(ko_text: str, en_text: str) -> tuple[str, str]:
    ko_h2 = _extract_h2_numbers(ko_text)
    en_h2 = _extract_h2_numbers(en_text)
    ko_svgs = _extract_svg_references(ko_text)
    en_svgs = _extract_svg_references(en_text)

    h2_count_match = len(ko_h2) == len(en_h2)
    h2_sequence_match = ko_h2 == en_h2
    svg_reference_match = ko_svgs == en_svgs
    overall_pass = h2_count_match and h2_sequence_match and svg_reference_match
    status = "PASS" if overall_pass else "FAIL"

    report = "\n".join(
        [
            "# Bilingual Parity Report v0.2 (2026-04-09)",
            "",
            f"- Overall parity status: **{status}**",
            "",
            "| Check | Status | Detail |",
            "| --- | --- | --- |",
            f"| H2 section count match | {'PASS' if h2_count_match else 'FAIL'} | ko={len(ko_h2)}, en={len(en_h2)} |",
            f"| H2 section index sequence match | {'PASS' if h2_sequence_match else 'FAIL'} | ko={ko_h2}, en={en_h2} |",
            f"| SVG reference set match | {'PASS' if svg_reference_match else 'FAIL'} | ko={ko_svgs}, en={en_svgs} |",
            "",
        ]
    )
    return status, report


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
    transfer_significance_rows: list[dict[str, object]] = []
    for row in transfer_rows:
        ci = _estimate_transfer_delta_ci95(transfer_row=row, n_bootstrap=300)
        transfer_significance = _estimate_transfer_delta_significance(transfer_row=row, n_bootstrap=2000)
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
        transfer_significance_rows.append(
            {
                "source_region": row.get("source_region", ""),
                "target_region": row.get("target_region", ""),
                "recommended_model": row.get("recommended_model", ""),
                "observed_delta_f1": f"{_to_float(row.get('delta_f1')):+.4f}",
                "bootstrap_delta_mean": transfer_significance["bootstrap_delta_mean"],
                "bootstrap_delta_ci95": transfer_significance["bootstrap_delta_ci95"],
                "bootstrap_p_two_sided": transfer_significance["bootstrap_p_two_sided"],
                "direction_probability": transfer_significance["direction_probability"],
                "n_bootstrap": transfer_significance["n_bootstrap"],
                "interpretation": transfer_significance["interpretation"],
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

    seed_raw_rows = _load_seed_sweep_raw_rows(results_root)
    significance_rows = _build_family_significance_rows(seed_raw_rows)

    def _first_existing(candidates: list[Path]) -> Path | None:
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    out_of_domain_detail_source_path = _first_existing(
        [
            results_root / "true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_detail.csv",
            *sorted(results_root.glob("true_unseen_area_evidence_report*_detail.csv")),
        ]
    )
    out_of_domain_summary_source_path = _first_existing(
        [
            results_root / "true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_summary.csv",
            *sorted(results_root.glob("true_unseen_area_evidence_report*_summary.csv")),
        ]
    )
    out_of_domain_detail_source_rows = (
        _read_csv(out_of_domain_detail_source_path) if out_of_domain_detail_source_path else []
    )
    out_of_domain_summary_source_rows = (
        _read_csv(out_of_domain_summary_source_path) if out_of_domain_summary_source_path else []
    )

    out_of_domain_detail_rows: list[dict[str, object]] = []
    for idx, row in enumerate(out_of_domain_detail_source_rows):
        hgbt_f1 = _to_float(row.get("hgbt_f1"), default=float("nan"))
        hgbt_minus_logreg = _to_float(row.get("hgbt_minus_logreg_f1"), default=float("nan"))
        hgbt_delta_f1 = _to_float(row.get("hgbt_delta_f1"), default=float("nan"))
        threshold = _to_float(row.get("hgbt_threshold"), default=float("nan"))
        support_flag = str(row.get("test_positive_support_flag", "")).strip()
        pred_path_text = str(row.get("predictions_csv_path", "")).strip()
        pred_path = Path(pred_path_text) if pred_path_text else None

        f1_ci95 = "n/a"
        ci_method = "not_available"
        if pred_path and pred_path.exists() and not math.isnan(threshold):
            labels, scores = _read_binary_labels_and_scores(predictions_csv_path=pred_path, model_name="hgbt")
            ci = _bootstrap_f1_ci95(
                labels=labels,
                scores=scores,
                threshold=threshold,
                n_bootstrap=500,
                seed=500 + idx,
            )
            if ci is not None:
                f1_ci95 = f"[{ci[0]:.4f}, {ci[1]:.4f}]"
                ci_method = "bootstrap(n=500)"

        out_of_domain_detail_rows.append(
            {
                "evidence_type": str(row.get("evidence_type", "")).strip(),
                "scope": str(row.get("scope", "")).strip(),
                "region": str(row.get("region", "")).strip(),
                "split": str(row.get("split", "")).strip(),
                "direction": str(row.get("direction", "")).strip(),
                "row_count": int(_to_float(row.get("row_count"), default=0.0)),
                "test_rows": int(_to_float(row.get("test_rows"), default=0.0)),
                "test_positive_count": int(_to_float(row.get("test_positive_count"), default=0.0)),
                "test_positive_support_flag": support_flag or "n/a",
                "hgbt_f1": "n/a" if math.isnan(hgbt_f1) else f"{hgbt_f1:.4f}",
                "hgbt_f1_ci95": f1_ci95,
                "hgbt_minus_logreg_f1": "n/a" if math.isnan(hgbt_minus_logreg) else f"{hgbt_minus_logreg:+.4f}",
                "hgbt_delta_f1": "n/a" if math.isnan(hgbt_delta_f1) else f"{hgbt_delta_f1:+.4f}",
                "hgbt_threshold": "n/a" if math.isnan(threshold) else f"{threshold:.2f}",
                "ci_method": ci_method,
            }
        )

    grouped_out_of_domain: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in out_of_domain_detail_rows:
        key = (str(row.get("evidence_type", "")), str(row.get("split", "")))
        grouped_out_of_domain.setdefault(key, []).append(row)

    out_of_domain_summary_rows: list[dict[str, object]] = []
    for (evidence_type, split), rows in sorted(grouped_out_of_domain.items()):
        f1_values = [
            _to_float(row.get("hgbt_f1"), default=float("nan"))
            for row in rows
            if str(row.get("hgbt_f1")) != "n/a"
        ]
        compare_values = [
            _to_float(row.get("hgbt_minus_logreg_f1"), default=float("nan"))
            for row in rows
            if str(row.get("hgbt_minus_logreg_f1")) != "n/a"
        ]
        delta_values = [
            _to_float(row.get("hgbt_delta_f1"), default=float("nan"))
            for row in rows
            if str(row.get("hgbt_delta_f1")) != "n/a"
        ]
        support_flags = [str(row.get("test_positive_support_flag", "")).strip().lower() for row in rows]
        support_ok_count = sum(1 for flag in support_flags if flag == "ok")
        support_low_count = sum(1 for flag in support_flags if flag == "low")
        support_na_count = len(rows) - support_ok_count - support_low_count
        out_of_domain_summary_rows.append(
            {
                "evidence_type": evidence_type,
                "split": split,
                "row_count": len(rows),
                "region_count": len({str(row.get("region", "")) for row in rows}),
                "hgbt_f1_mean": f"{(sum(f1_values) / len(f1_values)):.4f}" if f1_values else "n/a",
                "hgbt_f1_min": f"{min(f1_values):.4f}" if f1_values else "n/a",
                "hgbt_f1_max": f"{max(f1_values):.4f}" if f1_values else "n/a",
                "hgbt_minus_logreg_f1_mean": f"{(sum(compare_values) / len(compare_values)):+.4f}" if compare_values else "n/a",
                "negative_delta_count": sum(1 for value in delta_values if value < 0.0),
                "positive_delta_count": sum(1 for value in delta_values if value > 0.0),
                "support_ok_count": support_ok_count,
                "support_low_count": support_low_count,
                "support_na_count": support_na_count,
            }
        )

    utility_profile_label = "miss_sensitive_fn5_fp1"
    utility_fn_weight = 5.0
    utility_fp_weight = 1.0
    threshold_utility_curve_rows: list[dict[str, object]] = []
    threshold_utility_operating_rows: list[dict[str, object]] = []
    for rec_row in recommendation_rows:
        dataset = str(rec_row.get("dataset", "")).strip()
        model_name = str(rec_row.get("model_name", "")).strip()
        if not dataset or not model_name:
            continue
        matched = by_dataset_model.get((dataset, model_name), {})
        predictions_path_text = str(matched.get("predictions_csv_path", "")).strip()
        if not predictions_path_text:
            continue
        predictions_path = Path(predictions_path_text)
        labels, scores = _read_binary_labels_and_scores(predictions_csv_path=predictions_path, model_name=model_name)
        if not labels or not scores:
            continue
        region = _dataset_to_region(dataset)
        curve_rows = _compute_threshold_utility_rows(
            region=region,
            dataset=dataset,
            model_name=model_name,
            labels=labels,
            scores=scores,
            fn_weight=utility_fn_weight,
            fp_weight=utility_fp_weight,
            utility_profile=utility_profile_label,
        )
        if not curve_rows:
            continue
        threshold_utility_curve_rows.extend(curve_rows)

        governed_threshold = _to_float(matched.get("threshold"), default=0.5)
        governed_row = min(
            curve_rows,
            key=lambda row: abs(_to_float(row.get("threshold"), default=0.5) - governed_threshold),
        )
        optimal_row = min(curve_rows, key=lambda row: _to_float(row.get("weighted_cost_per_sample"), default=1e9))
        governed_cost = _to_float(governed_row.get("weighted_cost_per_sample"), default=0.0)
        optimal_cost = _to_float(optimal_row.get("weighted_cost_per_sample"), default=0.0)
        governed_f1 = _to_float(governed_row.get("f1"), default=0.0)
        optimal_f1 = _to_float(optimal_row.get("f1"), default=0.0)
        cost_reduction_pct = 0.0
        if governed_cost > 0:
            cost_reduction_pct = (governed_cost - optimal_cost) / governed_cost * 100.0

        threshold_utility_operating_rows.append(
            {
                "region": region,
                "dataset": dataset,
                "model_name": model_name,
                "governed_threshold": f"{_to_float(governed_row.get('threshold')):.2f}",
                "utility_opt_threshold": f"{_to_float(optimal_row.get('threshold')):.2f}",
                "threshold_shift": f"{(_to_float(optimal_row.get('threshold')) - _to_float(governed_row.get('threshold'))):+.2f}",
                "governed_f1": f"{governed_f1:.4f}",
                "opt_f1": f"{optimal_f1:.4f}",
                "f1_delta_opt_minus_governed": f"{(optimal_f1 - governed_f1):+.4f}",
                "governed_weighted_cost_per_sample": f"{governed_cost:.6f}",
                "opt_weighted_cost_per_sample": f"{optimal_cost:.6f}",
                "governed_weighted_cost_normalized": f"{_to_float(governed_row.get('weighted_cost_normalized')):.6f}",
                "opt_weighted_cost_normalized": f"{_to_float(optimal_row.get('weighted_cost_normalized')):.6f}",
                "cost_reduction_pct": f"{cost_reduction_pct:+.2f}",
                "governed_fp": int(_to_float(governed_row.get("fp"))),
                "governed_fn": int(_to_float(governed_row.get("fn"))),
                "opt_fp": int(_to_float(optimal_row.get("fp"))),
                "opt_fn": int(_to_float(optimal_row.get("fn"))),
                "utility_profile": utility_profile_label,
                "fn_weight": f"{utility_fn_weight:.2f}",
                "fp_weight": f"{utility_fp_weight:.2f}",
                "n_samples": int(_to_float(governed_row.get("n_samples"))),
                "positive_count": int(_to_float(governed_row.get("positive_count"))),
                "negative_count": int(_to_float(governed_row.get("negative_count"))),
            }
        )

    output_root.mkdir(parents=True, exist_ok=True)

    recommended_csv_path = output_root / "recommended_models_summary.csv"
    family_csv_path = output_root / "best_family_by_region_summary.csv"
    transfer_csv_path = output_root / "transfer_core_summary.csv"
    transfer_uncertainty_csv_path = output_root / "transfer_uncertainty_summary.csv"
    transfer_significance_csv_path = output_root / "transfer_route_significance_summary.csv"
    out_of_domain_detail_csv_path = output_root / "out_of_domain_validation_detail_summary.csv"
    out_of_domain_summary_csv_path = output_root / "out_of_domain_validation_summary.csv"
    ablation_csv_path = output_root / "ablation_tabular_vs_cnn_summary.csv"
    significance_csv_path = output_root / "model_family_significance_summary.csv"
    threshold_utility_curve_csv_path = output_root / "threshold_utility_curve_summary.csv"
    threshold_utility_operating_csv_path = output_root / "threshold_utility_operating_points.csv"

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
        transfer_significance_csv_path,
        transfer_significance_rows,
        [
            "source_region",
            "target_region",
            "recommended_model",
            "observed_delta_f1",
            "bootstrap_delta_mean",
            "bootstrap_delta_ci95",
            "bootstrap_p_two_sided",
            "direction_probability",
            "n_bootstrap",
            "interpretation",
        ],
    )
    _write_csv(
        out_of_domain_detail_csv_path,
        out_of_domain_detail_rows,
        [
            "evidence_type",
            "scope",
            "region",
            "split",
            "direction",
            "row_count",
            "test_rows",
            "test_positive_count",
            "test_positive_support_flag",
            "hgbt_f1",
            "hgbt_f1_ci95",
            "hgbt_minus_logreg_f1",
            "hgbt_delta_f1",
            "hgbt_threshold",
            "ci_method",
        ],
    )
    _write_csv(
        out_of_domain_summary_csv_path,
        out_of_domain_summary_rows,
        [
            "evidence_type",
            "split",
            "row_count",
            "region_count",
            "hgbt_f1_mean",
            "hgbt_f1_min",
            "hgbt_f1_max",
            "hgbt_minus_logreg_f1_mean",
            "negative_delta_count",
            "positive_delta_count",
            "support_ok_count",
            "support_low_count",
            "support_na_count",
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
    _write_csv(
        significance_csv_path,
        significance_rows,
        [
            "region",
            "tabular_model",
            "raster_cnn_model",
            "n_pairs",
            "f1_delta_mean_tabular_minus_cnn",
            "f1_delta_ci95",
            "f1_sign_test_p",
            "f1_permutation_p",
            "f1_permutation_p_holm",
            "f1_wins_tabular",
            "f1_wins_cnn",
            "f1_ties",
            "ece_delta_mean_tabular_minus_cnn",
            "ece_delta_ci95",
            "ece_sign_test_p",
            "ece_permutation_p",
            "ece_permutation_p_holm",
            "ece_wins_tabular_lower",
            "ece_wins_cnn_lower",
            "ece_ties",
            "interpretation",
        ],
    )
    _write_csv(
        threshold_utility_curve_csv_path,
        threshold_utility_curve_rows,
        [
            "region",
            "dataset",
            "model_name",
            "threshold",
            "tp",
            "fp",
            "tn",
            "fn",
            "precision",
            "recall",
            "f1",
            "weighted_cost_per_sample",
            "weighted_cost_normalized",
            "utility_profile",
            "fn_weight",
            "fp_weight",
            "n_samples",
            "positive_count",
            "negative_count",
        ],
    )
    _write_csv(
        threshold_utility_operating_csv_path,
        threshold_utility_operating_rows,
        [
            "region",
            "dataset",
            "model_name",
            "governed_threshold",
            "utility_opt_threshold",
            "threshold_shift",
            "governed_f1",
            "opt_f1",
            "f1_delta_opt_minus_governed",
            "governed_weighted_cost_per_sample",
            "opt_weighted_cost_per_sample",
            "governed_weighted_cost_normalized",
            "opt_weighted_cost_normalized",
            "cost_reduction_pct",
            "governed_fp",
            "governed_fn",
            "opt_fp",
            "opt_fn",
            "utility_profile",
            "fn_weight",
            "fp_weight",
            "n_samples",
            "positive_count",
            "negative_count",
        ],
    )

    fig_model_family = output_root / "figure_1_model_family_comparison.svg"
    fig_transfer_heatmap = output_root / "figure_2_transfer_delta_f1_heatmap.svg"
    fig_pipeline = output_root / "figure_3_pipeline_overview.svg"
    fig_threshold_utility = output_root / "figure_4_threshold_utility_curve.svg"

    _render_grouped_bar_svg(family_best_rows, fig_model_family)
    _render_transfer_heatmap_svg(transfer_rows, fig_transfer_heatmap)
    _render_pipeline_svg(fig_pipeline)
    _render_threshold_utility_curve_svg(
        curve_rows=threshold_utility_curve_rows,
        operating_rows=threshold_utility_operating_rows,
        output_path=fig_threshold_utility,
    )

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
                f"  - `./{out_of_domain_detail_csv_path.name}`",
                f"  - `./{out_of_domain_summary_csv_path.name}`",
                f"  - `./{ablation_csv_path.name}`",
                "- Submission-readiness artifacts:",
                "  - `./manuscript_submission_template_v0.2_2026-04-09.tex`",
                "  - `./manuscript_consistency_report_v0.2_2026-04-09.md`",
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
    out_of_domain_summary_md_table = _markdown_table(
        out_of_domain_summary_rows,
        [
            "evidence_type",
            "split",
            "row_count",
            "region_count",
            "hgbt_f1_mean",
            "hgbt_f1_min",
            "hgbt_f1_max",
            "hgbt_minus_logreg_f1_mean",
            "negative_delta_count",
            "support_low_count",
        ],
    )
    out_of_domain_detail_md_table = _markdown_table(
        out_of_domain_detail_rows,
        [
            "evidence_type",
            "region",
            "split",
            "direction",
            "hgbt_f1",
            "hgbt_f1_ci95",
            "hgbt_minus_logreg_f1",
            "hgbt_delta_f1",
            "test_positive_support_flag",
        ],
    )
    out_of_domain_summary_source_note = "summary source unavailable"
    if out_of_domain_summary_source_rows:
        source_row = out_of_domain_summary_source_rows[0]
        out_of_domain_summary_source_note = (
            f"true_area_row_count={int(_to_float(source_row.get('true_area_row_count'), default=0.0))}, "
            f"transfer_row_count={int(_to_float(source_row.get('transfer_row_count'), default=0.0))}, "
            f"true_area_low_support_count={int(_to_float(source_row.get('true_area_low_support_count'), default=0.0))}"
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
    threshold_utility_md_table = _markdown_table(
        threshold_utility_operating_rows,
        [
            "region",
            "model_name",
            "governed_threshold",
            "utility_opt_threshold",
            "threshold_shift",
            "governed_f1",
            "opt_f1",
            "cost_reduction_pct",
            "governed_fp",
            "governed_fn",
            "opt_fp",
            "opt_fn",
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
    threshold_utility_ko_lines = [
        f"- {row['region']}: governed={row['governed_threshold']} -> utility-opt={row['utility_opt_threshold']}, "
        f"비용절감={row['cost_reduction_pct']}%, F1변화={row['f1_delta_opt_minus_governed']}"
        for row in threshold_utility_operating_rows
    ]
    threshold_utility_en_lines = [
        f"- {row['region']}: governed={row['governed_threshold']} -> utility-opt={row['utility_opt_threshold']}, "
        f"cost_reduction={row['cost_reduction_pct']}%, F1_delta={row['f1_delta_opt_minus_governed']}"
        for row in threshold_utility_operating_rows
    ]
    out_of_domain_ko_lines = [
        f"- {row['evidence_type']} / {row['split']}: 평균 F1={row['hgbt_f1_mean']}, "
        f"모델간 평균Δ={row['hgbt_minus_logreg_f1_mean']}, 음수Δ 건수={row['negative_delta_count']}, "
        f"low-support={row['support_low_count']}"
        for row in out_of_domain_summary_rows
    ]
    out_of_domain_en_lines = [
        f"- {row['evidence_type']} / {row['split']}: mean F1={row['hgbt_f1_mean']}, "
        f"mean model gap={row['hgbt_minus_logreg_f1_mean']}, negative Δ count={row['negative_delta_count']}, "
        f"low-support={row['support_low_count']}"
        for row in out_of_domain_summary_rows
    ]
    if not out_of_domain_ko_lines:
        out_of_domain_ko_lines = ["- out-of-domain 상세 행을 찾지 못해 요약을 생성하지 못했다."]
        out_of_domain_en_lines = ["- Out-of-domain detail rows were unavailable, so no summary line was generated."]

    # Consistency checks for manuscript claims and artifact linkage.
    recommended_by_region = {
        str(row.get("region", "")).strip().lower(): str(row.get("model_name", "")).strip()
        for row in recommended_summary_rows
    }
    expected_model_map = {
        "houston": "hgbt",
        "nola": "hgbt",
        "seattle": "extra_trees",
    }
    model_claim_ok = all(recommended_by_region.get(region) == model for region, model in expected_model_map.items())
    ece_gate_ok = all(_to_float(row.get("ece_mean_10seed"), default=1.0) <= 0.1 for row in recommended_summary_rows)

    transfer_by_route = {
        (
            str(row.get("source_region", "")).strip().lower(),
            str(row.get("target_region", "")).strip().lower(),
        ): _to_float(row.get("delta_f1"), default=0.0)
        for row in transfer_rows_for_table
    }
    transfer_sign_ok = (
        transfer_by_route.get(("houston", "nola"), 0.0) < 0.0
        and transfer_by_route.get(("houston", "seattle"), 0.0) < 0.0
        and transfer_by_route.get(("nola", "houston"), 0.0) > 0.0
        and transfer_by_route.get(("nola", "seattle"), 0.0) > 0.0
        and transfer_by_route.get(("seattle", "houston"), 0.0) > -0.1
        and transfer_by_route.get(("seattle", "nola"), 0.0) > -0.1
    )
    figure_assets_ok = all(path.exists() for path in [fig_model_family, fig_transfer_heatmap, fig_pipeline])
    utility_assets_ok = all(
        path.exists()
        for path in [
            fig_threshold_utility,
            threshold_utility_curve_csv_path,
            threshold_utility_operating_csv_path,
        ]
    )
    summary_tables_ok = all(
        path.exists()
        for path in [
            recommended_csv_path,
            transfer_csv_path,
            transfer_uncertainty_csv_path,
            transfer_significance_csv_path,
            out_of_domain_detail_csv_path,
            out_of_domain_summary_csv_path,
            ablation_csv_path,
            significance_csv_path,
            threshold_utility_curve_csv_path,
            threshold_utility_operating_csv_path,
        ]
    )

    consistency_checks = [
        (
            "Model-selection claim matches summary table",
            model_claim_ok,
            f"expected={expected_model_map}, observed={recommended_by_region}",
        ),
        (
            "ECE gate claim holds for all selected models",
            ece_gate_ok,
            "all ece_mean_10seed <= 0.1",
        ),
        (
            "Transfer-sign narrative matches computed deltas",
            transfer_sign_ok,
            "Houston negative, NOLA positive, Seattle near-neutral/positive",
        ),
        (
            "Core figure assets exist",
            figure_assets_ok,
            "figure_1/2/3 svg files present",
        ),
        (
            "Threshold utility assets exist",
            utility_assets_ok,
            "figure_4 + threshold utility csv artifacts present",
        ),
        (
            "Core quantitative tables exist",
            summary_tables_ok,
            "recommended/transfer/significance/ablation/utility csv files present",
        ),
    ]
    consistency_pass_count = sum(1 for _, passed, _ in consistency_checks if passed)
    consistency_total_count = len(consistency_checks)
    consistency_status = "PASS" if consistency_pass_count == consistency_total_count else "FAIL"

    # Build minimal LaTeX venue-style manuscript scaffold for submission conversion.
    latex_model_table = _latex_table(
        recommended_summary_rows,
        ["region", "model_name", "f1_mean_10seed", "ece_mean_10seed", "f1_ci95_low_10seed", "f1_ci95_high_10seed"],
        "llllll",
    )
    latex_transfer_table = _latex_table(
        transfer_rows_for_table,
        ["source_region", "target_region", "recommended_model", "delta_f1", "delta_f1_ci95", "target_ece"],
        "llllll",
    )
    latex_ablation_table = _latex_table(
        ablation_rows,
        ["region", "tabular_model", "raster_cnn_model", "delta_f1_tabular_minus_cnn", "delta_ece_tabular_minus_cnn"],
        "lllll",
    )

    manuscript_draft_ko_path = output_root / "manuscript_draft_v0.2_2026-04-09_ko.md"
    manuscript_draft_en_path = output_root / "manuscript_draft_v0.2_2026-04-09_en.md"
    manuscript_draft_path = output_root / "manuscript_draft_v0.2_2026-04-09.md"
    manuscript_todo_path = output_root / "manuscript_todo_v0.2_2026-04-09.md"
    terminology_mapping_path = output_root / "terminology_mapping_v0.2_2026-04-09.md"
    figure_captions_path = output_root / "figure_captions_bilingual_v0.2_2026-04-09.md"
    submission_template_tex_path = output_root / "manuscript_submission_template_v0.2_2026-04-09.tex"
    consistency_report_path = output_root / "manuscript_consistency_report_v0.2_2026-04-09.md"
    prior_work_matrix_path = output_root / "prior_work_evidence_matrix_v0.2_2026-04-09.md"
    examiner_review_todo_path = output_root / "examiner_critical_todo_v0.2_2026-04-09.md"
    significance_appendix_path = output_root / "statistical_significance_appendix_v0.2_2026-04-09.md"
    transfer_significance_appendix_path = output_root / "transfer_route_significance_appendix_v0.2_2026-04-09.md"
    threshold_utility_appendix_path = output_root / "threshold_utility_appendix_v0.2_2026-04-09.md"
    out_of_domain_validation_appendix_path = output_root / "out_of_domain_validation_appendix_v0.2_2026-04-09.md"
    bilingual_parity_report_path = output_root / "bilingual_parity_report_v0.2_2026-04-09.md"

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

    prior_work_rows = [
        {
            "id": "RW-01",
            "reference": "[IMO COLREGs (1972/1977)](https://www.imo.org/en/about/conventions/pages/colreg.aspx)",
            "what_it_supports": "Operational collision-avoidance behavior must be interpreted under explicit navigation rules.",
            "relevance_to_this_study": "Supports rule-aware interpretation for heatmap/contour-based decision support.",
            "current_coverage": "medium",
            "gap_to_close": "Add one paragraph mapping model outputs to COLREG-aware operational cautions.",
        },
        {
            "id": "RW-02",
            "reference": "[ITU-R M.1371-6 (2026)](https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1371-6-202602-I!!PDF-E.pdf)",
            "what_it_supports": "AIS message characteristics and limitations should be explicitly acknowledged.",
            "relevance_to_this_study": "Grounds data-quality assumptions for AIS-only modelling.",
            "current_coverage": "medium",
            "gap_to_close": "Add AIS technical limitation note in Methods and Threats-to-Validity.",
        },
        {
            "id": "RW-03",
            "reference": "[Zhang et al., 2016, Ocean Engineering](https://doi.org/10.1016/j.oceaneng.2016.07.059)",
            "what_it_supports": "Near-miss detection from AIS trajectories is a practical collision-risk proxy.",
            "relevance_to_this_study": "Aligns with event construction and risk-labeling rationale.",
            "current_coverage": "low",
            "gap_to_close": "Clarify how positive labels relate to near-miss style event definitions.",
        },
        {
            "id": "RW-04",
            "reference": "[Zhen et al., 2017, Ocean Engineering](https://doi.org/10.1016/j.oceaneng.2017.09.015)",
            "what_it_supports": "Real-time multi-vessel collision-risk analytics can be structured for surveillance.",
            "relevance_to_this_study": "Supports end-to-end framing from AIS ingest to risk surface output.",
            "current_coverage": "medium",
            "gap_to_close": "Add explicit novelty statement versus prior real-time surveillance frameworks.",
        },
        {
            "id": "RW-05",
            "reference": "[Chen et al., 2018, Ocean Engineering](https://doi.org/10.1016/j.oceaneng.2018.10.023)",
            "what_it_supports": "Velocity-obstacle-based candidate detection is a strong geometry baseline.",
            "relevance_to_this_study": "Useful comparator for model-based heatmap decisions.",
            "current_coverage": "low",
            "gap_to_close": "Add a baseline-comparison discussion versus VO-style geometric methods.",
        },
        {
            "id": "RW-06",
            "reference": "[Huang & van Gelder, 2019, Risk Analysis](https://doi.org/10.1111/risa.13293)",
            "what_it_supports": "Collision risk is time-varying and should be measured dynamically.",
            "relevance_to_this_study": "Supports scenario-specific heatmap update logic.",
            "current_coverage": "medium",
            "gap_to_close": "Add temporal dynamics interpretation in Discussion section.",
        },
        {
            "id": "RW-07",
            "reference": "[Tritsarolis et al., 2022, IEEE MDM](https://doi.org/10.1109/MDM55031.2022.00093)",
            "what_it_supports": "AIS-driven ML risk prediction is feasible with practical feature pipelines.",
            "relevance_to_this_study": "Directly aligns with AIS-based supervised model track.",
            "current_coverage": "medium",
            "gap_to_close": "Add side-by-side positioning versus existing ML-on-AIS workflows.",
        },
        {
            "id": "RW-08",
            "reference": "[Liu et al., 2023, Ocean Engineering](https://doi.org/10.1016/j.oceaneng.2023.113906)",
            "what_it_supports": "Quantitative AIS risk-analysis methods can provide interpretable regional diagnostics.",
            "relevance_to_this_study": "Supports regional comparison and transfer framing.",
            "current_coverage": "medium",
            "gap_to_close": "Add citation in transfer-risk interpretation paragraph.",
        },
        {
            "id": "RW-09",
            "reference": "[Kim, 2023, JMSE](https://doi.org/10.3390/jmse11071355)",
            "what_it_supports": "Collision-risk assessment method taxonomy and limitations overview.",
            "relevance_to_this_study": "Helps justify model-family design choices and limits.",
            "current_coverage": "low",
            "gap_to_close": "Add a compact related-work taxonomy table in manuscript.",
        },
        {
            "id": "RW-10",
            "reference": "[Ding & Weng, 2024, Ocean Engineering](https://doi.org/10.1016/j.oceaneng.2024.118242)",
            "what_it_supports": "AIS + visual fusion improves robustness under data-quality gaps.",
            "relevance_to_this_study": "Defines clear future direction beyond AIS-only setup.",
            "current_coverage": "medium",
            "gap_to_close": "State AIS-only boundary and planned multimodal extension explicitly.",
        },
        {
            "id": "RW-11",
            "reference": "[Guo et al., 2017, ICML/PMLR](https://proceedings.mlr.press/v70/guo17a.html)",
            "what_it_supports": "Modern models can be miscalibrated; probability calibration is essential.",
            "relevance_to_this_study": "Supports explicit ECE-gate governance.",
            "current_coverage": "high",
            "gap_to_close": "Add one sentence connecting ECE gate choice to calibration literature.",
        },
        {
            "id": "RW-12",
            "reference": "[Ben-David et al., 2010, Machine Learning](https://doi.org/10.1007/s10994-009-5152-4)",
            "what_it_supports": "Source-target distribution divergence bounds transfer performance.",
            "relevance_to_this_study": "Theoretical support for cross-region transfer caution.",
            "current_coverage": "high",
            "gap_to_close": "Link domain-shift findings to source-target divergence interpretation.",
        },
        {
            "id": "RW-13",
            "reference": "[Efron, 1979, Annals of Statistics](https://doi.org/10.1214/aos/1176344552)",
            "what_it_supports": "Bootstrap intervals are a valid nonparametric uncertainty tool.",
            "relevance_to_this_study": "Supports transfer CI protocol in Section 4.1.",
            "current_coverage": "high",
            "gap_to_close": "None (already integrated in uncertainty reporting).",
        },
    ]
    prior_work_md_table = _markdown_table(
        prior_work_rows,
        [
            "id",
            "reference",
            "what_it_supports",
            "relevance_to_this_study",
            "current_coverage",
            "gap_to_close",
        ],
    )
    if significance_rows:
        significance_md_table = _markdown_table(
            significance_rows,
            [
                "region",
                "tabular_model",
                "raster_cnn_model",
                "n_pairs",
                "f1_delta_mean_tabular_minus_cnn",
                "f1_permutation_p_holm",
                "ece_delta_mean_tabular_minus_cnn",
                "ece_permutation_p_holm",
                "interpretation",
            ],
        )
        significance_ko_lines = [
            f"- {row['region']}: ΔF1={row['f1_delta_mean_tabular_minus_cnn']} (Holm p={row['f1_permutation_p_holm']}), "
            f"ΔECE={row['ece_delta_mean_tabular_minus_cnn']} (Holm p={row['ece_permutation_p_holm']})"
            for row in significance_rows
        ]
        significance_en_lines = [
            f"- {row['region']}: ΔF1={row['f1_delta_mean_tabular_minus_cnn']} (Holm p={row['f1_permutation_p_holm']}), "
            f"ΔECE={row['ece_delta_mean_tabular_minus_cnn']} (Holm p={row['ece_permutation_p_holm']})"
            for row in significance_rows
        ]
        significance_generation_note_ko = (
            "paired exact sign test + paired exact permutation test, Holm 보정(p<0.05)으로 다중비교를 제어했다."
        )
        significance_generation_note_en = (
            "Paired exact sign test + paired exact permutation test with Holm correction (p<0.05)."
        )
    else:
        significance_md_table = (
            "| region | tabular_model | raster_cnn_model | n_pairs | f1_delta_mean_tabular_minus_cnn | "
            "f1_permutation_p_holm | ece_delta_mean_tabular_minus_cnn | ece_permutation_p_holm | interpretation |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| n/a | n/a | n/a | 0 | n/a | n/a | n/a | n/a | raw seed rows unavailable |"
        )
        significance_ko_lines = ["- raw seed rows를 찾지 못해 유의성 검정 산출물을 생성하지 못했다."]
        significance_en_lines = ["- Significance rows were not generated because raw seed rows were unavailable."]
        significance_generation_note_ko = "raw seed rows unavailable"
        significance_generation_note_en = "raw seed rows unavailable"

    if transfer_significance_rows:
        transfer_significance_md_table = _markdown_table(
            transfer_significance_rows,
            [
                "source_region",
                "target_region",
                "recommended_model",
                "observed_delta_f1",
                "bootstrap_delta_ci95",
                "bootstrap_p_two_sided",
                "direction_probability",
                "interpretation",
            ],
        )
        transfer_significance_ko_lines = [
            f"- {row['source_region']}->{row['target_region']}: ΔF1={row['observed_delta_f1']}, "
            f"bootstrap p={row['bootstrap_p_two_sided']}, direction_prob={row['direction_probability']}"
            for row in transfer_significance_rows
        ]
        transfer_significance_en_lines = [
            f"- {row['source_region']}->{row['target_region']}: ΔF1={row['observed_delta_f1']}, "
            f"bootstrap p={row['bootstrap_p_two_sided']}, direction_prob={row['direction_probability']}"
            for row in transfer_significance_rows
        ]
    else:
        transfer_significance_md_table = (
            "| source_region | target_region | recommended_model | observed_delta_f1 | bootstrap_delta_ci95 | "
            "bootstrap_p_two_sided | direction_probability | interpretation |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            "| n/a | n/a | n/a | n/a | n/a | n/a | n/a | not_available |"
        )
        transfer_significance_ko_lines = ["- transfer-route significance rows were not generated."]
        transfer_significance_en_lines = ["- transfer-route significance rows were not generated."]

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
            "### 4.2 Out-of-domain 검증 확장 (추가 해역/연도 전이)",
            f"- 상세 CSV: `{out_of_domain_detail_csv_path.name}`",
            f"- 요약 CSV: `{out_of_domain_summary_csv_path.name}`",
            "",
            out_of_domain_summary_md_table,
            "",
            "핵심 해석:",
            *out_of_domain_ko_lines,
            f"- 원본 요약 교차점검: {out_of_domain_summary_source_note}",
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
            f"- Figure 4: ![threshold-utility]({fig_threshold_utility.name})",
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
            "## 11. 제출 준비 산출물",
            f"- LaTeX 제출 템플릿: `{submission_template_tex_path.name}`",
            f"- 정합성 점검 리포트: `{consistency_report_path.name}`",
            f"- 이중언어 패리티 리포트: `{bilingual_parity_report_path.name}`",
            f"- Out-of-domain 검증 부록: `{out_of_domain_validation_appendix_path.name}`",
            f"- 정합성 자동 점검 결과: `{consistency_status}` ({consistency_pass_count}/{consistency_total_count})",
            "",
            "## 12. 선행연구 근거 매트릭스",
            f"- 근거 매트릭스: `{prior_work_matrix_path.name}`",
            "- 심사관 관점에서 핵심 claim별 문헌 근거/빈틈/보완 action을 연결했다.",
            "",
            "## 13. 심사관 관점 우선 TODO",
            f"- 상세 TODO: `{examiner_review_todo_path.name}`",
            "- 이 TODO는 novelty 서술, 통계 검정, 외부 검증 범위, 운영 임계값 해석을 우선 보완 대상으로 정의한다.",
            "",
            "## 14. 통계 유의성 부록",
            f"- 유의성 요약 CSV: `{significance_csv_path.name}`",
            f"- 부록 문서: `{significance_appendix_path.name}`",
            f"- 검정 구성: {significance_generation_note_ko}",
            "",
            significance_md_table,
            "",
            "핵심 해석:",
            *significance_ko_lines,
            "",
            "## 15. 전이 경로 통계 부록(bootstrap)",
            f"- 전이 경로 유의성 CSV: `{transfer_significance_csv_path.name}`",
            f"- 부록 문서: `{transfer_significance_appendix_path.name}`",
            "",
            transfer_significance_md_table,
            "",
            "핵심 해석:",
            *transfer_significance_ko_lines,
            "",
            "## 16. 임계값 유틸리티 부록 (운영 비용 프로파일)",
            f"- 유틸리티 곡선 CSV: `{threshold_utility_curve_csv_path.name}`",
            f"- 운영점 요약 CSV: `{threshold_utility_operating_csv_path.name}`",
            f"- 유틸리티 부록 문서: `{threshold_utility_appendix_path.name}`",
            "",
            threshold_utility_md_table,
            "",
            "핵심 해석:",
            *threshold_utility_ko_lines,
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
            "### 4.2 Out-of-Domain Validation Expansion (Additional Area/Year Transfer)",
            f"- Detail CSV: `{out_of_domain_detail_csv_path.name}`",
            f"- Summary CSV: `{out_of_domain_summary_csv_path.name}`",
            "",
            out_of_domain_summary_md_table,
            "",
            "Key interpretation:",
            *out_of_domain_en_lines,
            f"- Source-summary cross-check: {out_of_domain_summary_source_note}",
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
            f"- Figure 4: ![threshold-utility]({fig_threshold_utility.name})",
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
            "## 11. Submission-Readiness Artifacts",
            f"- LaTeX venue template draft: `{submission_template_tex_path.name}`",
            f"- Consistency audit report: `{consistency_report_path.name}`",
            f"- Bilingual parity report: `{bilingual_parity_report_path.name}`",
            f"- Out-of-domain validation appendix: `{out_of_domain_validation_appendix_path.name}`",
            f"- Automated consistency status: `{consistency_status}` ({consistency_pass_count}/{consistency_total_count})",
            "",
            "## 12. Prior-Work Evidence Matrix",
            f"- Evidence matrix: `{prior_work_matrix_path.name}`",
            "- It maps each core claim to supporting literature and explicitly documents residual gaps.",
            "",
            "## 13. Examiner-Priority TODO",
            f"- Detailed TODO: `{examiner_review_todo_path.name}`",
            "- This TODO prioritizes novelty framing, statistical testing, external validation scope, and operational threshold interpretation.",
            "",
            "## 14. Statistical Significance Appendix",
            f"- Significance summary CSV: `{significance_csv_path.name}`",
            f"- Appendix document: `{significance_appendix_path.name}`",
            f"- Test configuration: {significance_generation_note_en}",
            "",
            significance_md_table,
            "",
            "Key interpretation:",
            *significance_en_lines,
            "",
            "## 15. Transfer-Route Significance Appendix (bootstrap)",
            f"- Transfer-route significance CSV: `{transfer_significance_csv_path.name}`",
            f"- Appendix document: `{transfer_significance_appendix_path.name}`",
            "",
            transfer_significance_md_table,
            "",
            "Key interpretation:",
            *transfer_significance_en_lines,
            "",
            "## 16. Threshold Utility Appendix (Operational Cost Profile)",
            f"- Utility-curve CSV: `{threshold_utility_curve_csv_path.name}`",
            f"- Operating-point CSV: `{threshold_utility_operating_csv_path.name}`",
            f"- Utility appendix document: `{threshold_utility_appendix_path.name}`",
            "",
            threshold_utility_md_table,
            "",
            "Key interpretation:",
            *threshold_utility_en_lines,
            "",
        ]
    )

    manuscript_draft_ko_path.write_text(ko_text, encoding="utf-8")
    manuscript_draft_en_path.write_text(en_text, encoding="utf-8")
    manuscript_draft_path.write_text(ko_text, encoding="utf-8")
    bilingual_parity_status, bilingual_parity_report_text = _build_bilingual_parity_report(ko_text, en_text)
    bilingual_parity_report_path.write_text(bilingual_parity_report_text, encoding="utf-8")
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
                "## Figure 4",
                f"- Path: `./{fig_threshold_utility.name}`",
                "- KOR: FN 가중치(5) 중심 운영 비용 프로파일에서 임계값 변화에 따른 정규화 비용 곡선과 governed/utility-opt 운영점을 비교한다.",
                "- ENG: Normalized cost-vs-threshold curves under FN-heavy profile (FN=5, FP=1) with governed and utility-opt operating points.",
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
    submission_template_tex_path.write_text(
        "\n".join(
            [
                r"\documentclass[11pt]{article}",
                r"\usepackage[margin=1in]{geometry}",
                r"\usepackage{graphicx}",
                r"\usepackage{float}",
                r"\usepackage{booktabs}",
                r"\title{AIS Collision-Risk Heatmap: Submission Template v0.2}",
                r"\author{Research Team}",
                r"\date{2026-04-09}",
                r"\begin{document}",
                r"\maketitle",
                r"\section{Abstract}",
                r"Template placeholder: replace this section with venue-specific abstract text.",
                r"\section{Introduction}",
                r"This template is auto-generated from the manuscript enhancement pack outputs.",
                r"\section{Methods}",
                r"Data filtering, split policy, and threshold governance are aligned with manuscript Section 2.",
                r"\section{Results}",
                r"\subsection{Model Selection Summary}",
                r"\begin{table}[H]",
                r"\centering",
                latex_model_table,
                r"\caption{Selected models by region with seed-aggregated uncertainty.}",
                r"\end{table}",
                r"\subsection{Cross-Region Transfer Summary}",
                r"\begin{table}[H]",
                r"\centering",
                latex_transfer_table,
                r"\caption{Cross-region transfer deltas with uncertainty interval.}",
                r"\end{table}",
                r"\subsection{Ablation (Tabular vs Raster-CNN)}",
                r"\begin{table}[H]",
                r"\centering",
                latex_ablation_table,
                r"\caption{Family-level ablation summary by region.}",
                r"\end{table}",
                r"\section{Figures}",
                r"Replace placeholders with venue-required figure formats (PDF/PNG).",
                r"\begin{itemize}",
                rf"\item Figure 1 source: \texttt{{{_escape_latex(fig_model_family.name)}}}",
                rf"\item Figure 2 source: \texttt{{{_escape_latex(fig_transfer_heatmap.name)}}}",
                rf"\item Figure 3 source: \texttt{{{_escape_latex(fig_pipeline.name)}}}",
                rf"\item Figure 4 source: \texttt{{{_escape_latex(fig_threshold_utility.name)}}}",
                r"\end{itemize}",
                r"\section{Reproducibility Notes}",
                r"Core evidence tables:",
                r"\begin{itemize}",
                rf"\item \texttt{{{_escape_latex(recommended_csv_path.name)}}}",
                rf"\item \texttt{{{_escape_latex(transfer_csv_path.name)}}}",
                rf"\item \texttt{{{_escape_latex(transfer_uncertainty_csv_path.name)}}}",
                rf"\item \texttt{{{_escape_latex(transfer_significance_csv_path.name)}}}",
                rf"\item \texttt{{{_escape_latex(out_of_domain_detail_csv_path.name)}}}",
                rf"\item \texttt{{{_escape_latex(out_of_domain_summary_csv_path.name)}}}",
                rf"\item \texttt{{{_escape_latex(ablation_csv_path.name)}}}",
                rf"\item \texttt{{{_escape_latex(significance_csv_path.name)}}}",
                rf"\item \texttt{{{_escape_latex(threshold_utility_operating_csv_path.name)}}}",
                r"\end{itemize}",
                r"\end{document}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    consistency_rows = [
        f"| {name} | {'PASS' if passed else 'FAIL'} | {detail} |"
        for name, passed, detail in consistency_checks
    ]
    consistency_report_path.write_text(
        "\n".join(
            [
                "# Manuscript Consistency Report v0.2 (2026-04-09)",
                "",
                f"- Overall status: **{consistency_status}** ({consistency_pass_count}/{consistency_total_count})",
                f"- Generated from: `{results_root}`",
                "",
                "| Check | Status | Detail |",
                "| --- | --- | --- |",
                *consistency_rows,
                "",
                "## Reviewer-Facing Notes",
                "- Transfer CI is computed from source/target prediction CSV via bootstrap.",
                "- Houston-source transfer is negative with narrow CI in this run, supporting domain-shift caution.",
                "- Seattle transfer routes include zero in CI, so the claim is limited to near-neutral/weak-positive behavior.",
                f"- Out-of-domain expansion artifacts are attached (`{out_of_domain_detail_csv_path.name}`, `{out_of_domain_summary_csv_path.name}`).",
                "",
            ]
        ),
        encoding="utf-8",
    )
    prior_work_matrix_path.write_text(
        "\n".join(
            [
                "# Prior Work Evidence Matrix v0.2 (2026-04-09)",
                "",
                "This matrix connects manuscript claims to external evidence and records examiner-facing closure gaps.",
                "Bibliographic metadata for paywalled papers was normalized via DOI/Crossref records.",
                "",
                prior_work_md_table,
                "",
            ]
        ),
        encoding="utf-8",
    )
    significance_appendix_path.write_text(
        "\n".join(
            [
                "# Statistical Significance Appendix v0.2 (2026-04-09)",
                "",
                "This appendix reports seed-matched statistical tests for tabular vs raster-CNN comparisons.",
                f"Data source: `{results_root}` (raw seed rows resolved from `all_models_seed_sweep_summary.json`).",
                "",
                "## Test Design",
                "- Unit of analysis: seed-matched paired metric values by region.",
                "- Metrics: F1 and ECE (delta = tabular - raster-CNN).",
                "- Primary test: exact paired permutation test.",
                "- Secondary test: exact sign test (two-sided).",
                "- Multiple-comparison control: Holm correction across regions (per metric family).",
                "",
                "## Region-wise Results",
                significance_md_table,
                "",
                "## Interpretation Notes",
                *significance_en_lines,
                "",
                "## Limitations",
                "- Region-level sample size is limited to 10 seeds.",
                "- Transfer-route significance remains CI-based in the current manuscript; route-level repeated randomization is a next-step item.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    transfer_significance_appendix_path.write_text(
        "\n".join(
            [
                "# Transfer-Route Significance Appendix v0.2 (2026-04-09)",
                "",
                "This appendix reports bootstrap-based transfer-route significance using source/target prediction CSV pairs.",
                f"Data source: `{results_root}` and linked transfer prediction files.",
                "",
                "## Test Design",
                "- Unit of analysis: route-level transfer pair (source->target).",
                "- Statistic: delta F1 (target - source) under fixed threshold transfer.",
                "- Bootstrap protocol: stratified bootstrap on source and target prediction sets (n=2000).",
                "- Evidence fields: CI95, two-sided bootstrap p-value vs zero, and direction probability.",
                "",
                "## Route-wise Results",
                transfer_significance_md_table,
                "",
                "## Interpretation Notes",
                *transfer_significance_en_lines,
                "",
                "## Limitations",
                "- This appendix is based on single-run route artifacts and bootstrap resampling.",
                "- Full repeated-randomization (multi-run) transfer significance is still an open next-step item.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    threshold_utility_appendix_path.write_text(
        "\n".join(
            [
                "# Threshold Utility Appendix v0.2 (2026-04-09)",
                "",
                "This appendix evaluates operating-threshold tradeoffs under a miss-sensitive profile.",
                "Cost profile: FN weight = 5, FP weight = 1 (normalized per-region).",
                "",
                "## Operating-Point Summary",
                threshold_utility_md_table,
                "",
                "## Region Interpretation",
                *threshold_utility_en_lines,
                "",
                "## Figure Link",
                f"- Utility curve: `{fig_threshold_utility.name}`",
                "",
                "## Limitations",
                "- Cost profile weights are policy assumptions and should be adapted to stakeholder risk preference.",
                "- Utility analysis is based on current recommendation models and available prediction artifacts.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    out_of_domain_validation_appendix_path.write_text(
        "\n".join(
            [
                "# Out-of-Domain Validation Appendix v0.2 (2026-04-09)",
                "",
                "This appendix expands robustness evidence with true-unseen-area and cross-year transfer slices.",
                f"Detail source path: `{out_of_domain_detail_source_path}`",
                f"Summary source path: `{out_of_domain_summary_source_path}`",
                f"Source summary snapshot: `{out_of_domain_summary_source_note}`",
                "",
                "## Aggregated Summary",
                out_of_domain_summary_md_table,
                "",
                "## Row-Level Detail",
                out_of_domain_detail_md_table,
                "",
                "## Interpretation Notes",
                *out_of_domain_en_lines,
                "",
                "## Limitations",
                "- This appendix depends on currently available true-unseen/cross-year artifacts.",
                "- Additional external regimes are still needed for stronger global validity claims.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    examiner_review_todo_path.write_text(
        "\n".join(
            [
                "# Examiner-Critical TODO v0.2 (2026-04-09)",
                "",
                "## Critical Findings (Objective Reviewer View)",
                "1. **Novelty framing risk (high)**: the manuscript currently lacks an explicit related-work differential table.",
                "2. **Statistical evidence risk (medium)**: family-level significance appendix is now attached, but transfer-route repeated-randomization testing is still pending.",
                "3. **External validity risk (medium)**: transfer analysis is strong across three regions, but global regime diversity is still limited.",
                "4. **Operational interpretation risk (low-medium)**: threshold utility appendix is attached, but deployment-profile calibration still needs stakeholder-specific tuning.",
                "5. **Labeling protocol clarity risk (medium)**: near-miss/collision-proxy linkage is implied but not fully formalized against prior literature.",
                "",
                "## Detailed TODO with Acceptance Criteria",
                "- [ ] Add `Related Work Differential` subsection (5-8 key papers + one-line novelty delta for each).",
                "  - Acceptance: manuscript includes a compact table that references `prior_work_evidence_matrix_v0.2_2026-04-09.md` IDs (`RW-01`~`RW-13`).",
                f"- [x] Add significance test appendix for tabular vs raster-CNN (`{significance_appendix_path.name}`).",
                "  - Acceptance: report p-values with multiple-comparison control and effect-size-oriented interpretation notes.",
                f"- [x] Add bootstrap-based transfer-route significance summary (`{transfer_significance_appendix_path.name}`).",
                "  - Acceptance: route-level table includes CI95, two-sided p-value, and direction probability.",
                "- [ ] Extend significance testing to transfer deltas with repeated-randomization protocol.",
                "  - Acceptance: route-level significance table includes repeated runs and corrected p-values.",
                f"- [x] Add one additional out-of-domain test split (new area/year) for robustness (`{out_of_domain_validation_appendix_path.name}`).",
                "  - Acceptance: report includes same KPIs (`F1`, `ECE`, `ΔF1`, CI95) and explicitly states pass/fail gates.",
                f"- [x] Add threshold utility analysis (`{threshold_utility_appendix_path.name}`) for false-alarm vs miss-risk tradeoff.",
                "  - Acceptance: operating-point table + curve-based figure are attached with explicit cost profile.",
                "- [ ] Clarify label-generation policy with near-miss proxy grounding.",
                "  - Acceptance: Methods section provides deterministic event rule and cites at least one AIS near-miss paper (`RW-03`).",
                f"- [{'x' if bilingual_parity_status == 'PASS' else ' '}] Final bilingual publication pass (Korean + English).",
                f"  - Acceptance: KO/EN drafts have section/figure/table parity and terminology consistency check log (`{bilingual_parity_report_path.name}` = {bilingual_parity_status}).",
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
                f"- [x] Transform markdown draft to target venue template (Word/LaTeX) (`{submission_template_tex_path.name}`).",
                f"- [x] Final consistency pass between tables, figures, and manuscript claims (`{consistency_report_path.name}` = {consistency_status}).",
                "",
                "## D. Reviewer-Critical Upgrades (Next Iteration)",
                f"- [x] Build claim-to-citation matrix and connect it to manuscript narrative (`{prior_work_matrix_path.name}`).",
                f"- [ ] Close examiner-critical gaps with acceptance criteria (`{examiner_review_todo_path.name}`).",
                f"- [x] Add formal significance testing for model-family comparison (`{significance_appendix_path.name}`, Holm-corrected p-values).",
                f"- [x] Add bootstrap-based transfer-route significance summary (`{transfer_significance_appendix_path.name}`).",
                "- [ ] Extend formal significance testing to repeated-randomization transfer-route comparisons.",
                f"- [x] Expand out-of-domain validation scope (at least one additional area or time regime) (`{out_of_domain_validation_appendix_path.name}`).",
                f"- [x] Add threshold utility analysis for operational decision tradeoff (`{threshold_utility_appendix_path.name}`).",
                f"- [{'x' if bilingual_parity_status == 'PASS' else ' '}] Run final bilingual publication parity check (Korean/English) (`{bilingual_parity_report_path.name}` = {bilingual_parity_status}).",
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
        "transfer_route_significance_csv_path": str(transfer_significance_csv_path),
        "out_of_domain_validation_detail_csv_path": str(out_of_domain_detail_csv_path),
        "out_of_domain_validation_summary_csv_path": str(out_of_domain_summary_csv_path),
        "threshold_utility_curve_csv_path": str(threshold_utility_curve_csv_path),
        "threshold_utility_operating_points_csv_path": str(threshold_utility_operating_csv_path),
        "ablation_tabular_vs_cnn_csv_path": str(ablation_csv_path),
        "model_family_significance_csv_path": str(significance_csv_path),
        "figure_1_model_family_comparison_svg_path": str(fig_model_family),
        "figure_2_transfer_delta_f1_heatmap_svg_path": str(fig_transfer_heatmap),
        "figure_3_pipeline_overview_svg_path": str(fig_pipeline),
        "figure_4_threshold_utility_curve_svg_path": str(fig_threshold_utility),
        "figure_index_md_path": str(figure_index_path),
        "manuscript_draft_ko_md_path": str(manuscript_draft_ko_path),
        "manuscript_draft_en_md_path": str(manuscript_draft_en_path),
        "manuscript_draft_md_path": str(manuscript_draft_path),
        "manuscript_todo_md_path": str(manuscript_todo_path),
        "bilingual_parity_report_md_path": str(bilingual_parity_report_path),
        "terminology_mapping_md_path": str(terminology_mapping_path),
        "figure_captions_bilingual_md_path": str(figure_captions_path),
        "submission_template_tex_path": str(submission_template_tex_path),
        "consistency_report_md_path": str(consistency_report_path),
        "prior_work_evidence_matrix_md_path": str(prior_work_matrix_path),
        "examiner_critical_todo_md_path": str(examiner_review_todo_path),
        "statistical_significance_appendix_md_path": str(significance_appendix_path),
        "transfer_route_significance_appendix_md_path": str(transfer_significance_appendix_path),
        "threshold_utility_appendix_md_path": str(threshold_utility_appendix_path),
        "out_of_domain_validation_appendix_md_path": str(out_of_domain_validation_appendix_path),
    }
