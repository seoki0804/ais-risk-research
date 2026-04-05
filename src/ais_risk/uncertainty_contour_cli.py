from __future__ import annotations

import argparse

from .prediction_grid_projection import run_prediction_grid_projection
from .uncertainty_band import run_uncertainty_band
from .uncertainty_contour_report import build_uncertainty_contour_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run uncertainty band, prediction-to-grid projection, and contour report in one pass."
    )
    parser.add_argument("--predictions", required=True, help="Benchmark predictions CSV path.")
    parser.add_argument("--pairwise", required=True, help="Pairwise dataset CSV path.")
    parser.add_argument("--calibration-bins", required=True, help="Calibration bins CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for chained uncertainty contour outputs.")
    parser.add_argument("--config", default="configs/base.toml", help="Project TOML config path.")
    parser.add_argument("--models", help="Optional comma-separated model names.")
    parser.add_argument("--confidence-level", type=float, default=0.95, help="Confidence level for Wilson interval bands.")
    parser.add_argument(
        "--case-limit",
        type=int,
        default=5,
        help="Number of top-ranked cases to keep projected cell grids for.",
    )
    parser.add_argument(
        "--case-rank-metric",
        default="max_risk_mean",
        choices=["max_risk_mean", "max_cell_band_span", "target_count"],
        help="Metric used to rank cases before selecting contour candidates.",
    )
    parser.add_argument("--case-id", help="Optional explicit case_id for the final contour figure.")
    args = parser.parse_args()

    model_names = None
    if args.models:
        model_names = [item.strip() for item in args.models.split(",") if item.strip()]

    output_prefix = str(args.output_prefix)
    band_prefix = f"{output_prefix}_band"
    projection_prefix = f"{output_prefix}_projection"
    report_prefix = f"{output_prefix}_report"

    band_summary = run_uncertainty_band(
        predictions_csv_path=args.predictions,
        calibration_bins_csv_path=args.calibration_bins,
        output_prefix=band_prefix,
        model_names=model_names,
        confidence_level=float(args.confidence_level),
    )
    projection_summary = run_prediction_grid_projection(
        pairwise_csv_path=args.pairwise,
        sample_bands_csv_path=band_summary["sample_bands_csv_path"],
        output_prefix=projection_prefix,
        config_path=args.config,
        model_names=model_names,
        case_limit=args.case_limit,
        case_rank_metric=args.case_rank_metric,
    )
    report_summary = build_uncertainty_contour_report(
        projected_cells_csv_path=projection_summary["projected_cells_csv_path"],
        case_summary_csv_path=projection_summary["case_summary_csv_path"],
        output_prefix=report_prefix,
        config_path=args.config,
        case_id=args.case_id,
    )

    print(f"status={report_summary['status']}")
    print(f"band_summary_json={band_summary['summary_json_path']}")
    print(f"projection_summary_json={projection_summary['summary_json_path']}")
    print(f"report_summary_json={report_summary['summary_json_path']}")
    print(f"figure_svg={report_summary['figure_svg_path']}")
    print(f"case_id={report_summary['case_id']}")


if __name__ == "__main__":
    main()
