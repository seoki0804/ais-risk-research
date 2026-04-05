#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REPO_ROOT = Path("/Users/seoki/Desktop/research")
OUTPUT_ROOT = REPO_ROOT / "outputs"
DOC_ROOT = OUTPUT_ROOT / "presentation_deck_outline_61day_2026-03-13"
DEFAULT_DATES = [
    "2023-08-08",
    "2023-08-09",
    "2023-09-01",
    "2023-09-05",
    "2023-10-08",
    "2023-10-09",
]
REGIONS = ["houston", "nola", "seattle"]
SPLITS = ["own_ship", "timestamp"]
MODELS = ["hgbt", "logreg"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize same-area main benchmark outputs for the 61day validation date expansion set."
    )
    parser.add_argument("--run-date", default="2026-03-17", help="Benchmark output run date.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    benchmark_root = OUTPUT_ROOT / f"noaa_same_area_main_benchmark_61day_{args.run_date}"
    rows: list[dict[str, str]] = []
    nola_own_ship_f1: list[float] = []

    for date in DEFAULT_DATES:
        for region in REGIONS:
            for split in SPLITS:
                summary_path = benchmark_root / f"{region}_{date}_{split}_summary.json"
                if not summary_path.exists():
                    continue
                data = json.loads(summary_path.read_text(encoding="utf-8"))
                record = {
                    "date": date,
                    "region": region,
                    "split": split,
                    "row_count": str(data["row_count"]),
                    "own_ship_count": str(data["own_ship_count"]),
                    "positive_rate": f"{float(data['positive_rate']):.4f}",
                    "hgbt_f1": f"{float(data['models']['hgbt']['f1']):.4f}",
                    "logreg_f1": f"{float(data['models']['logreg']['f1']):.4f}",
                    "hgbt_threshold": str(data["models"]["hgbt"]["threshold"]),
                    "logreg_threshold": str(data["models"]["logreg"]["threshold"]),
                    "summary_json": str(summary_path),
                }
                rows.append(record)
                if region == "nola" and split == "own_ship":
                    nola_own_ship_f1.append(float(data["models"]["hgbt"]["f1"]))

    rows.sort(key=lambda item: (item["date"], item["region"], item["split"]))
    if not rows:
        raise SystemExit(f"no benchmark summaries found under {benchmark_root}")

    csv_path = DOC_ROOT / "same_area_main_benchmark_summary_61day.csv"
    md_path = DOC_ROOT / "same_area_main_benchmark_summary_61day.md"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with csv_path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    nola_line = "n/a"
    if nola_own_ship_f1:
        nola_line = f"{min(nola_own_ship_f1):.4f}-{max(nola_own_ship_f1):.4f}"

    lines = [
        "# 문서명",
        "Same-Area Main Benchmark Summary 61day",
        "",
        "# 문서 목적",
        "same-area additional dates를 main benchmark label(0.5 nm)과 main evaluation split으로 다시 연결한 결과를 한 표로 고정한다.",
        "",
        "# 작성 버전",
        "v1.0 (2026-03-17)",
        "",
        "## 1. 핵심 해석",
        "",
        "- [확정] 이 표는 exploratory coverage summary가 아니라 `main benchmark protocol` 결과를 모은다.",
        f"- [확정] current run-date: `{args.run_date}`",
        f"- [확정] NOLA own-ship hgbt F1 range across available dates: `{nola_line}`",
        "",
        "## 2. 날짜별 benchmark 요약",
        "",
        "| Date | Region | Split | Rows | Own ships | Positive rate | hgbt F1 | logreg F1 | hgbt thr | logreg thr |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['date']}` | {row['region']} | `{row['split']}` | {row['row_count']} | "
            f"{row['own_ship_count']} | {row['positive_rate']} | {row['hgbt_f1']} | {row['logreg_f1']} | "
            f"{row['hgbt_threshold']} | {row['logreg_threshold']} |"
        )

    lines.extend(
        [
            "",
            "## 3. reviewer-safe 사용 규칙",
            "",
            "- [확정] exploratory same-area summary는 `coverage recovery` 증거다.",
            "- [확정] 이 표는 `main-label generalization`의 실제 성능을 본다.",
            "- [확정] 따라서 두 표를 분리해서 써야 한다.",
            "",
            "## 4. 산출물",
            "",
            f"- CSV: [{csv_path.name}]({csv_path})",
        ]
    )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"summary_md={md_path}")
    print(f"summary_csv={csv_path}")


if __name__ == "__main__":
    main()
