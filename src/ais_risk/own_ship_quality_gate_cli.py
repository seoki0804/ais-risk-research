from __future__ import annotations

import argparse
from pathlib import Path

from .own_ship_quality_gate import (
    apply_own_ship_quality_gate,
    build_own_ship_quality_gate_summary,
    load_own_ship_candidate_rows,
    save_own_ship_quality_gate_outputs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply quality gates to ranked own-ship MMSI candidates.")
    parser.add_argument("--input", required=True, help="Path to own_ship_candidates CSV.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for quality gate summary.")
    parser.add_argument("--min-row-count", type=int, default=80)
    parser.add_argument("--min-observed-row-count", type=int, default=40)
    parser.add_argument("--max-interpolation-ratio", type=float, default=0.70)
    parser.add_argument("--min-heading-coverage-ratio", type=float, default=0.50)
    parser.add_argument("--min-movement-ratio", type=float, default=0.30)
    parser.add_argument("--min-active-window-ratio", type=float, default=0.10)
    parser.add_argument("--min-average-nearby-targets", type=float, default=0.50)
    parser.add_argument("--max-segment-break-count", type=int, default=50)
    parser.add_argument("--min-candidate-score", type=float, default=0.20)
    parser.add_argument("--min-recommended-target-count", type=int, default=1)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = load_own_ship_candidate_rows(Path(args.input))
    gated_rows = apply_own_ship_quality_gate(
        rows,
        min_row_count=int(args.min_row_count),
        min_observed_row_count=int(args.min_observed_row_count),
        max_interpolation_ratio=float(args.max_interpolation_ratio),
        min_heading_coverage_ratio=float(args.min_heading_coverage_ratio),
        min_movement_ratio=float(args.min_movement_ratio),
        min_active_window_ratio=float(args.min_active_window_ratio),
        min_average_nearby_targets=float(args.min_average_nearby_targets),
        max_segment_break_count=int(args.max_segment_break_count),
        min_candidate_score=float(args.min_candidate_score),
        min_recommended_target_count=int(args.min_recommended_target_count),
    )
    summary = build_own_ship_quality_gate_summary(
        gated_rows,
        input_path=Path(args.input),
        min_row_count=int(args.min_row_count),
        min_observed_row_count=int(args.min_observed_row_count),
        max_interpolation_ratio=float(args.max_interpolation_ratio),
        min_heading_coverage_ratio=float(args.min_heading_coverage_ratio),
        min_movement_ratio=float(args.min_movement_ratio),
        min_active_window_ratio=float(args.min_active_window_ratio),
        min_average_nearby_targets=float(args.min_average_nearby_targets),
        max_segment_break_count=int(args.max_segment_break_count),
        min_candidate_score=float(args.min_candidate_score),
        min_recommended_target_count=int(args.min_recommended_target_count),
    )
    summary_json_path, summary_md_path, rows_csv_path = save_own_ship_quality_gate_outputs(
        Path(args.output_prefix), summary, gated_rows
    )
    print(f"candidate_count={summary['candidate_count']}")
    print(f"passed_count={summary['passed_count']}")
    print(f"recommended_mmsi={summary.get('recommended_mmsi') or ''}")
    print(f"summary_json={summary_json_path}")
    print(f"summary_md={summary_md_path}")
    print(f"rows_csv={rows_csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
