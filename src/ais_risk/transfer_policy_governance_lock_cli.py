from __future__ import annotations

import argparse

from .transfer_policy_governance_lock import run_transfer_policy_governance_lock


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lock split governance for in-time recommendation path and transfer-only override path."
    )
    parser.add_argument("--recommendation-csv", required=True, help="Recommendation CSV path.")
    parser.add_argument("--transfer-check-csv", required=True, help="Transfer check CSV path.")
    parser.add_argument(
        "--out-of-time-threshold-policy-compare-json",
        required=True,
        help="Out-of-time threshold-policy compare summary JSON path.",
    )
    parser.add_argument(
        "--transfer-calibration-probe-detail-csv",
        required=True,
        help="Transfer calibration probe detail CSV path.",
    )
    parser.add_argument("--output-prefix", required=True, help="Output prefix path (without extension).")
    parser.add_argument(
        "--source-region-for-transfer-override",
        default="houston",
        help="Source region to apply transfer override policy.",
    )
    parser.add_argument(
        "--metric-mode",
        default="fixed",
        choices=["fixed", "retuned"],
        help="Transfer metric mode used for override projection.",
    )
    parser.add_argument("--max-target-ece", type=float, default=0.10, help="Target ECE gate.")
    parser.add_argument("--max-negative-pairs-allowed", type=int, default=1, help="Negative pair budget.")
    parser.add_argument(
        "--required-out-of-time-policy",
        default="fixed_baseline_threshold",
        help="Out-of-time threshold policy required for governance lock.",
    )
    parser.add_argument(
        "--override-model-name",
        default="",
        help="Optional explicit model name for transfer override candidate.",
    )
    parser.add_argument(
        "--override-method",
        default="",
        help="Optional explicit calibration method for transfer override candidate.",
    )
    args = parser.parse_args()

    summary = run_transfer_policy_governance_lock(
        recommendation_csv_path=args.recommendation_csv,
        transfer_check_csv_path=args.transfer_check_csv,
        out_of_time_threshold_policy_compare_json_path=args.out_of_time_threshold_policy_compare_json,
        transfer_calibration_probe_detail_csv_path=args.transfer_calibration_probe_detail_csv,
        output_prefix=args.output_prefix,
        source_region_for_transfer_override=args.source_region_for_transfer_override,
        metric_mode=args.metric_mode,
        max_target_ece=float(args.max_target_ece),
        max_negative_pairs_allowed=int(args.max_negative_pairs_allowed),
        required_out_of_time_policy=args.required_out_of_time_policy,
        override_model_name=args.override_model_name,
        override_method=args.override_method,
    )

    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"policy_lock_csv={summary['policy_lock_csv_path']}")
    print(f"projected_transfer_check_csv={summary['projected_transfer_check_csv_path']}")
    print(f"candidate_summary_csv={summary['candidate_summary_csv_path']}")


if __name__ == "__main__":
    main()
