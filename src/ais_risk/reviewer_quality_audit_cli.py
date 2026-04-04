from __future__ import annotations

import argparse

from .reviewer_quality_audit import run_reviewer_quality_audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reviewer-quality audit from final benchmark artifacts.")
    parser.add_argument(
        "--recommendation-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv",
        help="Recommendation CSV path.",
    )
    parser.add_argument(
        "--aggregate-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv",
        help="Aggregate seed-sweep CSV path.",
    )
    parser.add_argument(
        "--winner-summary-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_winner_summary.csv",
        help="Winner summary CSV path.",
    )
    parser.add_argument(
        "--out-of-time-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_out_of_time_check_10seed/out_of_time_recommendation_check.csv",
        help="Out-of-time check CSV path.",
    )
    parser.add_argument(
        "--transfer-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.csv",
        help="Transfer check CSV path.",
    )
    parser.add_argument(
        "--reliability-region-summary-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report_10seed/reliability_recommended_region_summary.csv",
        help="Reliability region summary CSV path.",
    )
    parser.add_argument(
        "--taxonomy-region-summary-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_error_taxonomy_10seed/error_taxonomy_region_summary.csv",
        help="Error taxonomy region summary CSV path.",
    )
    parser.add_argument(
        "--output-prefix",
        default="/Users/seoki/Desktop/research/docs/reviewer_quality_audit_2026-04-04_expanded_models_10seed",
        help="Output prefix path (without extension).",
    )
    args = parser.parse_args()

    summary = run_reviewer_quality_audit(
        recommendation_csv_path=args.recommendation_csv,
        aggregate_csv_path=args.aggregate_csv,
        winner_summary_csv_path=args.winner_summary_csv,
        out_of_time_csv_path=args.out_of_time_csv,
        transfer_csv_path=args.transfer_csv,
        reliability_region_summary_csv_path=args.reliability_region_summary_csv,
        taxonomy_region_summary_csv_path=args.taxonomy_region_summary_csv,
        output_prefix=args.output_prefix,
    )
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")


if __name__ == "__main__":
    main()
