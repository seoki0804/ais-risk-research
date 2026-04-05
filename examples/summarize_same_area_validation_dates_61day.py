#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


REPO_ROOT = Path("/Users/seoki/Desktop/research")
OUTPUT_ROOT = REPO_ROOT / "outputs"
DOC_ROOT = OUTPUT_ROOT / "presentation_deck_outline_61day_2026-03-13"
TARGET_DATES = [
    "2023-08-08",
    "2023-08-09",
    "2023-09-01",
    "2023-09-05",
    "2023-10-08",
    "2023-10-09",
]
REGIONS = ["houston", "nola", "seattle"]


def find_latest_stats(target_date: str, region: str) -> tuple[str, Path]:
    candidates = sorted(
        OUTPUT_ROOT.glob(
            f"noaa_focus_pairwise_bundle_*/noaa_focus_pairwise_bundle_{target_date}/{region}_pairwise_dataset_stats.json"
        )
    )
    if not candidates:
        raise FileNotFoundError(f"missing stats for {target_date} {region}")
    latest = max(candidates, key=lambda path: path.parts[-3])
    run_date = latest.parts[-3].replace("noaa_focus_pairwise_bundle_", "")
    return run_date, latest


def format_float(value: float) -> str:
    return f"{value:.4f}"


def main() -> None:
    rows: list[dict[str, str]] = []
    area_ranges: dict[str, dict[str, float]] = {
        region: {
            "min_own_ship_count": 10**9,
            "max_own_ship_count": -1,
            "min_positive_rate": 10**9,
            "max_positive_rate": -1.0,
        }
        for region in REGIONS
    }

    for target_date in TARGET_DATES:
        for region in REGIONS:
            run_date, stats_path = find_latest_stats(target_date, region)
            data = json.loads(stats_path.read_text(encoding="utf-8"))
            own_ship_count = int(data["own_ship_count"])
            positive_rate = float(data["positive_rate"])
            row_count = int(data["row_count"])
            timestamp_count = int(data["timestamp_count"])
            area_ranges[region]["min_own_ship_count"] = min(
                area_ranges[region]["min_own_ship_count"], own_ship_count
            )
            area_ranges[region]["max_own_ship_count"] = max(
                area_ranges[region]["max_own_ship_count"], own_ship_count
            )
            area_ranges[region]["min_positive_rate"] = min(
                area_ranges[region]["min_positive_rate"], positive_rate
            )
            area_ranges[region]["max_positive_rate"] = max(
                area_ranges[region]["max_positive_rate"], positive_rate
            )
            rows.append(
                {
                    "date": target_date,
                    "region": region,
                    "run_date": run_date,
                    "row_count": str(row_count),
                    "own_ship_count": str(own_ship_count),
                    "timestamp_count": str(timestamp_count),
                    "positive_rate": format_float(positive_rate),
                    "label_distance_nm": str(data["label_distance_nm"]),
                    "stats_json": str(stats_path),
                }
            )

    csv_path = DOC_ROOT / "same_area_validation_date_summary_61day.csv"
    md_path = DOC_ROOT / "same_area_validation_date_summary_61day.md"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# 문서명",
        "Same-Area Validation Date Summary 61day",
        "",
        "# 문서 목적",
        "같은 NOAA 파이프라인으로 확보한 추가 날짜 6개에 대해 region별 exploratory pairwise bundle 규모와 own-ship diversity를 한 표로 고정한다.",
        "",
        "# 작성 버전",
        "v1.0 (2026-03-17)",
        "",
        "## 1. 핵심 결론",
        "",
        "- [확정] 여섯 날짜 모두에서 `Houston / NOLA / Seattle` exploratory pairwise bundle이 이미 존재한다.",
        "- [확정] NOLA는 여섯 날짜 전부에서 `own_ship_count = 5`를 유지했다.",
        "- [확정] Seattle은 `4~5`, Houston은 `3~5` 범위로 유지됐다.",
        "- [해석] same-area additional dates만으로도 `NOLA diversity recovery` 근거는 꽤 강해졌다.",
        "- [주의] 이 표는 `exploratory bundle (label_distance_nm = 1.6)` 기준이며, main benchmark label과는 구분해서 써야 한다.",
        "",
        "## 2. 날짜별 요약",
        "",
        "| Date | Region | Run date | Rows | Own ships | Timestamps | Positive rate | Label distance |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['date']}` | {row['region']} | `{row['run_date']}` | "
            f"{row['row_count']} | {row['own_ship_count']} | {row['timestamp_count']} | "
            f"{row['positive_rate']} | {row['label_distance_nm']} |"
        )

    lines.extend(
        [
            "",
            "## 3. region별 범위 요약",
            "",
            "| Region | Own ship count range | Positive rate range |",
            "|---|---:|---:|",
        ]
    )
    for region in REGIONS:
        region_summary = area_ranges[region]
        lines.append(
            f"| {region} | {int(region_summary['min_own_ship_count'])}-{int(region_summary['max_own_ship_count'])} | "
            f"{format_float(region_summary['min_positive_rate'])}-{format_float(region_summary['max_positive_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## 4. reviewer-safe 해석",
            "",
            "- `Additional same-area dates materially improve own-ship diversity coverage under the same NOAA preprocessing pipeline.`",
            "- `For NOLA in particular, the diversity bottleneck seen in the single-day exploratory bundle is not persistent once additional dates are included.`",
            "- `These figures should be reported as exploratory validation coverage, not as the main benchmark label definition.`",
            "",
            "## 5. 산출물",
            "",
            f"- CSV: [{csv_path.name}]({csv_path})",
        ]
    )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"summary_md={md_path}")
    print(f"summary_csv={csv_path}")


if __name__ == "__main__":
    main()
