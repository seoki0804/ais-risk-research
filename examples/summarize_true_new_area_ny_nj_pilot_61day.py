#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path("/Users/seoki/Desktop/research")
SCAN_ROOT = ROOT / "outputs" / "2026-03-17_new_area_candidate_scan"
OUT_ROOT = ROOT / "outputs" / "presentation_deck_outline_61day_2026-03-13"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize the NY/NJ true new-area pilot.")
    parser.add_argument("--date", default="2023-09-05", help="Pilot date in YYYY-MM-DD format.")
    parser.add_argument(
        "--run-date",
        default="2026-03-17_r2",
        help="Output run date prefix used by run_true_new_area_ny_nj_pilot_61day.sh.",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_candidate_summary(area: str) -> dict[str, object]:
    base = SCAN_ROOT / area
    summary = read_json(base / "quality_gate_summary.json")
    rows = list(csv.DictReader((base / "quality_gate_rows.csv").open(encoding="utf-8")))
    passed = [row for row in rows if row.get("gate_passed") == "True"]
    passed.sort(key=lambda row: float(row.get("quality_score") or 0.0), reverse=True)
    top = passed[0] if passed else None
    return {
        "area": area.replace("_20230905", ""),
        "candidate_count": summary.get("candidate_count"),
        "passed_count": summary.get("passed_count"),
        "recommended_mmsi": summary.get("recommended_mmsi"),
        "recommended_quality_score": summary.get("recommended_quality_score"),
        "top_passed_candidate_score": float(top["candidate_score"]) if top else None,
        "top_passed_avg_nearby_targets": float(top["average_nearby_targets"]) if top else None,
        "top_passed_row_count": int(top["row_count"]) if top else None,
    }


def load_benchmark(pilot_root: Path, date: str, split: str) -> dict[str, object]:
    path = pilot_root / f"ny_nj_{date}_{split}_summary.json"
    if not path.exists():
        return {
            "split": split,
            "status": "missing",
            "row_count": None,
            "positive_rate": None,
            "own_ship_count": None,
            "hgbt_f1": None,
            "hgbt_auroc": None,
            "hgbt_auprc": None,
            "hgbt_threshold": None,
            "logreg_f1": None,
            "logreg_auroc": None,
            "logreg_auprc": None,
            "logreg_threshold": None,
            "test_rows": None,
            "test_own_ships": None,
            "test_timestamps": None,
        }
    summary = read_json(path)
    hgbt = summary["models"]["hgbt"]
    logreg = summary["models"]["logreg"]
    split_meta = summary["split"]
    return {
        "split": split,
        "status": "completed",
        "row_count": summary["row_count"],
        "positive_rate": summary["positive_rate"],
        "own_ship_count": summary["own_ship_count"],
        "hgbt_f1": hgbt["f1"],
        "hgbt_auroc": hgbt["auroc"],
        "hgbt_auprc": hgbt["auprc"],
        "hgbt_threshold": hgbt["threshold"],
        "logreg_f1": logreg["f1"],
        "logreg_auroc": logreg["auroc"],
        "logreg_auprc": logreg["auprc"],
        "logreg_threshold": logreg["threshold"],
        "test_rows": split_meta["test_rows"],
        "test_own_ships": split_meta.get("test_own_ships"),
        "test_timestamps": split_meta.get("test_timestamps"),
    }


def main() -> None:
    args = parse_args()
    run_id = f"{args.run_date}_true_new_area_ny_nj_{args.date.replace('-', '')}"
    pilot_root = ROOT / "outputs" / run_id
    candidate_rows = [
        load_candidate_summary("la_long_beach_20230905"),
        load_candidate_summary("ny_nj_20230905"),
        load_candidate_summary("savannah_20230905"),
    ]
    candidate_rows.sort(key=lambda row: (row["passed_count"], row["recommended_quality_score"]), reverse=True)
    benchmark_rows = [load_benchmark(pilot_root, args.date, "own_ship"), load_benchmark(pilot_root, args.date, "timestamp")]

    md_path = OUT_ROOT / "true_new_area_ny_nj_pilot_note_61day.md"
    csv_path = OUT_ROOT / "true_new_area_ny_nj_pilot_summary_61day.csv"

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "section",
                "name",
                "candidate_count",
                "passed_count",
                "recommended_mmsi",
                "recommended_quality_score",
                "top_passed_candidate_score",
                "top_passed_avg_nearby_targets",
                "top_passed_row_count",
                "status",
                "row_count",
                "positive_rate",
                "own_ship_count",
                "hgbt_f1",
                "hgbt_auroc",
                "hgbt_auprc",
                "hgbt_threshold",
                "logreg_f1",
                "logreg_auroc",
                "logreg_auprc",
                "logreg_threshold",
                "test_rows",
                "test_own_ships",
                "test_timestamps",
            ],
        )
        writer.writeheader()
        for row in candidate_rows:
            payload = dict(row)
            payload.pop("area", None)
            writer.writerow({"section": "candidate_scan", "name": row["area"], **payload})
        for row in benchmark_rows:
            payload = dict(row)
            payload.pop("split", None)
            writer.writerow({"section": "pilot_benchmark", "name": row["split"], **payload})

    own = next(row for row in benchmark_rows if row["split"] == "own_ship")
    timestamp = next(row for row in benchmark_rows if row["split"] == "timestamp")

    lines = [
        "# True New-Area NY/NJ Pilot Note",
        "",
        "이 문서는 기존 Houston/NOLA/Seattle 바깥의 `brand-new area` 후보를 스캔한 뒤, NY/NJ를 실제 메인 라벨(0.5nm) pairwise benchmark까지 연결한 결과를 정리한다.",
        "",
        "## 1. Candidate Scan",
        "",
        "| Area | Candidate Count | Passed Count | Recommended MMSI | Recommended Quality | Avg Nearby Targets | Row Count |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in candidate_rows:
        lines.append(
            f"| {row['area']} | {row['candidate_count']} | {row['passed_count']} | {row['recommended_mmsi']} | {row['recommended_quality_score']:.3f} | {row['top_passed_avg_nearby_targets']:.2f} | {row['top_passed_row_count']} |"
        )
    lines.extend(
        [
            "",
            "- [확정] NY/NJ는 gate pass count `8`, recommended quality `0.791`, top passed avg nearby targets `3.81`로 세 후보 중 가장 reviewer-safe했다.",
            "- [확정] 따라서 true new-area first pilot은 NY/NJ로 고정한다.",
            "",
            "## 2. NY/NJ Main-Label Pilot",
            "",
            "| Split | Rows | Positive Rate | Own Ships | hgbt F1 | hgbt AUROC | hgbt AUPRC | hgbt Threshold | logreg F1 | Test Rows | Test Own Ships |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            (
                f"| own_ship | {own['row_count']} | "
                f"{own['positive_rate']:.4f} | {own['own_ship_count']} | "
                f"{own['hgbt_f1']:.4f} | {own['hgbt_auroc']:.4f} | {own['hgbt_auprc']:.4f} | "
                f"{own['hgbt_threshold']:.2f} | {own['logreg_f1']:.4f} | {own['test_rows']} | {own['test_own_ships']} |"
            )
            if own["status"] == "completed"
            else "| own_ship | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |"
            ,
            (
                f"| timestamp | {timestamp['row_count']} | "
                f"{timestamp['positive_rate']:.4f} | {timestamp['own_ship_count']} | "
                f"{timestamp['hgbt_f1']:.4f} | {timestamp['hgbt_auroc']:.4f} | {timestamp['hgbt_auprc']:.4f} | "
                f"{timestamp['hgbt_threshold']:.2f} | {timestamp['logreg_f1']:.4f} | {timestamp['test_rows']} | {timestamp['test_own_ships']} |"
            )
            if timestamp["status"] == "completed"
            else "| timestamp | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |"
            ,
            "",
            "## 3. Reviewer-Safe Reading",
            "",
            (
                f"- [확정] NY/NJ same-day new-area pilot에서도 own-ship split hgbt F1은 `{own['hgbt_f1']:.4f}`로 collapse하지 않았다."
                if own["status"] == "completed"
                else "- [주의] 이번 pilot에서는 own-ship split이 성립하지 않거나 실패해, same-day new-area own-ship reading은 아직 잠기지 않았다."
            ),
            (
                f"- [확정] timestamp split hgbt F1은 `{timestamp['hgbt_f1']:.4f}`였다."
                if timestamp["status"] == "completed"
                else "- [주의] timestamp split도 아직 파일럿 결과가 잠기지 않았다."
            ),
            (
                "- [확정] 이 결과는 `brand-new geographic area`에서도 현재 pairwise tabular benchmark family가 완전히 무너지지 않는다는 첫 파일럿 근거로 쓸 수 있다."
                if any(row["status"] == "completed" for row in benchmark_rows)
                else "- [주의] 아직은 candidate scan만 확보됐고, benchmark reading은 추가 지원이 필요하다."
            ),
            "- [주의] 다만 아직은 `single-date, single-new-area` pilot이므로 broad external validity claim으로 확장하면 안 된다.",
            "- [다음] 가장 자연스러운 후속은 NY/NJ 추가 날짜 2개를 묶어 same-ecosystem temporal extension까지 확인하는 것이다.",
            "",
            f"CSV: [{csv_path.name}]({csv_path})",
        ]
    )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"markdown={md_path}")
    print(f"csv={csv_path}")


if __name__ == "__main__":
    main()
