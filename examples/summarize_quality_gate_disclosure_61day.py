from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from ais_risk.own_ship_quality_gate import (
    apply_own_ship_quality_gate,
    build_own_ship_quality_gate_summary,
    load_own_ship_candidate_rows,
)


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _mean(rows: list[dict[str, object]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(_safe_float(row.get(key)) for row in rows) / float(len(rows))


def _parse_entry(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("expected NAME=PATH")
    name, path_value = raw.split("=", 1)
    name = name.strip()
    path = Path(path_value).expanduser()
    if not name:
        raise argparse.ArgumentTypeError("entry name must not be empty")
    return name, path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize own-ship quality gate disclosure across regions.")
    parser.add_argument("--entry", action="append", required=True, type=_parse_entry, help="NAME=path/to/own_ship_candidates.csv")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-md", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows_out: list[dict[str, object]] = []

    for name, path in args.entry:
        candidate_rows = load_own_ship_candidate_rows(path)
        gated_rows = apply_own_ship_quality_gate(candidate_rows)
        summary = build_own_ship_quality_gate_summary(
            gated_rows,
            input_path=path,
            min_row_count=80,
            min_observed_row_count=40,
            max_interpolation_ratio=0.70,
            min_heading_coverage_ratio=0.50,
            min_movement_ratio=0.30,
            min_active_window_ratio=0.10,
            min_average_nearby_targets=0.50,
            max_segment_break_count=50,
            min_candidate_score=0.20,
            min_recommended_target_count=1,
        )
        passed_rows = [row for row in gated_rows if bool(row.get("gate_passed"))]
        failed_rows = [row for row in gated_rows if not bool(row.get("gate_passed"))]

        fail_counter: Counter[str] = Counter()
        for row in failed_rows:
            for reason in str(row.get("fail_reason_text") or "").split("; "):
                if reason and reason != "-":
                    fail_counter[reason] += 1
        top_fail = [item[0] for item in fail_counter.most_common(3)]
        while len(top_fail) < 3:
            top_fail.append("")

        rows_out.append(
            {
                "region_case": name,
                "candidate_count": summary["candidate_count"],
                "passed_count": summary["passed_count"],
                "pass_ratio": summary["pass_ratio"],
                "recommended_mmsi": summary.get("recommended_mmsi") or "",
                "top_fail_1": top_fail[0],
                "top_fail_2": top_fail[1],
                "top_fail_3": top_fail[2],
                "candidate_score_all_mean": _mean(gated_rows, "candidate_score"),
                "candidate_score_passed_mean": _mean(passed_rows, "candidate_score"),
                "interpolation_ratio_all_mean": _mean(gated_rows, "interpolation_ratio"),
                "interpolation_ratio_passed_mean": _mean(passed_rows, "interpolation_ratio"),
                "movement_ratio_all_mean": _mean(gated_rows, "movement_ratio"),
                "movement_ratio_passed_mean": _mean(passed_rows, "movement_ratio"),
                "active_window_ratio_all_mean": _mean(gated_rows, "active_window_ratio"),
                "active_window_ratio_passed_mean": _mean(passed_rows, "active_window_ratio"),
                "average_nearby_targets_all_mean": _mean(gated_rows, "average_nearby_targets"),
                "average_nearby_targets_passed_mean": _mean(passed_rows, "average_nearby_targets"),
            }
        )

    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(rows_out[0].keys()) if rows_out else []
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    md_lines = [
        "# Own-Ship Quality Gate Disclosure Summary 61day",
        "",
        "| region/case | candidates | passed | pass ratio | recommended MMSI | top fail 1 | top fail 2 | top fail 3 |",
        "|---|---:|---:|---:|---|---|---|---|",
    ]
    for row in rows_out:
        md_lines.append(
            "| {region_case} | {candidate_count} | {passed_count} | {pass_ratio:.3f} | {recommended_mmsi} | {top_fail_1} | {top_fail_2} | {top_fail_3} |".format(
                **row
            )
        )

    md_lines.extend(
        [
            "",
            "## Metric Means",
            "",
            "| region/case | cand score all | cand score passed | interp all | interp passed | movement all | movement passed | active all | active passed | nearby all | nearby passed |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows_out:
        md_lines.append(
            "| {region_case} | {candidate_score_all_mean:.3f} | {candidate_score_passed_mean:.3f} | {interpolation_ratio_all_mean:.3f} | {interpolation_ratio_passed_mean:.3f} | {movement_ratio_all_mean:.3f} | {movement_ratio_passed_mean:.3f} | {active_window_ratio_all_mean:.3f} | {active_window_ratio_passed_mean:.3f} | {average_nearby_targets_all_mean:.3f} | {average_nearby_targets_passed_mean:.3f} |".format(
                **row
            )
        )

    output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"rows={len(rows_out)}")
    print(f"csv={output_csv}")
    print(f"md={output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
