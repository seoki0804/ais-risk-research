from __future__ import annotations

import argparse

from .calibration_eval import run_calibration_evaluation
from .split_conformal_interval import run_split_conformal_interval
from .uncertainty_band import run_uncertainty_band
from .uncertainty_interval_compare import run_uncertainty_interval_compare


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Wilson-bin and split conformal uncertainty baselines on the same target predictions."
    )
    parser.add_argument("--calibration-predictions", required=True, help="Source validation predictions CSV path.")
    parser.add_argument("--target-predictions", required=True, help="Target predictions CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for uncertainty rigor comparison.")
    parser.add_argument("--models", help="Optional comma-separated model names.")
    parser.add_argument("--confidence-level", type=float, default=0.95, help="Confidence level for Wilson intervals.")
    args = parser.parse_args()

    model_names = None
    if args.models:
        model_names = [item.strip() for item in args.models.split(",") if item.strip()]

    output_prefix = str(args.output_prefix)
    calibration_prefix = f"{output_prefix}_val_calibration"
    wilson_prefix = f"{output_prefix}_wilson"
    conformal_prefix = f"{output_prefix}_split_conformal"
    compare_prefix = f"{output_prefix}_compare"

    calibration_summary = run_calibration_evaluation(
        predictions_csv_path=args.calibration_predictions,
        output_prefix=calibration_prefix,
        model_names=model_names,
        num_bins=10,
    )
    wilson_summary = run_uncertainty_band(
        predictions_csv_path=args.target_predictions,
        calibration_bins_csv_path=calibration_summary["calibration_bins_csv_path"],
        output_prefix=wilson_prefix,
        model_names=model_names,
        confidence_level=float(args.confidence_level),
    )
    conformal_summary = run_split_conformal_interval(
        calibration_predictions_csv_path=args.calibration_predictions,
        target_predictions_csv_path=args.target_predictions,
        output_prefix=conformal_prefix,
        model_names=model_names,
        miscoverage_alpha=(1.0 - float(args.confidence_level)),
    )
    compare_summary = run_uncertainty_interval_compare(
        baseline_a_csv_path=wilson_summary["sample_bands_csv_path"],
        baseline_b_csv_path=conformal_summary["interval_csv_path"],
        output_prefix=compare_prefix,
        baseline_a_name="wilson_bin",
        baseline_b_name="split_conformal",
    )

    print("status=completed")
    print(f"calibration_summary_json={calibration_summary['summary_json_path']}")
    print(f"wilson_summary_json={wilson_summary['summary_json_path']}")
    print(f"conformal_summary_json={conformal_summary['summary_json_path']}")
    print(f"compare_summary_json={compare_summary['summary_json_path']}")


if __name__ == "__main__":
    main()
