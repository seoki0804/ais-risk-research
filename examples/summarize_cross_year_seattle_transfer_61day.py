#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize pooled cross-year Seattle transfer runs.")
    parser.add_argument("--run-root", required=True, help="Directory containing transfer summary JSON files.")
    parser.add_argument("--output-md", required=True, help="Markdown note output path.")
    parser.add_argument("--output-csv", required=True, help="CSV summary output path.")
    return parser.parse_args()


def load_summary(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root)
    records: list[dict[str, object]] = []

    for label in ["seattle_2023_to_2024", "seattle_2024_to_2023"]:
        path = run_root / f"{label}_transfer_summary.json"
        payload = load_summary(path)
        hgbt = payload["models"]["hgbt"]["target_transfer"]
        logreg = payload["models"]["logreg"]["target_transfer"]
        records.append(
            {
                "label": label,
                "source_row_count": payload["source_row_count"],
                "target_row_count": payload["target_row_count"],
                "source_own_ship_count": payload["source_own_ship_count"],
                "target_own_ship_count": payload["target_own_ship_count"],
                "hgbt_f1": hgbt["f1"],
                "hgbt_auroc": hgbt["auroc"],
                "hgbt_auprc": hgbt["auprc"],
                "hgbt_threshold": hgbt["threshold"],
                "logreg_f1": logreg["f1"],
                "transfer_summary_json": str(path),
            }
        )

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    rec_23_24 = next(item for item in records if item["label"] == "seattle_2023_to_2024")
    rec_24_23 = next(item for item in records if item["label"] == "seattle_2024_to_2023")

    lines = [
        "# 문서명",
        "Cross-Year Seattle Transfer Note 61day",
        "",
        "# 문서 목적",
        "`2023 pooled Seattle -> 2024 pooled Seattle`와 반대 방향 transfer를 한 번에 정리해, second cross-year harbor evidence를 true transfer setting까지 확장한다.",
        "",
        "# 대상 독자",
        "주저자, 공동저자, reviewer 대응 작성자",
        "",
        "# 작성 버전",
        "v1.0 (2026-03-17)",
        "",
        "## 1. 핵심 결과",
        "",
        f"- [확정] `2023 -> 2024` pooled transfer에서 target-side `hgbt F1={rec_23_24['hgbt_f1']:.4f}`, `AUROC={rec_23_24['hgbt_auroc']:.4f}`, `AUPRC={rec_23_24['hgbt_auprc']:.4f}`이 나왔다.",
        f"- [확정] `2024 -> 2023` pooled transfer에서 target-side `hgbt F1={rec_24_23['hgbt_f1']:.4f}`, `AUROC={rec_24_23['hgbt_auroc']:.4f}`, `AUPRC={rec_24_23['hgbt_auprc']:.4f}`이 나왔다.",
        "- [확정] current Seattle result는 same-day pilot과 pooled own-ship benchmark를 넘어, pooled cross-year transfer까지 연결됐다.",
        "",
        "## 2. 요약표",
        "",
        "| direction | source rows | target rows | source own ships | target own ships | target hgbt F1 | target hgbt AUROC | target hgbt AUPRC | target logreg F1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for record in records:
        direction = "2023->2024" if record["label"] == "seattle_2023_to_2024" else "2024->2023"
        lines.append(
            f"| {direction} | {record['source_row_count']} | {record['target_row_count']} | "
            f"{record['source_own_ship_count']} | {record['target_own_ship_count']} | "
            f"{record['hgbt_f1']:.4f} | {record['hgbt_auroc']:.4f} | {record['hgbt_auprc']:.4f} | {record['logreg_f1']:.4f} |"
        )

    lines.extend(
        [
            "",
            "## 3. reviewer-safe interpretation",
            "",
            "- [확정] current Seattle result는 이제 `same-day`, `pooled own-ship`, `pooled cross-year transfer`까지 연결됐다.",
            "- [주의] 다만 이 결과도 여전히 `single harbor` 기준이므로, strongest safe phrasing은 `second cross-year harbor transfer evidence in Seattle`다.",
            "",
            "## 4. 진입점",
            "",
            f"- [CSV]({output_csv})",
            "- [2024 pooled note](/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/cross_year_2024_seattle_pooled_note_61day.md)",
        ]
    )

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
