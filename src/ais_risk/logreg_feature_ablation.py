from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from .benchmark import (
    _build_metrics,
    _choose_threshold,
    _partition_rows_for_benchmark,
    _top_logistic_coefficients,
    load_pairwise_dataset_rows,
)


def _feature_dict_with_drops(
    row: dict[str, str],
    dropped_fields: set[str] | None = None,
) -> dict[str, float | str]:
    dropped = dropped_fields or set()
    payload: dict[str, float | str] = {
        "distance_nm": float(row["distance_nm"]),
        "dcpa_nm": float(row["dcpa_nm"]),
        "tcpa_min": float(row["tcpa_min"]),
        "relative_speed_knots": float(row["relative_speed_knots"]),
        "relative_bearing_deg": float(row["relative_bearing_deg"]),
        "bearing_abs_deg": float(row["bearing_abs_deg"]),
        "course_difference_deg": float(row["course_difference_deg"]),
        "local_target_count": float(row["local_target_count"]),
        "rule_score": float(row["rule_score"]),
        "rule_component_distance": float(row["rule_component_distance"]),
        "rule_component_dcpa": float(row["rule_component_dcpa"]),
        "rule_component_tcpa": float(row["rule_component_tcpa"]),
        "rule_component_bearing": float(row["rule_component_bearing"]),
        "rule_component_relspeed": float(row["rule_component_relspeed"]),
        "rule_component_encounter": float(row["rule_component_encounter"]),
        "rule_component_density": float(row["rule_component_density"]),
    }
    if "encounter_type" not in dropped:
        payload["encounter_type"] = row["encounter_type"] or "unknown"
    if "own_vessel_type" not in dropped:
        payload["own_vessel_type"] = row["own_vessel_type"] or "unknown"
    if "target_vessel_type" not in dropped:
        payload["target_vessel_type"] = row["target_vessel_type"] or "unknown"
    if "pair_interp_flag" not in dropped:
        payload["pair_interp_flag"] = f"{row['own_is_interpolated']}_{row['target_is_interpolated']}"
    return payload


def _vectorize_rows_with_drops(
    rows: list[dict[str, str]],
    dropped_fields: set[str],
    vectorizer: DictVectorizer | None = None,
):
    features = [_feature_dict_with_drops(row, dropped_fields=dropped_fields) for row in rows]
    if vectorizer is None:
        vectorizer = DictVectorizer(sparse=False)
        matrix = vectorizer.fit_transform(features)
    else:
        matrix = vectorizer.transform(features)
    labels = np.array([int(row["label_future_conflict"]) for row in rows], dtype=int)
    return matrix.astype(np.float32), labels, vectorizer


def _positive_recall_by_target_vessel_type(
    rows: list[dict[str, str]],
    predictions: np.ndarray,
) -> list[dict[str, float | int | str]]:
    totals: dict[str, int] = {}
    hits: dict[str, int] = {}
    for row, pred in zip(rows, predictions):
        if int(row["label_future_conflict"]) != 1:
            continue
        vessel_type = row["target_vessel_type"] or "unknown"
        totals[vessel_type] = totals.get(vessel_type, 0) + 1
        hits[vessel_type] = hits.get(vessel_type, 0) + int(pred)
    items: list[dict[str, float | int | str]] = []
    for vessel_type in sorted(totals):
        count = totals[vessel_type]
        recall = float(hits.get(vessel_type, 0) / count) if count else 0.0
        items.append(
            {
                "target_vessel_type": vessel_type,
                "positive_count": int(count),
                "recall": recall,
            }
        )
    items.sort(key=lambda item: (-int(item["positive_count"]), str(item["target_vessel_type"])))
    return items


def _variant_record(
    name: str,
    dropped_fields: set[str],
    train_rows: list[dict[str, str]],
    val_rows: list[dict[str, str]],
    test_rows: list[dict[str, str]],
    random_seed: int | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    x_train, y_train, vectorizer = _vectorize_rows_with_drops(train_rows, dropped_fields=dropped_fields)
    x_val, y_val, _ = _vectorize_rows_with_drops(val_rows, dropped_fields=dropped_fields, vectorizer=vectorizer)
    x_test, y_test, _ = _vectorize_rows_with_drops(test_rows, dropped_fields=dropped_fields, vectorizer=vectorizer)

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_val_scaled = scaler.transform(x_val)
    x_test_scaled = scaler.transform(x_test)

    model = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=None if random_seed is None else int(random_seed),
    )
    model.fit(x_train_scaled, y_train)
    val_scores = model.predict_proba(x_val_scaled)[:, 1]
    test_scores = model.predict_proba(x_test_scaled)[:, 1]
    threshold = _choose_threshold(y_val, val_scores)
    metrics = _build_metrics(y_test, test_scores, threshold)
    predictions = (test_scores >= threshold).astype(int)
    metrics["elapsed_seconds"] = float(time.perf_counter() - started)
    metrics["top_positive_features"] = _top_logistic_coefficients(model, vectorizer.feature_names_)
    return {
        "variant_name": name,
        "dropped_fields": sorted(dropped_fields),
        "feature_count": len(vectorizer.feature_names_),
        "metrics": metrics,
        "positive_recall_by_target_vessel_type": _positive_recall_by_target_vessel_type(test_rows, predictions),
    }


def build_logreg_feature_ablation_summary_markdown(summary: dict[str, Any]) -> str:
    def _fmt_metric(value: Any, digits: int = 4) -> str:
        if value is None:
            return "-"
        return f"{float(value):.{digits}f}"

    lines = [
        "# Logreg Feature Ablation Summary",
        "",
        f"- input_path: `{summary['input_path']}`",
        f"- split_strategy: `{summary['split_strategy']}`",
        f"- train_rows: `{summary['split']['train_rows']}`",
        f"- val_rows: `{summary['split']['val_rows']}`",
        f"- test_rows: `{summary['split']['test_rows']}`",
        f"- row_count: `{summary['row_count']}`",
        f"- own_ship_count: `{summary['own_ship_count']}`",
        f"- random_seed: `{summary['random_seed']}`",
        "",
        "## Variants",
        "",
        "| variant | dropped_fields | feature_count | f1 | precision | recall | auroc | auprc | threshold |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    baseline_f1 = None
    for item in summary["variants"]:
        metrics = item["metrics"]
        if item["variant_name"] == "baseline":
            baseline_f1 = float(metrics["f1"])
        lines.append(
            "| "
            + f"{item['variant_name']} | "
            + f"{', '.join(item['dropped_fields']) or '-'} | "
            + f"{item['feature_count']} | "
            + f"{_fmt_metric(metrics['f1'])} | "
            + f"{_fmt_metric(metrics['precision'])} | "
            + f"{_fmt_metric(metrics['recall'])} | "
            + f"{_fmt_metric(metrics['auroc'])} | "
            + f"{_fmt_metric(metrics['auprc'])} | "
            + f"{_fmt_metric(metrics['threshold'], digits=2)} |"
        )
    if baseline_f1 is not None:
        lines.extend(["", "## Delta vs baseline", ""])
        lines.append("| variant | delta_f1 |")
        lines.append("|---|---:|")
        for item in summary["variants"]:
            metrics = item["metrics"]
            delta = float(metrics["f1"]) - baseline_f1
            lines.append(f"| {item['variant_name']} | {delta:+.4f} |")
    lines.extend(["", "## Test Positive Recall by Target Vessel Type", ""])
    for item in summary["variants"]:
        lines.append(f"### {item['variant_name']}")
        lines.append("")
        lines.append("| target_vessel_type | positive_count | recall |")
        lines.append("|---|---:|---:|")
        for recall_item in item["positive_recall_by_target_vessel_type"]:
            lines.append(
                f"| {recall_item['target_vessel_type']} | {int(recall_item['positive_count'])} | {float(recall_item['recall']):.4f} |"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def run_logreg_feature_ablation(
    input_path: str | Path,
    output_prefix: str | Path,
    variants: list[tuple[str, set[str]]] | None = None,
    split_strategy: str = "own_ship",
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    random_seed: int | None = 42,
) -> dict[str, Any]:
    rows = load_pairwise_dataset_rows(input_path)
    train_rows, val_rows, test_rows, split_summary = _partition_rows_for_benchmark(
        rows=rows,
        split_strategy=split_strategy,
        train_fraction=float(train_fraction),
        val_fraction=float(val_fraction),
    )
    requested_variants = variants or [("baseline", set())]
    variant_results = [
        _variant_record(
            name=name,
            dropped_fields=dropped_fields,
            train_rows=train_rows,
            val_rows=val_rows,
            test_rows=test_rows,
            random_seed=random_seed,
        )
        for name, dropped_fields in requested_variants
    ]

    output_prefix_path = Path(output_prefix)
    summary = {
        "input_path": str(input_path),
        "output_prefix": str(output_prefix_path),
        "row_count": len(rows),
        "own_ship_count": len({row["own_mmsi"] for row in rows}),
        "split_strategy": split_strategy,
        "split": split_summary,
        "random_seed": random_seed,
        "variants": variant_results,
    }
    summary_json_path = output_prefix_path.with_name(output_prefix_path.name + "_summary.json")
    summary_md_path = output_prefix_path.with_name(output_prefix_path.name + "_summary.md")
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_logreg_feature_ablation_summary_markdown(summary), encoding="utf-8")
    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_md_path"] = str(summary_md_path)
    return summary
