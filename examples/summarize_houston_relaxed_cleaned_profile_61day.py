#!/usr/bin/env python3
"""Summarize Houston strict vs relaxed cleaned-input profiles."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd


ROOT = Path("/Users/seoki/Desktop/research")
OUT_DIR = ROOT / "outputs" / "presentation_deck_outline_61day_2026-03-13"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def confusion(path: Path, pred_col: str) -> dict[str, int]:
    df = pd.read_csv(path)
    label = df["label_future_conflict"].astype(int)
    pred = df[pred_col].astype(int)
    return {
        "tp": int(((label == 1) & (pred == 1)).sum()),
        "fp": int(((label == 0) & (pred == 1)).sum()),
        "tn": int(((label == 0) & (pred == 0)).sum()),
        "fn": int(((label == 1) & (pred == 0)).sum()),
    }


def model_metrics(summary: dict, model: str = "hgbt") -> dict:
    return summary["models"][model]


def main() -> None:
    raw_own = load_json(
        ROOT / "outputs/noaa_same_area_pooled_benchmark_61day_2026-03-17/houston_pooled_own_ship_summary.json"
    )
    raw_ts = load_json(
        ROOT / "outputs/noaa_same_area_pooled_benchmark_61day_2026-03-17/houston_pooled_timestamp_summary.json"
    )
    strict_filter = load_json(
        ROOT / "outputs/2026-03-17_houston_cleaned_input_control/houston_pooled_observed_pair_filter_summary.json"
    )
    strict_own = load_json(
        ROOT / "outputs/2026-03-17_houston_cleaned_input_control/houston_pooled_observed_pair_hgbt_summary.json"
    )
    strict_ts = load_json(
        ROOT / "outputs/2026-03-17_houston_cleaned_input_control/houston_pooled_observed_pair_timestamp_summary.json"
    )
    strict_cnn = load_json(
        ROOT
        / "outputs/2026-03-17_houston_cleaned_input_control/houston_pooled_observed_pair_timestamp_cnn_weighted_summary.json"
    )
    relaxed_filter = load_json(
        ROOT
        / "outputs/2026-03-17_houston_relaxed_cleaned_input_control/houston_pooled_own_observed_allow_target_interp_filter_summary.json"
    )
    relaxed_own = load_json(
        ROOT
        / "outputs/2026-03-17_houston_relaxed_cleaned_input_control/houston_pooled_own_observed_allow_target_interp_own_ship_summary.json"
    )
    relaxed_ts = load_json(
        ROOT
        / "outputs/2026-03-17_houston_relaxed_cleaned_input_control/houston_pooled_own_observed_allow_target_interp_timestamp_summary.json"
    )
    relaxed_cnn = load_json(
        ROOT
        / "outputs/2026-03-17_houston_relaxed_cleaned_input_control/houston_pooled_own_observed_allow_target_interp_timestamp_cnn_weighted_summary.json"
    )

    strict_own_conf = confusion(
        ROOT / "outputs/2026-03-17_houston_cleaned_input_control/houston_pooled_observed_pair_hgbt_test_predictions.csv",
        "hgbt_pred",
    )
    strict_ts_conf = confusion(
        ROOT / "outputs/2026-03-17_houston_cleaned_input_control/houston_pooled_observed_pair_timestamp_test_predictions.csv",
        "hgbt_pred",
    )
    relaxed_own_conf = confusion(
        ROOT
        / "outputs/2026-03-17_houston_relaxed_cleaned_input_control/houston_pooled_own_observed_allow_target_interp_own_ship_test_predictions.csv",
        "hgbt_pred",
    )
    relaxed_ts_conf = confusion(
        ROOT
        / "outputs/2026-03-17_houston_relaxed_cleaned_input_control/houston_pooled_own_observed_allow_target_interp_timestamp_test_predictions.csv",
        "hgbt_pred",
    )

    rows = [
        {
            "profile": "raw_own_ship",
            "rows": raw_own["row_count"],
            "positive_rate": raw_own["positive_rate"],
            "f1": model_metrics(raw_own)["f1"],
            "predicted_positive_rate": model_metrics(raw_own)["positive_rate_predicted"],
            "tp": None,
            "fp": None,
            "fn": None,
        },
        {
            "profile": "strict_observed_pair_own_ship",
            "rows": strict_filter["output_row_count"],
            "positive_rate": strict_filter["output_positive_rate"],
            "f1": model_metrics(strict_own)["f1"],
            "predicted_positive_rate": model_metrics(strict_own)["positive_rate_predicted"],
            "tp": strict_own_conf["tp"],
            "fp": strict_own_conf["fp"],
            "fn": strict_own_conf["fn"],
        },
        {
            "profile": "relaxed_own_observed_own_ship",
            "rows": relaxed_filter["output_row_count"],
            "positive_rate": relaxed_filter["output_positive_rate"],
            "f1": model_metrics(relaxed_own)["f1"],
            "predicted_positive_rate": model_metrics(relaxed_own)["positive_rate_predicted"],
            "tp": relaxed_own_conf["tp"],
            "fp": relaxed_own_conf["fp"],
            "fn": relaxed_own_conf["fn"],
        },
        {
            "profile": "raw_timestamp",
            "rows": raw_ts["row_count"],
            "positive_rate": raw_ts["positive_rate"],
            "f1": model_metrics(raw_ts)["f1"],
            "predicted_positive_rate": model_metrics(raw_ts)["positive_rate_predicted"],
            "tp": None,
            "fp": None,
            "fn": None,
        },
        {
            "profile": "strict_observed_pair_timestamp",
            "rows": strict_filter["output_row_count"],
            "positive_rate": strict_filter["output_positive_rate"],
            "f1": model_metrics(strict_ts)["f1"],
            "predicted_positive_rate": model_metrics(strict_ts)["positive_rate_predicted"],
            "tp": strict_ts_conf["tp"],
            "fp": strict_ts_conf["fp"],
            "fn": strict_ts_conf["fn"],
        },
        {
            "profile": "relaxed_own_observed_timestamp",
            "rows": relaxed_filter["output_row_count"],
            "positive_rate": relaxed_filter["output_positive_rate"],
            "f1": model_metrics(relaxed_ts)["f1"],
            "predicted_positive_rate": model_metrics(relaxed_ts)["positive_rate_predicted"],
            "tp": relaxed_ts_conf["tp"],
            "fp": relaxed_ts_conf["fp"],
            "fn": relaxed_ts_conf["fn"],
        },
        {
            "profile": "strict_observed_pair_timestamp_cnn_weighted",
            "rows": strict_filter["output_row_count"],
            "positive_rate": strict_filter["output_positive_rate"],
            "f1": strict_cnn["metrics"]["f1"],
            "predicted_positive_rate": strict_cnn["metrics"]["positive_rate_predicted"],
            "tp": strict_cnn["metrics"]["recall"],
            "fp": None,
            "fn": None,
        },
        {
            "profile": "relaxed_own_observed_timestamp_cnn_weighted",
            "rows": relaxed_filter["output_row_count"],
            "positive_rate": relaxed_filter["output_positive_rate"],
            "f1": relaxed_cnn["metrics"]["f1"],
            "predicted_positive_rate": relaxed_cnn["metrics"]["positive_rate_predicted"],
            "tp": relaxed_cnn["metrics"]["recall"],
            "fp": None,
            "fn": None,
        },
    ]

    csv_path = OUT_DIR / "houston_relaxed_cleaned_profile_summary_61day.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    note = f"""# 문서명
Houston Relaxed Cleaned Profile Note 61day

# 문서 목적
Houston에서 strict observed-pair cleaning이 support를 과도하게 줄였다는 해석이 맞는지, `own_observed_allow_target_interp` relaxed profile로 직접 확인한다.

# 작성 버전
v1.0 (2026-03-17)

## 1. 핵심 관찰

- [확정] Houston holdout own ship(`368221490`)의 유일한 positive row는 `own_is_interpolated=0`, `target_is_interpolated=1`, `future_points_used=2`였다.
- [확정] 따라서 `observed_pair`와 `observed_pair_fp5`는 모두 이 positive를 제거하며, Houston support collapse를 완화하지 못한다.
- [확정] Houston에서 진짜 relaxed control은 `own observed, target interpolation allowed` profile이다.

## 2. support recovery

- [확정] raw holdout own ship rows/positives: `92 / 1`
- [확정] strict observed-pair holdout rows/positives: `11 / 0`
- [확정] relaxed own-observed holdout rows/positives: `38 / 1`

## 3. benchmark comparison

| profile | rows | positive rate | hgbt F1 | predicted positive rate | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| raw own-ship | {raw_own['row_count']} | {raw_own['positive_rate']:.4f} | {model_metrics(raw_own)['f1']:.4f} | {model_metrics(raw_own)['positive_rate_predicted']:.4f} | - | - | - |
| strict observed-pair own-ship | {strict_filter['output_row_count']} | {strict_filter['output_positive_rate']:.4f} | {model_metrics(strict_own)['f1']:.4f} | {model_metrics(strict_own)['positive_rate_predicted']:.4f} | {strict_own_conf['tp']} | {strict_own_conf['fp']} | {strict_own_conf['fn']} |
| relaxed own-observed own-ship | {relaxed_filter['output_row_count']} | {relaxed_filter['output_positive_rate']:.4f} | {model_metrics(relaxed_own)['f1']:.4f} | {model_metrics(relaxed_own)['positive_rate_predicted']:.4f} | {relaxed_own_conf['tp']} | {relaxed_own_conf['fp']} | {relaxed_own_conf['fn']} |
| raw timestamp | {raw_ts['row_count']} | {raw_ts['positive_rate']:.4f} | {model_metrics(raw_ts)['f1']:.4f} | {model_metrics(raw_ts)['positive_rate_predicted']:.4f} | - | - | - |
| strict observed-pair timestamp | {strict_filter['output_row_count']} | {strict_filter['output_positive_rate']:.4f} | {model_metrics(strict_ts)['f1']:.4f} | {model_metrics(strict_ts)['positive_rate_predicted']:.4f} | {strict_ts_conf['tp']} | {strict_ts_conf['fp']} | {strict_ts_conf['fn']} |
| relaxed own-observed timestamp | {relaxed_filter['output_row_count']} | {relaxed_filter['output_positive_rate']:.4f} | {model_metrics(relaxed_ts)['f1']:.4f} | {model_metrics(relaxed_ts)['positive_rate_predicted']:.4f} | {relaxed_ts_conf['tp']} | {relaxed_ts_conf['fp']} | {relaxed_ts_conf['fn']} |

## 4. current weighted CNN on Houston cleaned profiles

- [확정] strict observed-pair timestamp CNN: `F1 {strict_cnn['metrics']['f1']:.4f}`, predicted positive rate `{strict_cnn['metrics']['positive_rate_predicted']:.4f}`
- [확정] relaxed own-observed timestamp CNN: `F1 {relaxed_cnn['metrics']['f1']:.4f}`, predicted positive rate `{relaxed_cnn['metrics']['positive_rate_predicted']:.4f}`

## 5. reviewer-safe reading

- [확정] Houston support collapse under strict cleaning is not a generic cleaned-input result; it is caused by a specific profile mismatch in which the only positive holdout row requires target interpolation.
- [확정] `observed_pair_fp5` is stricter, not more relaxed, for Houston and therefore is not the right recovery profile.
- [확정] reviewer-safe interpretation should therefore separate `strict observed-pair cleaning` from `own-observed relaxed cleaning` when discussing Houston.

## 6. 산출물

- CSV: [houston_relaxed_cleaned_profile_summary_61day.csv](/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/houston_relaxed_cleaned_profile_summary_61day.csv)
"""
    note_path = OUT_DIR / "houston_relaxed_cleaned_profile_note_61day.md"
    note_path.write_text(note)
    print(note_path)
    print(csv_path)


if __name__ == "__main__":
    main()
