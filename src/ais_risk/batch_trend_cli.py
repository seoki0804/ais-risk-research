from __future__ import annotations

import argparse

from .batch_trend import build_batch_trend_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build trend report from study batch summaries.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for batch trend report.")
    parser.add_argument(
        "--history-batch-summary-glob",
        default="outputs/study_batch*_summary.json",
        help="Glob pattern for historical batch summary JSON files.",
    )
    parser.add_argument("--current-batch-summary", help="Optional current batch summary JSON path.")
    parser.add_argument("--max-history", type=int, default=8, help="Maximum number of history files to include.")
    parser.add_argument("--moving-average-window", type=int, default=3, help="Window size for moving-average metrics.")
    parser.add_argument(
        "--own-ship-case-f1-std-threshold",
        type=float,
        default=0.10,
        help="Alert threshold for own_ship_case_f1_std.",
    )
    parser.add_argument(
        "--own-ship-case-f1-ci95-width-threshold",
        type=float,
        default=0.20,
        help="Alert threshold for own_ship_case_f1_ci95_width.",
    )
    parser.add_argument(
        "--calibration-ece-threshold",
        type=float,
        default=0.15,
        help="Alert threshold for best calibration ECE.",
    )
    parser.add_argument(
        "--delta-loo-f1-drop-threshold",
        type=float,
        default=0.02,
        help="Worsening threshold for own_ship_loo_f1_mean drop.",
    )
    parser.add_argument(
        "--delta-calibration-ece-rise-threshold",
        type=float,
        default=0.02,
        help="Worsening threshold for best calibration ECE rise.",
    )
    parser.add_argument(
        "--delta-own-ship-case-std-rise-threshold",
        type=float,
        default=0.02,
        help="Worsening threshold for own_ship_case_f1_std rise.",
    )
    parser.add_argument(
        "--delta-own-ship-case-f1-ci95-width-rise-threshold",
        type=float,
        default=0.02,
        help="Worsening threshold for own_ship_case_f1_ci95_width rise.",
    )
    args = parser.parse_args()

    summary = build_batch_trend_report(
        output_prefix=args.output_prefix,
        history_batch_summary_glob=args.history_batch_summary_glob,
        current_batch_summary_path=args.current_batch_summary,
        max_history=int(args.max_history),
        own_ship_case_f1_std_threshold=float(args.own_ship_case_f1_std_threshold),
        own_ship_case_f1_ci95_width_threshold=float(args.own_ship_case_f1_ci95_width_threshold),
        calibration_ece_threshold=float(args.calibration_ece_threshold),
        delta_loo_f1_drop_threshold=float(args.delta_loo_f1_drop_threshold),
        delta_calibration_ece_rise_threshold=float(args.delta_calibration_ece_rise_threshold),
        delta_own_ship_case_std_rise_threshold=float(args.delta_own_ship_case_std_rise_threshold),
        delta_own_ship_case_ci95_width_rise_threshold=float(args.delta_own_ship_case_f1_ci95_width_rise_threshold),
        moving_average_window=int(args.moving_average_window),
    )
    print(f"status={summary['status']}")
    print(f"history_count={summary['history_count']}")
    print(f"dataset_count={summary['dataset_count']}")
    print(f"priority_dataset_count={summary['priority_dataset_count']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"dataset_trends_csv={summary['dataset_trends_csv_path']}")


if __name__ == "__main__":
    main()
