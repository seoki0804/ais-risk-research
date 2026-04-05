#!/usr/bin/env python3
"""Compare pooled NOLA hgbt vs regional raster CNN variants."""

from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path("/Users/seoki/Desktop/research")
BASE_POOLED_DIR = Path(
    os.environ.get(
        "BASE_POOLED_DIR",
        str(ROOT / "outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix"),
    )
)
PAIRWISE = BASE_POOLED_DIR / "nola_pooled_pairwise.csv"
HGBT_PRED = BASE_POOLED_DIR / "nola_pooled_own_ship_test_predictions.csv"
HGBT_SUMMARY = BASE_POOLED_DIR / "nola_pooled_own_ship_summary.json"
CNN_DIR = Path(
    os.environ.get(
        "CNN_DIR",
        str(ROOT / "outputs/2026-03-19_regional_raster_cnn_nola_pooled_leakfix"),
    )
)
VARIANTS = {
    "hgbt": {
        "predictions": HGBT_PRED,
        "summary": HGBT_SUMMARY,
        "score_field": "hgbt_score",
        "pred_field": "hgbt_pred",
    },
    "cnn_weighted": {
        "predictions": CNN_DIR / "nola_regional_raster_cnn_pooled_weighted_bce_predictions.csv",
        "summary": CNN_DIR / "nola_regional_raster_cnn_pooled_weighted_bce_summary.json",
        "score_field": "cnn_score",
        "pred_field": "cnn_pred",
    },
    "cnn_focal": {
        "predictions": CNN_DIR / "nola_regional_raster_cnn_pooled_focal_predictions.csv",
        "summary": CNN_DIR / "nola_regional_raster_cnn_pooled_focal_summary.json",
        "score_field": "cnn_score",
        "pred_field": "cnn_pred",
    },
}
OUT_DIR = ROOT / "outputs/presentation_deck_outline_61day_2026-03-13"
OUT_MD = OUT_DIR / "regional_raster_cnn_nola_pooled_compare_note_61day.md"
OUT_CSV = OUT_DIR / "regional_raster_cnn_nola_pooled_compare_summary_61day.csv"


def classify(y: int, pred: int) -> str:
    if y == 1 and pred == 1:
        return "TP"
    if y == 1 and pred == 0:
        return "FN"
    if y == 0 and pred == 1:
        return "FP"
    return "TN"


def pct(num: int, den: int) -> str:
    if den == 0:
        return "0.0%"
    return f"{100.0 * num / den:.1f}%"


def load_pairwise() -> list[dict[str, str]]:
    return list(csv.DictReader(PAIRWISE.open()))


def load_predictions(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    return {
        (row["timestamp"], row["own_mmsi"], row["target_mmsi"]): row
        for row in csv.DictReader(path.open())
    }


def main() -> None:
    pairwise_rows = load_pairwise()
    outputs: list[dict[str, str]] = []
    notes: dict[str, dict[str, object]] = {}

    for model_name, config in VARIANTS.items():
        preds = load_predictions(config["predictions"])
        summary = json.loads(config["summary"].read_text())
        metrics = summary["models"]["hgbt"] if model_name == "hgbt" else summary["metrics"]
        confusion = Counter()
        fp_type = Counter()
        fn_type = Counter()
        fp_date = Counter()
        for row in pairwise_rows:
            key = (row["timestamp"], row["own_mmsi"], row["target_mmsi"])
            if key not in preds:
                continue
            pred = int(preds[key][config["pred_field"]])
            truth = int(row["label_future_conflict"])
            label = classify(truth, pred)
            confusion[label] += 1
            if label == "FP":
                fp_type[row["target_vessel_type"]] += 1
                fp_date[row["source_date"]] += 1
            elif label == "FN":
                fn_type[row["target_vessel_type"]] += 1

        total_fp = confusion["FP"]
        outputs.append(
            {
                "model": model_name,
                "f1": f"{float(metrics['f1']):.4f}",
                "auroc": f"{float(metrics['auroc']):.4f}",
                "auprc": f"{float(metrics['auprc']):.4f}",
                "precision": f"{float(metrics['precision']):.4f}",
                "recall": f"{float(metrics['recall']):.4f}",
                "positive_rate_predicted": f"{float(metrics['positive_rate_predicted']):.4f}",
                "threshold": f"{float(metrics['threshold']):.2f}",
                "fp_count": str(confusion["FP"]),
                "fn_count": str(confusion["FN"]),
                "passenger_tug_fp_share": pct(fp_type["passenger"] + fp_type["tug"], total_fp),
                "aug0808_fp_share": pct(fp_date["2023-08-08"], total_fp),
                "tanker_fn_share": pct(fn_type["tanker"], confusion["FN"]),
            }
        )
        notes[model_name] = {
            "confusion": confusion,
            "fp_type": fp_type,
            "fn_type": fn_type,
            "fp_date": fp_date,
        }

    with OUT_CSV.open("w", newline="") as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=[
                "model",
                "f1",
                "auroc",
                "auprc",
                "precision",
                "recall",
                "positive_rate_predicted",
                "threshold",
                "fp_count",
                "fn_count",
                "passenger_tug_fp_share",
                "aug0808_fp_share",
                "tanker_fn_share",
            ],
        )
        writer.writeheader()
        writer.writerows(outputs)

    lines = [
        "# 문서명",
        "Regional Raster CNN NOLA Pooled Compare Note 61day",
        "",
        "# 문서 목적",
        "same-area pooled NOLA split에서 regional raster CNN comparator가 hgbt보다 residual difficulty를 더 잘 설명하거나 줄이는지 비교한다.",
        "",
        "# 작성 버전",
        "v1.1 (2026-03-19, leak-fix rerun synced)",
        "",
        "## 1. 핵심 결과",
        "",
        "| Model | F1 | AUROC | AUPRC | Precision | Recall | Predicted positive rate | Threshold | FP | FN | Passenger+Tug FP share | 2023-08-08 FP share | Tanker FN share |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in outputs:
        lines.append(
            f"| `{row['model']}` | {row['f1']} | {row['auroc']} | {row['auprc']} | {row['precision']} | {row['recall']} | "
            f"{row['positive_rate_predicted']} | {row['threshold']} | {row['fp_count']} | {row['fn_count']} | "
            f"{row['passenger_tug_fp_share']} | {row['aug0808_fp_share']} | {row['tanker_fn_share']} |"
        )

    lines.extend(
        [
            "",
            "## 2. Fast Reading",
            "",
            "- [확정] pooled NOLA에서는 `hgbt`가 CNN 두 변형보다 명확히 더 강했다.",
            f"- [확정] `weighted_bce`가 CNN 두 변형 중 더 낫지만, `F1 {outputs[1]['f1']}`로 `hgbt {outputs[0]['f1']}`보다 한참 낮다.",
            f"- [확정] CNN은 recall을 유지했지만 FP를 크게 늘렸다. `hgbt FP={outputs[0]['fp_count']}`, `cnn_weighted FP={outputs[1]['fp_count']}`, `cnn_focal FP={outputs[2]['fp_count']}`였다.",
            "- [확정] CNN의 추가 FP도 대부분 `passenger/tug`와 `2023-08-08` cluster에 집중돼, NOLA residual difficulty의 핵심 pathology를 줄이지 못했다.",
            "",
            "## 3. reviewer-safe 결론",
            "",
            "- current pooled NOLA split에서는 regional raster CNN comparator가 tabular hgbt를 대체하지 못한다.",
            "- CNN은 focal-target-centered regional representation을 학습할 수는 있지만, NOLA pooled case에서는 passenger/tug diverging false-positive cluster를 줄이지 못하고 오히려 증폭했다.",
            "- reviewer-safe reading은 `the learned regional baseline is viable but still area-dependent, and it does not resolve the current NOLA residual-difficulty pattern.`",
            "",
            "## 4. 산출물",
            "",
            f"- CSV: [{OUT_CSV.name}]({OUT_CSV})",
        ]
    )
    OUT_MD.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
