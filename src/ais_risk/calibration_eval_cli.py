from __future__ import annotations

import argparse

from .calibration_eval import run_calibration_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run probability calibration evaluation from benchmark predictions.")
    parser.add_argument("--predictions", required=True, help="Benchmark predictions CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for calibration evaluation outputs.")
    parser.add_argument("--models", help="Optional comma-separated model names.")
    parser.add_argument("--num-bins", type=int, default=10, help="Reliability diagram bin count.")
    args = parser.parse_args()

    model_names = None
    if args.models:
        model_names = [item.strip() for item in args.models.split(",") if item.strip()]

    summary = run_calibration_evaluation(
        predictions_csv_path=args.predictions,
        output_prefix=args.output_prefix,
        model_names=model_names,
        num_bins=int(args.num_bins),
    )
    print(f"status={summary['status']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"calibration_bins_csv={summary['calibration_bins_csv_path']}")


if __name__ == "__main__":
    main()
