from __future__ import annotations

import argparse

from .error_analysis import run_benchmark_error_analysis


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze benchmark prediction errors (FP/FN) and export ranked error cases."
    )
    parser.add_argument("--predictions", required=True, help="Benchmark test predictions CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for error analysis files.")
    parser.add_argument("--models", help="Optional comma-separated model names. If omitted, auto-detect from CSV.")
    parser.add_argument("--top-k-each", type=int, default=20, help="Top-K FP and top-K FN rows per model.")
    args = parser.parse_args()

    model_names = None
    if args.models:
        model_names = [item.strip() for item in args.models.split(",") if item.strip()]
    summary = run_benchmark_error_analysis(
        predictions_csv_path=args.predictions,
        output_prefix=args.output_prefix,
        model_names=model_names,
        top_k_each=int(args.top_k_each),
    )
    print(f"status={summary['status']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"error_cases_csv={summary['error_cases_csv_path']}")
    print(f"selected_error_rows={summary['selected_error_row_count']}")


if __name__ == "__main__":
    main()
