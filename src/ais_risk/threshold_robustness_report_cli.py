from __future__ import annotations

import argparse

from .threshold_robustness_report import run_threshold_robustness_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate threshold robustness report from seed-sweep recommendations.")
    parser.add_argument(
        "--recommendation-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv",
        help="Recommendation CSV from seed sweep.",
    )
    parser.add_argument(
        "--run-manifest-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_run_manifest.csv",
        help="Run manifest CSV from seed sweep.",
    )
    parser.add_argument(
        "--output-prefix",
        default="/Users/seoki/Desktop/research/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed",
        help="Output prefix path (without extension).",
    )
    parser.add_argument(
        "--cost-profiles",
        default="balanced:1:1,fn_heavy:1:3,fn_very_heavy:1:5,fp_heavy:3:1",
        help="Comma-separated cost profiles in name:fp_cost:fn_cost format.",
    )
    args = parser.parse_args()

    summary = run_threshold_robustness_report(
        recommendation_csv_path=args.recommendation_csv,
        run_manifest_csv_path=args.run_manifest_csv,
        output_prefix=args.output_prefix,
        cost_profiles=args.cost_profiles,
    )
    print(f"detail_csv={summary['detail_csv_path']}")
    print(f"summary_csv={summary['summary_csv_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_json={summary['summary_json_path']}")


if __name__ == "__main__":
    main()
