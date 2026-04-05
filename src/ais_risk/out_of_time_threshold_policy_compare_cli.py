from __future__ import annotations

import argparse

from .out_of_time_threshold_policy_compare import run_out_of_time_threshold_policy_compare


def _parse_str_list(raw: str) -> list[str]:
    return [token.strip() for token in str(raw).split(",") if token.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare out-of-time threshold policies for recommended models "
            "(val-tuned vs fixed-baseline threshold, with optional oracle upper bound)."
        )
    )
    parser.add_argument("--recommendation-csv", required=True, help="Recommendation CSV path.")
    parser.add_argument("--baseline-leaderboard-csv", required=True, help="Baseline leaderboard CSV path.")
    parser.add_argument("--out-of-time-output-root", required=True, help="Out-of-time evaluation output root.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix path (without extension).")
    parser.add_argument(
        "--dataset-prefixes",
        default="",
        help="Optional comma-separated dataset prefixes (e.g., 'houston,nola').",
    )
    parser.add_argument("--threshold-grid-step", type=float, default=0.01, help="Threshold sweep step.")
    parser.add_argument("--max-out-of-time-ece", type=float, default=0.10, help="ECE gate for out-of-time metrics.")
    parser.add_argument(
        "--min-out-of-time-delta-f1",
        type=float,
        default=-0.05,
        help="Temporal gate threshold for out-of-time ΔF1.",
    )
    parser.add_argument(
        "--max-in-time-regression-from-best-f1",
        type=float,
        default=0.02,
        help="Max allowed in-time F1 regression from best model in dataset.",
    )
    parser.add_argument(
        "--disable-oracle-policy",
        action="store_true",
        help="Exclude oracle threshold policy (upper-bound mode).",
    )
    args = parser.parse_args()

    summary = run_out_of_time_threshold_policy_compare(
        recommendation_csv_path=args.recommendation_csv,
        baseline_leaderboard_csv_path=args.baseline_leaderboard_csv,
        out_of_time_output_root=args.out_of_time_output_root,
        output_prefix=args.output_prefix,
        dataset_prefix_filters=_parse_str_list(args.dataset_prefixes),
        threshold_grid_step=float(args.threshold_grid_step),
        max_out_of_time_ece=float(args.max_out_of_time_ece),
        min_out_of_time_delta_f1=float(args.min_out_of_time_delta_f1),
        max_in_time_regression_from_best_f1=float(args.max_in_time_regression_from_best_f1),
        include_oracle_policy=not bool(args.disable_oracle_policy),
    )

    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"detail_csv={summary['detail_csv_path']}")
    print(f"policy_summary_csv={summary['policy_summary_csv_path']}")


if __name__ == "__main__":
    main()
