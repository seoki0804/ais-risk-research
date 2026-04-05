from __future__ import annotations

import argparse

from .validation_leaderboard import build_validation_leaderboard


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build cumulative validation leaderboard from study summary files."
    )
    parser.add_argument(
        "--study-summary-glob",
        default="outputs/**/*_study_summary.json",
        help="Glob pattern for study summary JSON files.",
    )
    parser.add_argument("--output-csv", default="outputs/validation_leaderboard.csv", help="Output CSV path.")
    parser.add_argument("--output-md", default="outputs/validation_leaderboard.md", help="Output markdown path.")
    parser.add_argument(
        "--sort-by",
        default="own_ship_loo_f1_mean",
        choices=[
            "own_ship_loo_f1_mean",
            "own_ship_f1",
            "timestamp_f1",
            "calibration_best_ece",
            "calibration_best_brier",
            "calibration_own_ship_loo_model_ece",
            "calibration_own_ship_loo_model_brier",
            "own_ship_case_f1_mean",
            "own_ship_case_f1_std",
            "own_ship_case_f1_ci95_width",
            "own_ship_case_f1_std_repeat_mean",
            "own_ship_case_f1_std_repeat_max",
            "own_ship_case_auroc_mean",
        ],
        help="Metric key for sorting leaderboard.",
    )
    parser.add_argument("--ascending", action="store_true", help="Sort ascending (default descending).")
    parser.add_argument("--allow-duplicates", action="store_true", help="Do not deduplicate by dataset_id.")
    parser.add_argument(
        "--own-ship-case-f1-std-threshold",
        type=float,
        default=0.10,
        help="Alert threshold for own_ship_case_f1_std (set negative value to disable).",
    )
    parser.add_argument(
        "--calibration-best-ece-threshold",
        type=float,
        default=0.15,
        help="Alert threshold for calibration_best_ece (set negative value to disable).",
    )
    parser.add_argument(
        "--own-ship-case-f1-ci95-width-threshold",
        type=float,
        default=0.20,
        help="Alert threshold for own_ship_case_f1_ci95_width (set negative value to disable).",
    )
    args = parser.parse_args()

    summary = build_validation_leaderboard(
        study_summary_glob=args.study_summary_glob,
        output_csv_path=args.output_csv,
        output_md_path=args.output_md,
        sort_by=args.sort_by,
        descending=not bool(args.ascending),
        deduplicate_dataset_id=not bool(args.allow_duplicates),
        own_ship_case_f1_std_threshold=float(args.own_ship_case_f1_std_threshold),
        calibration_best_ece_threshold=float(args.calibration_best_ece_threshold),
        own_ship_case_f1_ci95_width_threshold=float(args.own_ship_case_f1_ci95_width_threshold),
    )
    print(f"status={summary['status']}")
    print(f"row_count={summary['row_count']}")
    print(f"output_csv={summary['output_csv_path']}")
    print(f"output_md={summary['output_md_path']}")


if __name__ == "__main__":
    main()
