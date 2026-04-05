from __future__ import annotations

import argparse

from .manuscript_freeze_packet import run_manuscript_freeze_packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate manuscript-ready freeze claims and operator-profile locks.")
    parser.add_argument(
        "--unseen-area-summary-csv",
        default="/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_summary.csv",
        help="True unseen-area summary CSV path.",
    )
    parser.add_argument(
        "--threshold-robustness-summary-csv",
        default="/Users/seoki/Desktop/research/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed_summary.csv",
        help="Threshold robustness summary CSV path.",
    )
    parser.add_argument(
        "--significance-csv",
        default="/Users/seoki/Desktop/research/docs/significance_report_2026-04-04_expanded_models_10seed.csv",
        help="Significance summary CSV path.",
    )
    parser.add_argument(
        "--output-prefix",
        default="/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed",
        help="Output prefix path (without extension).",
    )
    parser.add_argument(
        "--recommendation-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv",
        help="Optional recommendation CSV path for model-claim hygiene freeze.",
    )
    parser.add_argument(
        "--aggregate-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv",
        help="Optional aggregate seed-sweep CSV path for model-claim hygiene freeze.",
    )
    parser.add_argument(
        "--max-ece",
        type=float,
        default=0.10,
        help="Calibration gate threshold used for model-claim hygiene freeze.",
    )
    parser.add_argument(
        "--max-f1-std",
        type=float,
        default=0.03,
        help="Seed-variance gate threshold used for model-claim hygiene freeze.",
    )
    parser.add_argument(
        "--min-test-positive-support",
        type=int,
        default=10,
        help="Minimum positive support policy threshold used in frozen claim text.",
    )
    args = parser.parse_args()

    summary = run_manuscript_freeze_packet(
        unseen_area_summary_csv_path=args.unseen_area_summary_csv,
        threshold_robustness_summary_csv_path=args.threshold_robustness_summary_csv,
        significance_csv_path=args.significance_csv,
        output_prefix=args.output_prefix,
        min_test_positive_support=int(args.min_test_positive_support),
        recommendation_csv_path=args.recommendation_csv or None,
        aggregate_csv_path=args.aggregate_csv or None,
        max_ece=float(args.max_ece),
        max_f1_std=float(args.max_f1_std),
    )
    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"operator_profile_lock_csv={summary['operator_profile_lock_csv_path']}")
    if summary.get("model_claim_scope_csv_path"):
        print(f"model_claim_scope_csv={summary['model_claim_scope_csv_path']}")


if __name__ == "__main__":
    main()
