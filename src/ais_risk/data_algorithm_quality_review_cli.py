from __future__ import annotations

import argparse

from .data_algorithm_quality_review import run_data_algorithm_quality_review


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Review data sufficiency, overfit/variance risk, and algorithm stability "
            "for recommended AIS models with optional governance-bridge projection."
        )
    )
    parser.add_argument("--recommendation-csv", required=True, help="Recommendation CSV path.")
    parser.add_argument("--aggregate-csv", required=True, help="Seed sweep aggregate CSV path.")
    parser.add_argument("--out-of-time-csv", required=True, help="Out-of-time recommendation-check CSV path.")
    parser.add_argument("--transfer-csv", required=True, help="Transfer recommendation-check CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix path (without extension).")
    parser.add_argument(
        "--out-of-time-threshold-policy-compare-json",
        default="",
        help="Optional out-of-time threshold-policy compare JSON path.",
    )
    parser.add_argument(
        "--multisource-transfer-governance-bridge-json",
        default="",
        help="Optional multi-source transfer governance bridge JSON path.",
    )
    parser.add_argument(
        "--transfer-override-seed-stress-test-json",
        default="",
        help="Optional transfer override seed-stress test JSON path.",
    )
    parser.add_argument(
        "--manuscript-freeze-packet-json",
        default="",
        help="Optional manuscript freeze packet JSON path used for DQ-5 closure evidence.",
    )
    parser.add_argument(
        "--min-positive-support",
        type=int,
        default=30,
        help="Minimum positive support required for a dataset-level support pass.",
    )
    parser.add_argument("--max-ece", type=float, default=0.10, help="Maximum acceptable ECE.")
    parser.add_argument("--max-f1-std", type=float, default=0.03, help="Maximum acceptable seed F1 std.")
    parser.add_argument(
        "--min-out-of-time-delta-f1",
        type=float,
        default=-0.05,
        help="Minimum acceptable out-of-time delta F1.",
    )
    parser.add_argument(
        "--max-negative-transfer-pairs",
        type=int,
        default=1,
        help="Maximum allowed negative transfer pairs for a source region.",
    )
    args = parser.parse_args()

    summary = run_data_algorithm_quality_review(
        recommendation_csv_path=args.recommendation_csv,
        aggregate_csv_path=args.aggregate_csv,
        out_of_time_csv_path=args.out_of_time_csv,
        transfer_csv_path=args.transfer_csv,
        output_prefix=args.output_prefix,
        out_of_time_threshold_policy_compare_json_path=(
            args.out_of_time_threshold_policy_compare_json or None
        ),
        multisource_transfer_governance_bridge_json_path=(
            args.multisource_transfer_governance_bridge_json or None
        ),
        transfer_override_seed_stress_test_json_path=(
            args.transfer_override_seed_stress_test_json or None
        ),
        manuscript_freeze_packet_json_path=(args.manuscript_freeze_packet_json or None),
        min_positive_support=int(args.min_positive_support),
        max_ece=float(args.max_ece),
        max_f1_std=float(args.max_f1_std),
        min_out_of_time_delta_f1=float(args.min_out_of_time_delta_f1),
        max_negative_transfer_pairs=int(args.max_negative_transfer_pairs),
    )

    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"dataset_scorecard_csv={summary['dataset_scorecard_csv_path']}")
    print(f"high_risk_models_csv={summary['high_risk_models_csv_path']}")
    print(f"todo_csv={summary['todo_csv_path']}")


if __name__ == "__main__":
    main()
