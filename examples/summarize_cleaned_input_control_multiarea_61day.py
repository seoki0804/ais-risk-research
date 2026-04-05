#!/usr/bin/env python3
"""Summarize observed-pair cleaned-input controls across Houston, Seattle, and NOLA."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path("/Users/seoki/Desktop/research")
OUT_DIR = ROOT / "outputs" / "presentation_deck_outline_61day_2026-03-13"
BASE_POOLED_DIR = Path(
    os.environ.get(
        "BASE_POOLED_DIR",
        str(ROOT / "outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix"),
    )
)
HOU_CLEAN_DIR = Path(
    os.environ.get(
        "HOU_CLEAN_DIR",
        str(ROOT / "outputs/2026-03-19_houston_cleaned_input_control_leakfix"),
    )
)
SEA_CLEAN_DIR = Path(
    os.environ.get(
        "SEA_CLEAN_DIR",
        str(ROOT / "outputs/2026-03-19_seattle_cleaned_input_control_leakfix"),
    )
)
NOLA_CLEAN_DIR = Path(
    os.environ.get(
        "NOLA_CLEAN_DIR",
        str(ROOT / "outputs/2026-03-19_nola_cleaned_input_control_leakfix"),
    )
)


@dataclass
class EvalSpec:
    area: str
    raw_eval: str
    cleaned_eval: str
    raw_summary: Path
    raw_predictions: Path
    cleaned_summary: Path
    cleaned_predictions: Path
    filter_summary: Path


AREAS = [
    EvalSpec(
        area="Houston",
        raw_eval="timestamp",
        cleaned_eval="timestamp",
        raw_summary=BASE_POOLED_DIR / "houston_pooled_timestamp_summary.json",
        raw_predictions=BASE_POOLED_DIR / "houston_pooled_timestamp_test_predictions.csv",
        cleaned_summary=HOU_CLEAN_DIR / "houston_pooled_observed_pair_timestamp_summary.json",
        cleaned_predictions=HOU_CLEAN_DIR / "houston_pooled_observed_pair_timestamp_test_predictions.csv",
        filter_summary=HOU_CLEAN_DIR / "houston_pooled_observed_pair_filter_summary.json",
    ),
    EvalSpec(
        area="Seattle",
        raw_eval="own_ship",
        cleaned_eval="own_ship",
        raw_summary=BASE_POOLED_DIR / "seattle_pooled_own_ship_summary.json",
        raw_predictions=BASE_POOLED_DIR / "seattle_pooled_own_ship_test_predictions.csv",
        cleaned_summary=SEA_CLEAN_DIR / "seattle_pooled_observed_pair_hgbt_summary.json",
        cleaned_predictions=SEA_CLEAN_DIR / "seattle_pooled_observed_pair_hgbt_test_predictions.csv",
        filter_summary=SEA_CLEAN_DIR / "seattle_pooled_observed_pair_filter_summary.json",
    ),
    EvalSpec(
        area="NOLA",
        raw_eval="own_ship",
        cleaned_eval="own_ship",
        raw_summary=BASE_POOLED_DIR / "nola_pooled_own_ship_summary.json",
        raw_predictions=BASE_POOLED_DIR / "nola_pooled_own_ship_test_predictions.csv",
        cleaned_summary=NOLA_CLEAN_DIR / "nola_pooled_observed_pair_hgbt_summary.json",
        cleaned_predictions=NOLA_CLEAN_DIR / "nola_pooled_observed_pair_hgbt_test_predictions.csv",
        filter_summary=NOLA_CLEAN_DIR / "nola_pooled_observed_pair_filter_summary.json",
    ),
]


CNN_SPECS = [
    {
        "area": "Houston",
        "eval": "timestamp",
        "summary": HOU_CLEAN_DIR / "houston_pooled_observed_pair_timestamp_cnn_weighted_summary.json",
        "predictions": HOU_CLEAN_DIR / "houston_pooled_observed_pair_timestamp_cnn_weighted_predictions.csv",
        "score_key": "cnn_pred",
    },
    {
        "area": "Seattle",
        "eval": "own_ship",
        "summary": SEA_CLEAN_DIR / "seattle_pooled_observed_pair_cnn_weighted_summary.json",
        "predictions": SEA_CLEAN_DIR / "seattle_pooled_observed_pair_cnn_weighted_predictions.csv",
        "score_key": "cnn_pred",
    },
    {
        "area": "NOLA",
        "eval": "own_ship",
        "summary": NOLA_CLEAN_DIR / "nola_pooled_observed_pair_cnn_weighted_summary.json",
        "predictions": NOLA_CLEAN_DIR / "nola_pooled_observed_pair_cnn_weighted_predictions.csv",
        "score_key": "cnn_pred",
    },
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def confusion_from_predictions(path: Path, pred_col: str) -> dict[str, int]:
    df = pd.read_csv(path)
    label = df["label_future_conflict"].astype(int)
    pred = df[pred_col].astype(int)
    tp = int(((label == 1) & (pred == 1)).sum())
    fp = int(((label == 0) & (pred == 1)).sum())
    tn = int(((label == 0) & (pred == 0)).sum())
    fn = int(((label == 1) & (pred == 0)).sum())
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def area_reading(area: str) -> str:
    if area == "Houston":
        return (
            "Strict observed-pair cleaning is not universally beneficial: it over-prunes support in Houston. "
            "The holdout own-ship split becomes degenerate, and even the timestamp fallback drops sharply."
        )
    if area == "Seattle":
        return (
            "Seattle improves under the same strict cleaned-input control, which supports a real input-quality effect "
            "when support remains adequate."
        )
    return (
        "NOLA improves even more strongly under the same cleaned-input control, especially through a large false-positive "
        "reduction, which confirms that interpolation-heavy rows materially contribute to the current residual difficulty."
    )


def cnn_reading() -> str:
    return (
        "Across Houston, Seattle, and NOLA, the current weighted CNN does not stabilize on cleaned subsets. "
        "It remains in or moves into an all-positive regime, so cleaned input alone is not a fix for the current learned regional baseline."
    )


def main() -> None:
    rows: list[dict[str, object]] = []
    for spec in AREAS:
        raw_summary = load_json(spec.raw_summary)
        cleaned_summary = load_json(spec.cleaned_summary)
        filt = load_json(spec.filter_summary)
        raw_hgbt = raw_summary["models"]["hgbt"]
        cleaned_hgbt = cleaned_summary["models"]["hgbt"]
        raw_conf = confusion_from_predictions(spec.raw_predictions, "hgbt_pred")
        cleaned_conf = confusion_from_predictions(spec.cleaned_predictions, "hgbt_pred")
        rows.append(
            {
                "area": spec.area,
                "raw_eval": spec.raw_eval,
                "cleaned_eval": spec.cleaned_eval,
                "rows_before": filt["input_row_count"],
                "rows_after": filt["output_row_count"],
                "retention_ratio": filt["output_row_count"] / filt["input_row_count"],
                "positive_rate_before": filt["input_positive_rate"],
                "positive_rate_after": filt["output_positive_rate"],
                "raw_f1": raw_hgbt["f1"],
                "cleaned_f1": cleaned_hgbt["f1"],
                "delta_f1": cleaned_hgbt["f1"] - raw_hgbt["f1"],
                "raw_predicted_positive_rate": raw_hgbt["positive_rate_predicted"],
                "cleaned_predicted_positive_rate": cleaned_hgbt["positive_rate_predicted"],
                "raw_tp": raw_conf["tp"],
                "raw_fp": raw_conf["fp"],
                "raw_tn": raw_conf["tn"],
                "raw_fn": raw_conf["fn"],
                "cleaned_tp": cleaned_conf["tp"],
                "cleaned_fp": cleaned_conf["fp"],
                "cleaned_tn": cleaned_conf["tn"],
                "cleaned_fn": cleaned_conf["fn"],
                "reading": area_reading(spec.area),
            }
        )

    cnn_rows: list[dict[str, object]] = []
    for spec in CNN_SPECS:
        summary = load_json(spec["summary"])
        conf = confusion_from_predictions(spec["predictions"], spec["score_key"])
        metrics = summary["metrics"]
        cnn_rows.append(
            {
                "area": spec["area"],
                "eval": spec["eval"],
                "f1": metrics["f1"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "predicted_positive_rate": metrics["positive_rate_predicted"],
                "tp": conf["tp"],
                "fp": conf["fp"],
                "tn": conf["tn"],
                "fn": conf["fn"],
            }
        )

    csv_path = OUT_DIR / "cleaned_input_control_multiarea_summary_61day.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    cnn_csv_path = OUT_DIR / "cleaned_input_control_multiarea_cnn_summary_61day.csv"
    with cnn_csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(cnn_rows[0].keys()))
        writer.writeheader()
        writer.writerows(cnn_rows)

    table_lines = [
        "| Area | Raw eval | Raw hgbt F1 | Cleaned eval | Cleaned hgbt F1 | Delta | Rows before -> after | Raw FP -> cleaned FP |",
        "|---|---|---:|---|---:|---:|---|---:|",
    ]
    for row in rows:
        table_lines.append(
            "| {area} | `{raw_eval}` | {raw_f1:.4f} | `{cleaned_eval}` | {cleaned_f1:.4f} | {delta_f1:+.4f} | `{rows_before} -> {rows_after}` | `{raw_fp} -> {cleaned_fp}` |".format(
                **row
            )
        )

    cnn_lines = [
        "| Area | Eval | Cleaned CNN F1 | Precision | Recall | Predicted positive rate | FP |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in cnn_rows:
        cnn_lines.append(
            "| {area} | `{eval}` | {f1:.4f} | {precision:.4f} | {recall:.4f} | {predicted_positive_rate:.4f} | {fp} |".format(
                **row
            )
        )

    note = f"""# 문서명
Cleaned-Input Control Multiarea Note 61day

# 문서 목적
Observed-pair cleaned-input control을 Houston, Seattle, NOLA에 함께 적용했을 때 input-quality dependence가 보편적인 개선인지, 아니면 support-sensitive phenomenon인지 정리한다.

# 작성 버전
v1.2 (2026-03-19, leak-fix rerun synced)

## 1. 핵심 결론

- [확정] strict observed-pair cleaned-input control은 `Seattle`과 `NOLA`에서 false-positive burden을 줄였지만, leak-fix rerun 기준 tabular `hgbt` F1을 개선하지는 못했다.
- [확정] `Houston`에서는 support를 과도하게 줄여 strict own-ship split을 degenerate하게 만들었고, timestamp fallback도 크게 약화됐다.
- [확정] 따라서 cleaned input은 universal improvement가 아니라 `region- and support-sensitive control`로 읽는 편이 정확하다.
- [확정] current weighted regional CNN comparator는 cleaned subset들에서 안정화되지 않았고, 세 해역 모두에서 all-positive 또는 near-all-positive regime에 머물렀다.

## 2. tabular hgbt multiarea summary

{chr(10).join(table_lines)}

## 3. current learned regional baseline on cleaned subsets

{chr(10).join(cnn_lines)}

## 4. reviewer-safe reading

- [확정] `Seattle`: same strict filter에서 `hgbt F1 {rows[1]['raw_f1']:.4f} -> {rows[1]['cleaned_f1']:.4f}`로 소폭 내려가지만, `FP {rows[1]['raw_fp']} -> {rows[1]['cleaned_fp']}`이므로 interpolation-heavy rows가 error structure에는 실질적으로 기여한다.
- [확정] `NOLA`: `hgbt F1 {rows[2]['raw_f1']:.4f} -> {rows[2]['cleaned_f1']:.4f}`로 소폭 내려가지만, `FP {rows[2]['raw_fp']} -> {rows[2]['cleaned_fp']}`이므로 interpolation-heavy rows가 current residual-difficulty pattern에 materially contribute한다.
- [확정] `Houston`: same strict filter가 holdout own ship의 유일한 positive를 제거해 strict own-ship split을 degenerate하게 만들었고, timestamp fallback도 `{rows[0]['raw_f1']:.4f} -> {rows[0]['cleaned_f1']:.4f}`으로 떨어졌다. Houston에서는 cleaned input이 support-sensitive over-pruning으로 읽힌다.
- [확정] current weighted regional CNN comparator는 `Houston timestamp F1 {cnn_rows[0]['f1']:.4f}`, `Seattle own_ship F1 {cnn_rows[1]['f1']:.4f}`, `NOLA own_ship F1 {cnn_rows[2]['f1']:.4f}`에 머물렀고, cleaned subset이 current learned regional baseline을 자동으로 안정화해주지 않았다.
- [확정] 가장 방어적인 문장은 다음과 같다: `Observed-pair cleaned-input control confirms a real input-quality effect in the error structure, but under the strict leak-fix rerun it is better interpreted as a diagnostic control than as a performance-improving preprocessing step. It sharply degrades Houston, slightly lowers Seattle and NOLA hgbt while reducing false positives, and does not stabilize the current learned regional CNN comparator.`

## 5. 산출물

- CSV: [cleaned_input_control_multiarea_summary_61day.csv](/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/cleaned_input_control_multiarea_summary_61day.csv)
- CNN CSV: [cleaned_input_control_multiarea_cnn_summary_61day.csv](/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/cleaned_input_control_multiarea_cnn_summary_61day.csv)
"""

    note_path = OUT_DIR / "cleaned_input_control_multiarea_note_61day.md"
    note_path.write_text(note)
    print(note_path)
    print(csv_path)
    print(cnn_csv_path)


if __name__ == "__main__":
    main()
