#!/usr/bin/env python3
"""Summarize same-area single-day support/threshold pathology against pooled runs."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import mean, pstdev


ROOT = Path("/Users/seoki/Desktop/research")
SUMMARY_CSV = ROOT / "outputs/presentation_deck_outline_61day_2026-03-13/same_area_main_benchmark_summary_61day.csv"
POOLED_DIR = ROOT / "outputs/noaa_same_area_pooled_benchmark_61day_2026-03-17"
OUT_DIR = ROOT / "outputs/presentation_deck_outline_61day_2026-03-13"
OUT_MD = OUT_DIR / "support_threshold_pathology_summary_61day.md"
OUT_CSV = OUT_DIR / "support_threshold_pathology_summary_61day.csv"

LOW_POSITIVE_RATE = 0.10
HIGH_THRESHOLD = 0.50
REGIONS = ("houston", "nola", "seattle")


def fmt_float(value: float) -> str:
    return f"{value:.4f}"


def load_single_day_rows() -> list[dict[str, str]]:
    with SUMMARY_CSV.open() as fp:
        return list(csv.DictReader(fp))


def load_pooled_json(region: str) -> dict:
    with (POOLED_DIR / f"{region}_pooled_own_ship_summary.json").open() as fp:
        return json.load(fp)


def build_region_summary(rows: list[dict[str, str]], pooled: dict) -> dict[str, str]:
    f1_values = [float(row["hgbt_f1"]) for row in rows]
    thr_values = [float(row["hgbt_threshold"]) for row in rows]
    pos_values = [float(row["positive_rate"]) for row in rows]

    zero_rows = [row for row in rows if float(row["hgbt_f1"]) == 0.0]
    low_rows = [row for row in rows if float(row["positive_rate"]) < LOW_POSITIVE_RATE]
    low_zero_rows = [
        row
        for row in rows
        if float(row["positive_rate"]) < LOW_POSITIVE_RATE and float(row["hgbt_f1"]) == 0.0
    ]
    high_thr_rows = [row for row in rows if float(row["hgbt_threshold"]) >= HIGH_THRESHOLD]

    pooled_f1 = float(pooled["models"]["hgbt"]["f1"])
    pooled_thr = float(pooled["models"]["hgbt"]["threshold"])
    pooled_pos = float(pooled["positive_rate"])

    return {
        "region": rows[0]["region"],
        "single_day_mean_f1": fmt_float(mean(f1_values)),
        "single_day_min_f1": fmt_float(min(f1_values)),
        "single_day_max_f1": fmt_float(max(f1_values)),
        "single_day_mean_positive_rate": fmt_float(mean(pos_values)),
        "single_day_low_positive_day_count": str(len(low_rows)),
        "single_day_zero_f1_day_count": str(len(zero_rows)),
        "single_day_low_positive_zero_f1_count": str(len(low_zero_rows)),
        "single_day_threshold_mean": fmt_float(mean(thr_values)),
        "single_day_threshold_std": fmt_float(pstdev(thr_values)),
        "single_day_threshold_min": fmt_float(min(thr_values)),
        "single_day_threshold_max": fmt_float(max(thr_values)),
        "single_day_high_threshold_day_count": str(len(high_thr_rows)),
        "pooled_positive_rate": fmt_float(pooled_pos),
        "pooled_hgbt_f1": fmt_float(pooled_f1),
        "pooled_hgbt_threshold": fmt_float(pooled_thr),
        "pooled_minus_single_day_mean_f1": fmt_float(pooled_f1 - mean(f1_values)),
    }


def build_day_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row in rows:
        positive_rate = float(row["positive_rate"])
        f1 = float(row["hgbt_f1"])
        threshold = float(row["hgbt_threshold"])
        flags: list[str] = []
        if positive_rate < LOW_POSITIVE_RATE:
            flags.append("low_positive_rate")
        if threshold >= HIGH_THRESHOLD:
            flags.append("high_selected_threshold")
        if f1 == 0.0:
            flags.append("zero_f1")
        output.append(
            {
                "date": row["date"],
                "region": row["region"],
                "rows": row["row_count"],
                "own_ships": row["own_ship_count"],
                "positive_rate": fmt_float(positive_rate),
                "hgbt_f1": fmt_float(f1),
                "hgbt_threshold": fmt_float(threshold),
                "pathology_flags": ",".join(flags) if flags else "none",
            }
        )
    return output


def write_csv(region_rows: list[dict[str, str]], day_rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "record_type",
        "region",
        "date",
        "rows",
        "own_ships",
        "positive_rate",
        "hgbt_f1",
        "hgbt_threshold",
        "pathology_flags",
        "single_day_mean_f1",
        "single_day_min_f1",
        "single_day_max_f1",
        "single_day_mean_positive_rate",
        "single_day_low_positive_day_count",
        "single_day_zero_f1_day_count",
        "single_day_low_positive_zero_f1_count",
        "single_day_threshold_mean",
        "single_day_threshold_std",
        "single_day_threshold_min",
        "single_day_threshold_max",
        "single_day_high_threshold_day_count",
        "pooled_positive_rate",
        "pooled_hgbt_f1",
        "pooled_hgbt_threshold",
        "pooled_minus_single_day_mean_f1",
    ]
    with OUT_CSV.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in region_rows:
            writer.writerow({"record_type": "region_summary", **row})
        for row in day_rows:
            writer.writerow({"record_type": "day_detail", **row})


def render_markdown(region_rows: list[dict[str, str]], day_rows: list[dict[str, str]]) -> str:
    lines: list[str] = [
        "# 문서명",
        "Support Threshold Pathology Summary 61day",
        "",
        "# 문서 목적",
        "same-area main benchmark의 single-day own-ship 성능 붕괴가 sparse-day support와 threshold selection swing에 얼마나 연결되는지 pooled benchmark와 함께 요약한다.",
        "",
        "# 작성 버전",
        "v1.0 (2026-03-17)",
        "",
        "## 1. 핵심 해석",
        "",
        f"- [확정] 현재 pathology flag는 `positive_rate < {LOW_POSITIVE_RATE:.2f}`를 sparse-day support 경고, `hgbt_threshold >= {HIGH_THRESHOLD:.2f}`를 high-threshold swing 경고로 둔다.",
        "- [확정] Houston은 sparse-day support와 threshold swing이 가장 강하게 겹친다.",
        "- [확정] Seattle은 single-day pathology가 존재하지만 pooled benchmark에서 상당 부분 완화된다.",
        "- [확정] NOLA는 sparse-day pathology만으로 설명되지 않는다. threshold dispersion은 작지만 pooled own-ship F1도 중간 수준에 머문다.",
        "",
        "## 2. 지역별 요약",
        "",
        "| Region | Single-day mean F1 | F1 range | Mean positive rate | Low-pos days | Zero-F1 days | High-thr days | Threshold range | Pooled F1 | Pooled - mean |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in region_rows:
        lines.append(
            f"| `{row['region']}` | {row['single_day_mean_f1']} | {row['single_day_min_f1']}-{row['single_day_max_f1']} | "
            f"{row['single_day_mean_positive_rate']} | {row['single_day_low_positive_day_count']} | "
            f"{row['single_day_zero_f1_day_count']} | {row['single_day_high_threshold_day_count']} | "
            f"{row['single_day_threshold_min']}-{row['single_day_threshold_max']} | {row['pooled_hgbt_f1']} | "
            f"{row['pooled_minus_single_day_mean_f1']} |"
        )
    lines.extend(
        [
            "",
            "## 3. 날짜별 pathology detail",
            "",
            "| Date | Region | Rows | Own ships | Positive rate | hgbt F1 | hgbt thr | Flags |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in sorted(day_rows, key=lambda item: (item["date"], item["region"])):
        lines.append(
            f"| `{row['date']}` | `{row['region']}` | {row['rows']} | {row['own_ships']} | {row['positive_rate']} | "
            f"{row['hgbt_f1']} | {row['hgbt_threshold']} | `{row['pathology_flags']}` |"
        )
    lines.extend(
        [
            "",
            "## 4. reviewer-safe 요약",
            "",
            "- Houston에서는 `low-positive-rate + high-threshold swing + zero-F1`가 같은 날짜에 자주 겹친다. 따라서 single-day own-ship 실패의 큰 부분은 sparse-day threshold pathology로 읽는 것이 타당하다.",
            "- Seattle도 single-day zero-F1/threshold swing이 존재하지만, pooled benchmark에서 `0.7952`까지 회복돼 single-day support pathology 설명이 더 잘 맞는다.",
            "- NOLA는 additional dates로 own-ship coverage를 회복했지만, threshold dispersion이 크지 않은데도 pooled own-ship F1이 `0.4857`에 머문다. 따라서 남은 NOLA difficulty는 sparse-day threshold pathology만으로는 충분히 설명되지 않는다.",
            "- reviewer-safe reading은 `additional dates fix coverage, pooled evaluation reduces sparse-day pathology in Houston and Seattle, but NOLA remains a harder same-area transfer case for reasons beyond own-ship count alone.`",
            "",
            "## 5. 산출물",
            "",
            f"- CSV: [{OUT_CSV.name}]({OUT_CSV})",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    all_rows = load_single_day_rows()
    own_ship_rows = [row for row in all_rows if row["split"] == "own_ship"]
    region_rows = []
    for region in REGIONS:
        region_own_ship_rows = [row for row in own_ship_rows if row["region"] == region]
        pooled = load_pooled_json(region)
        region_rows.append(build_region_summary(region_own_ship_rows, pooled))
    day_rows = build_day_rows(own_ship_rows)
    write_csv(region_rows, day_rows)
    OUT_MD.write_text(render_markdown(region_rows, day_rows))


if __name__ == "__main__":
    main()
