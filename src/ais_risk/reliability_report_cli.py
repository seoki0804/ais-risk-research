from __future__ import annotations

import argparse

from .reliability_report import run_reliability_report_for_recommended_models


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reliability report/figures for region-recommended models.")
    parser.add_argument(
        "--recommendation-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_recommendation.csv",
        help="Recommendation CSV from seed sweep.",
    )
    parser.add_argument(
        "--run-manifest-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_expanded/all_models_seed_sweep_run_manifest.csv",
        help="Run manifest CSV from seed sweep.",
    )
    parser.add_argument("--output-root", required=True, help="Output directory for reliability artifacts.")
    parser.add_argument("--num-bins", type=int, default=10, help="Calibration bin count.")
    args = parser.parse_args()

    summary = run_reliability_report_for_recommended_models(
        recommendation_csv_path=args.recommendation_csv,
        run_manifest_csv_path=args.run_manifest_csv,
        output_root=args.output_root,
        num_bins=int(args.num_bins),
    )
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"region_summary_csv={summary['region_summary_csv_path']}")
    print(f"region_bins_csv={summary['region_bins_csv_path']}")


if __name__ == "__main__":
    main()
