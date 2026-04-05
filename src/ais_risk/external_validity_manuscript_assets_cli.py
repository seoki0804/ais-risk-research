from __future__ import annotations

import argparse

from .external_validity_manuscript_assets import _parse_region_json_map, run_external_validity_manuscript_assets


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate manuscript-facing external-validity supplement table and 3-region scenario panels."
    )
    parser.add_argument(
        "--transfer-gap-detail-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics_detail.csv",
        help="Transfer-gap diagnostics detail CSV path.",
    )
    parser.add_argument(
        "--recommendation-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv",
        help="Recommendation CSV path.",
    )
    parser.add_argument(
        "--reliability-region-summary-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_reliability_report_10seed/reliability_recommended_region_summary.csv",
        help="Reliability region summary CSV path.",
    )
    parser.add_argument(
        "--taxonomy-region-summary-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_error_taxonomy_10seed/error_taxonomy_region_summary.csv",
        help="Taxonomy region summary CSV path.",
    )
    parser.add_argument(
        "--contour-summary-json-by-region",
        default=(
            "houston:/Users/seoki/Desktop/research/outputs/2026-04-05_uncertainty_contour_panel_10seed/houston_report_summary.json,"
            "nola:/Users/seoki/Desktop/research/outputs/2026-04-05_uncertainty_contour_panel_10seed/nola_report_summary.json,"
            "seattle:/Users/seoki/Desktop/research/outputs/2026-04-05_uncertainty_contour_panel_10seed/seattle_report_summary.json"
        ),
        help="Comma-separated mapping region:path to contour report summary JSON.",
    )
    parser.add_argument(
        "--output-prefix",
        default="/Users/seoki/Desktop/research/docs/external_validity_manuscript_assets_2026-04-05_10seed",
        help="Output prefix path (without extension).",
    )
    args = parser.parse_args()

    summary = run_external_validity_manuscript_assets(
        transfer_gap_detail_csv_path=args.transfer_gap_detail_csv,
        recommendation_csv_path=args.recommendation_csv,
        reliability_region_summary_csv_path=args.reliability_region_summary_csv,
        taxonomy_region_summary_csv_path=args.taxonomy_region_summary_csv,
        contour_report_summary_json_by_region=_parse_region_json_map(args.contour_summary_json_by_region),
        output_prefix=args.output_prefix,
    )

    print(f"summary_json={summary['summary_json_path']}")
    print(f"integration_note_md={summary['integration_note_md_path']}")
    print(f"transfer_table_md={summary['transfer_uncertainty_table_md_path']}")
    print(f"scenario_panels_md={summary['scenario_panels_md_path']}")


if __name__ == "__main__":
    main()
