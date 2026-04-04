from __future__ import annotations

import argparse

from .unseen_area_evidence_report import run_unseen_area_evidence_report


def _split_csv_paths(value: str) -> list[str]:
    return [item.strip() for item in str(value).split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize true unseen-area and cross-year transfer evidence.")
    parser.add_argument(
        "--true-area-pairwise-summaries",
        default=(
            "/Users/seoki/Desktop/research/outputs/2026-03-17_r5_true_new_area_ny_nj_pooled/ny_nj_pooled_pairwise_summary.json,"
            "/Users/seoki/Desktop/research/outputs/2026-03-17_r13_true_new_area_la_long_beach_pooled/la_long_beach_pooled_pairwise_summary.json,"
            "/Users/seoki/Desktop/research/outputs/2026-03-17_r24_true_new_area_savannah_pooled/savannah_pooled_pairwise_summary.json,"
            "/Users/seoki/Desktop/research/outputs/2026-03-17_r35_cross_year_2024_ny_nj_pooled/ny_nj_2024_pooled_pairwise_summary.json"
        ),
        help="Comma-separated pooled true-area pairwise summary JSON paths.",
    )
    parser.add_argument(
        "--transfer-summaries",
        default=(
            "/Users/seoki/Desktop/research/outputs/2026-03-17_r36_cross_year_ny_nj_transfer/ny_nj_2023_to_2024_transfer_summary.json,"
            "/Users/seoki/Desktop/research/outputs/2026-03-17_r36_cross_year_ny_nj_transfer/ny_nj_2024_to_2023_transfer_summary.json,"
            "/Users/seoki/Desktop/research/outputs/2026-03-17_r59_cross_year_seattle_transfer/seattle_2023_to_2024_transfer_summary.json,"
            "/Users/seoki/Desktop/research/outputs/2026-03-17_r59_cross_year_seattle_transfer/seattle_2024_to_2023_transfer_summary.json,"
            "/Users/seoki/Desktop/research/outputs/2026-04-05_r2_cross_year_la_long_beach_transfer/la_long_beach_2023_to_2024_transfer_summary.json,"
            "/Users/seoki/Desktop/research/outputs/2026-04-05_r2_cross_year_la_long_beach_transfer/la_long_beach_2024_to_2023_transfer_summary.json"
        ),
        help="Comma-separated cross-year transfer summary JSON paths.",
    )
    parser.add_argument(
        "--output-prefix",
        default="/Users/seoki/Desktop/research/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed",
        help="Output prefix path (without extension).",
    )
    parser.add_argument(
        "--min-test-positive-support",
        type=int,
        default=10,
        help="Minimum test positives to mark split support as acceptable.",
    )
    parser.add_argument("--target-model", default="hgbt", help="Primary model label in summary JSON payload.")
    parser.add_argument("--comparator-model", default="logreg", help="Comparator model label in summary JSON payload.")
    args = parser.parse_args()

    summary = run_unseen_area_evidence_report(
        true_area_pairwise_summary_json_paths=_split_csv_paths(args.true_area_pairwise_summaries),
        transfer_summary_json_paths=_split_csv_paths(args.transfer_summaries),
        output_prefix=args.output_prefix,
        min_test_positive_support=int(args.min_test_positive_support),
        target_model=args.target_model,
        comparator_model=args.comparator_model,
    )
    print(f"detail_csv={summary['detail_csv_path']}")
    print(f"summary_csv={summary['summary_csv_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_json={summary['summary_json_path']}")


if __name__ == "__main__":
    main()
