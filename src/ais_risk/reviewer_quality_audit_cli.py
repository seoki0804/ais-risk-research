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
    parser.add_argument(
        "--significance-csv",
        default="/Users/seoki/Desktop/research/docs/significance_report_2026-04-04_expanded_models_10seed.csv",
        help="Optional significance summary CSV path.",
    )
    parser.add_argument(
        "--threshold-robustness-summary-csv",
        default="/Users/seoki/Desktop/research/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed_summary.csv",
        help="Optional threshold-robustness summary CSV path.",
    )
    parser.add_argument(
        "--unseen-area-summary-csv",
        default="/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed_summary.csv",
        help="Optional true unseen-area summary CSV path.",
    )
    parser.add_argument(
        "--manuscript-freeze-packet-json",
        default="/Users/seoki/Desktop/research/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json",
        help="Optional manuscript freeze packet JSON path.",
    )
    parser.add_argument(
        "--transfer-model-scan-json",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_model_scan_10seed/houston_transfer_model_scan.json",
        help="Optional transfer-model scan JSON path.",
    )
    parser.add_argument(
        "--transfer-gap-summary-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics_summary.csv",
        help="Optional transfer-gap diagnostics summary CSV path.",
    )
    parser.add_argument(
        "--temporal-robust-summary-json",
        default="/Users/seoki/Desktop/research/docs/temporal_robust_recommendation_2026-04-05_houston_10seed.json",
        help="Optional temporal-robust recommendation summary JSON path.",
    )
    parser.add_argument(
        "--out-of-time-threshold-policy-compare-json",
        default="/Users/seoki/Desktop/research/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed.json",
        help="Optional out-of-time threshold policy compare summary JSON path.",
    )
    parser.add_argument(
        "--transfer-policy-governance-lock-json",
        default="/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed.json",
        help="Optional transfer-policy governance lock summary JSON path.",
    )
    parser.add_argument(
        "--transfer-policy-compare-json",
        default="/Users/seoki/Desktop/research/docs/houston_transfer_policy_compare_2026-04-05_10seed.json",
        help="Optional transfer-policy compare summary JSON path.",
    )
    parser.add_argument(
        "--transfer-policy-compare-all-models-json",
        default="/Users/seoki/Desktop/research/docs/houston_transfer_policy_compare_all_models_2026-04-05_10seed.json",
        help="Optional transfer-policy compare(all-models) summary JSON path.",
    )
    parser.add_argument(
        "--transfer-calibration-probe-json",
        default="/Users/seoki/Desktop/research/docs/houston_transfer_calibration_probe_2026-04-05_10seed.json",
        help="Optional transfer-calibration probe summary JSON path.",
    )
    parser.add_argument(
        "--external-validity-manuscript-assets-json",
        default="/Users/seoki/Desktop/research/docs/external_validity_manuscript_assets_2026-04-05_10seed.json",
        help="Optional manuscript-assets summary JSON path.",
    )
    parser.add_argument(
        "--multisource-transfer-model-scan-summary-json",
        default="/Users/seoki/Desktop/research/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed.json",
        help="Optional multi-source transfer-model-scan summary JSON path.",
    )
    parser.add_argument(
        "--multisource-transfer-governance-bridge-json",
        default="/Users/seoki/Desktop/research/docs/multisource_transfer_governance_bridge_2026-04-05_10seed.json",
        help="Optional multi-source transfer governance-bridge summary JSON path.",
    )
    parser.add_argument(
        "--data-algorithm-quality-review-json",
        default="/Users/seoki/Desktop/research/docs/data_algorithm_quality_review_2026-04-05_10seed.json",
        help="Optional data/algorithm quality-review summary JSON path.",
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
        significance_csv_path=args.significance_csv,
        threshold_robustness_summary_csv_path=args.threshold_robustness_summary_csv,
        unseen_area_summary_csv_path=args.unseen_area_summary_csv,
        manuscript_freeze_packet_json_path=args.manuscript_freeze_packet_json,
        transfer_model_scan_json_path=args.transfer_model_scan_json,
        transfer_gap_summary_csv_path=args.transfer_gap_summary_csv,
        temporal_robust_summary_json_path=args.temporal_robust_summary_json,
        out_of_time_threshold_policy_compare_json_path=args.out_of_time_threshold_policy_compare_json,
        transfer_policy_governance_lock_json_path=args.transfer_policy_governance_lock_json,
        transfer_policy_compare_json_path=args.transfer_policy_compare_json,
        transfer_policy_compare_all_models_json_path=args.transfer_policy_compare_all_models_json,
        transfer_calibration_probe_json_path=args.transfer_calibration_probe_json,
        external_validity_manuscript_assets_json_path=args.external_validity_manuscript_assets_json,
        multisource_transfer_model_scan_summary_json_path=args.multisource_transfer_model_scan_summary_json,
        multisource_transfer_governance_bridge_json_path=args.multisource_transfer_governance_bridge_json,
        data_algorithm_quality_review_json_path=args.data_algorithm_quality_review_json,
    )
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")


if __name__ == "__main__":
    main()
