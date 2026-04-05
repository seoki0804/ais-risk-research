#!/usr/bin/env python3
"""Summarize NOLA cleaned-input control against raw pooled baseline."""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path


ROOT = Path("/Users/seoki/Desktop/research")
BASE_POOLED_DIR = Path(
    os.environ.get(
        "BASE_POOLED_DIR",
        str(ROOT / "outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix"),
    )
)
CLEAN_DIR = Path(
    os.environ.get(
        "CLEAN_DIR",
        str(ROOT / "outputs/2026-03-19_nola_cleaned_input_control_leakfix"),
    )
)
PAIRWISE_RAW = BASE_POOLED_DIR / "nola_pooled_pairwise.csv"
PAIRWISE_CLEAN = CLEAN_DIR / "nola_pooled_observed_pair.csv"
HGBT_RAW = BASE_POOLED_DIR / "nola_pooled_own_ship_test_predictions.csv"
HGBT_RAW_SUMMARY = BASE_POOLED_DIR / "nola_pooled_own_ship_summary.json"
HGBT_CLEAN = CLEAN_DIR / "nola_pooled_observed_pair_hgbt_test_predictions.csv"
HGBT_CLEAN_SUMMARY = CLEAN_DIR / "nola_pooled_observed_pair_hgbt_summary.json"
CNN_CLEAN = CLEAN_DIR / "nola_pooled_observed_pair_cnn_weighted_predictions.csv"
CNN_CLEAN_SUMMARY = CLEAN_DIR / "nola_pooled_observed_pair_cnn_weighted_summary.json"
FILTER_SUMMARY = CLEAN_DIR / "nola_pooled_observed_pair_filter_summary.json"
OUT_DIR = ROOT / "outputs/presentation_deck_outline_61day_2026-03-13"
OUT_MD = OUT_DIR / "nola_cleaned_input_control_note_61day.md"
OUT_CSV = OUT_DIR / "nola_cleaned_input_control_summary_61day.csv"


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


def evaluate(pairwise_path: Path, pred_path: Path, pred_field: str) -> dict[str, object]:
    pairwise_rows = list(csv.DictReader(pairwise_path.open()))
    preds = {
        (row["timestamp"], row["own_mmsi"], row["target_mmsi"]): row
        for row in csv.DictReader(pred_path.open())
    }
    confusion = Counter()
    fp_type = Counter()
    fp_date = Counter()
    for row in pairwise_rows:
        key = (row["timestamp"], row["own_mmsi"], row["target_mmsi"])
        if key not in preds:
            continue
        pred = int(preds[key][pred_field])
        truth = int(row["label_future_conflict"])
        label = classify(truth, pred)
        confusion[label] += 1
        if label == "FP":
            fp_type[row["target_vessel_type"]] += 1
            fp_date[row["source_date"]] += 1
    return {
        "confusion": confusion,
        "fp_type": fp_type,
        "fp_date": fp_date,
    }


def main() -> None:
    filter_summary = json.loads(FILTER_SUMMARY.read_text())
    hgbt_raw_summary = json.loads(HGBT_RAW_SUMMARY.read_text())
    hgbt_clean_summary = json.loads(HGBT_CLEAN_SUMMARY.read_text())
    cnn_clean_summary = json.loads(CNN_CLEAN_SUMMARY.read_text())

    hgbt_raw = evaluate(PAIRWISE_RAW, HGBT_RAW, "hgbt_pred")
    hgbt_clean = evaluate(PAIRWISE_CLEAN, HGBT_CLEAN, "hgbt_pred")
    cnn_clean = evaluate(PAIRWISE_CLEAN, CNN_CLEAN, "cnn_pred")

    rows = [
        {
            "model": "hgbt_raw",
            "f1": f"{float(hgbt_raw_summary['models']['hgbt']['f1']):.4f}",
            "positive_rate_predicted": f"{float(hgbt_raw_summary['models']['hgbt']['positive_rate_predicted']):.4f}",
            "fp_count": str(hgbt_raw["confusion"]["FP"]),
            "passenger_tug_fp_share": pct(hgbt_raw["fp_type"]["passenger"] + hgbt_raw["fp_type"]["tug"], hgbt_raw["confusion"]["FP"]),
            "aug0808_fp_share": pct(hgbt_raw["fp_date"]["2023-08-08"], hgbt_raw["confusion"]["FP"]),
        },
        {
            "model": "hgbt_cleaned",
            "f1": f"{float(hgbt_clean_summary['models']['hgbt']['f1']):.4f}",
            "positive_rate_predicted": f"{float(hgbt_clean_summary['models']['hgbt']['positive_rate_predicted']):.4f}",
            "fp_count": str(hgbt_clean["confusion"]["FP"]),
            "passenger_tug_fp_share": pct(hgbt_clean["fp_type"]["passenger"] + hgbt_clean["fp_type"]["tug"], hgbt_clean["confusion"]["FP"]),
            "aug0808_fp_share": pct(hgbt_clean["fp_date"]["2023-08-08"], hgbt_clean["confusion"]["FP"]),
        },
        {
            "model": "cnn_cleaned_weighted",
            "f1": f"{float(cnn_clean_summary['metrics']['f1']):.4f}",
            "positive_rate_predicted": f"{float(cnn_clean_summary['metrics']['positive_rate_predicted']):.4f}",
            "fp_count": str(cnn_clean["confusion"]["FP"]),
            "passenger_tug_fp_share": pct(cnn_clean["fp_type"]["passenger"] + cnn_clean["fp_type"]["tug"], cnn_clean["confusion"]["FP"]),
            "aug0808_fp_share": pct(cnn_clean["fp_date"]["2023-08-08"], cnn_clean["confusion"]["FP"]),
        },
    ]

    with OUT_CSV.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=["model", "f1", "positive_rate_predicted", "fp_count", "passenger_tug_fp_share", "aug0808_fp_share"])
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# 문서명",
        "NOLA Cleaned-Input Control Note 61day",
        "",
        "# 문서 목적",
        "NOLA pooled residual difficulty가 interpolation-heavy input 때문에 과장된 것인지, observed-pair only cleaned-input control로 점검한다.",
        "",
        "# 작성 버전",
        "v1.2 (2026-03-19, leak-fix rerun synced)",
        "",
        "## 1. cleaned-input 정의",
        "",
        "- [확정] current cleaned-input control은 `own_is_interpolated=0` and `target_is_interpolated=0` observed-pair only subset이다.",
        f"- [확정] rows: `{filter_summary['input_row_count']} -> {filter_summary['output_row_count']}`",
        f"- [확정] positive rate: `{filter_summary['input_positive_rate']:.4f} -> {filter_summary['output_positive_rate']:.4f}`",
        f"- [확정] own ship count는 `5`로 유지된다.",
        "",
        "## 2. comparator summary",
        "",
        "| Model | F1 | Predicted positive rate | FP count | Passenger+Tug FP share | 2023-08-08 FP share |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['model']}` | {row['f1']} | {row['positive_rate_predicted']} | {row['fp_count']} | {row['passenger_tug_fp_share']} | {row['aug0808_fp_share']} |"
        )
    lines.extend(
        [
            "",
            "## 3. reviewer-safe 해석",
            "",
            f"- [확정] observed-pair cleaned-input control에서 `hgbt`는 `FP {rows[0]['fp_count']} -> {rows[1]['fp_count']}`, `2023-08-08 FP share {rows[0]['aug0808_fp_share']} -> {rows[1]['aug0808_fp_share']}`로 false-positive burden을 크게 줄였지만, own-ship `F1`은 `{rows[0]['f1']} -> {rows[1]['f1']}`로 소폭 내려갔다.",
            "- [확정] 따라서 current NOLA residual difficulty에는 interpolation-heavy rows가 실질적으로 기여하지만, strict observed-pair filter 자체를 net performance fix로 읽으면 과장이다.",
            "- [확정] cleaned-input 이후에도 passenger/tug 중심 error가 완전히 사라진 것은 아니므로, difficulty를 data cleaning alone으로 모두 해결했다고 읽으면 과장이다.",
            f"- [확정] 같은 cleaned subset에서 CNN weighted comparator는 `predicted positive rate = {rows[2]['positive_rate_predicted']}`, `F1 = {rows[2]['f1']}`으로 all-positive collapse를 보였다. 즉, cleaned-input이 current learned regional baseline을 자동으로 안정화해 주지는 않는다.",
            "",
            "## 4. 산출물",
            "",
            f"- CSV: [{OUT_CSV.name}]({OUT_CSV})",
        ]
    )
    OUT_MD.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
