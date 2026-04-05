from __future__ import annotations

import argparse

from .uncertainty_band import run_uncertainty_band


def main() -> None:
    parser = argparse.ArgumentParser(description="Build sample-level uncertainty bands from benchmark predictions and calibration bins.")
    parser.add_argument("--predictions", required=True, help="Benchmark predictions CSV path.")
    parser.add_argument("--calibration-bins", required=True, help="Calibration bins CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for uncertainty band outputs.")
    parser.add_argument("--models", help="Optional comma-separated model names.")
    parser.add_argument("--confidence-level", type=float, default=0.95, help="Confidence level for Wilson interval bands.")
    args = parser.parse_args()

    model_names = None
    if args.models:
        model_names = [item.strip() for item in args.models.split(",") if item.strip()]

    summary = run_uncertainty_band(
        predictions_csv_path=args.predictions,
        calibration_bins_csv_path=args.calibration_bins,
        output_prefix=args.output_prefix,
        model_names=model_names,
        confidence_level=float(args.confidence_level),
    )
    print(f"status={summary['status']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"sample_bands_csv={summary['sample_bands_csv_path']}")


if __name__ == "__main__":
    main()
