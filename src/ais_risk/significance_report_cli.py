from __future__ import annotations

import argparse

from .significance_report import run_significance_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate significance notes for recommended vs best alternative models.")
    parser.add_argument(
        "--recommendation-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv",
        help="Recommendation CSV from seed sweep.",
    )
    parser.add_argument(
        "--raw-rows-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_raw_rows.csv",
        help="Raw rows CSV from seed sweep.",
    )
    parser.add_argument(
        "--output-prefix",
        default="/Users/seoki/Desktop/research/docs/significance_report_2026-04-04_expanded_models_10seed",
        help="Output prefix path (without extension).",
    )
    parser.add_argument("--bootstrap-samples", type=int, default=5000, help="Bootstrap sample count.")
    parser.add_argument("--bootstrap-seed", type=int, default=42, help="Bootstrap random seed.")
    parser.add_argument("--min-pairs", type=int, default=5, help="Minimum paired seeds for significance report.")
    args = parser.parse_args()

    summary = run_significance_report(
        recommendation_csv_path=args.recommendation_csv,
        raw_rows_csv_path=args.raw_rows_csv,
        output_prefix=args.output_prefix,
        bootstrap_samples=int(args.bootstrap_samples),
        bootstrap_seed=int(args.bootstrap_seed),
        min_pairs=int(args.min_pairs),
    )
    print(f"csv={summary['csv_path']}")
    print(f"md={summary['md_path']}")
    print(f"json={summary['json_path']}")


if __name__ == "__main__":
    main()
