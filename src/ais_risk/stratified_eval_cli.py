from __future__ import annotations

import argparse

from .stratified_eval import run_stratified_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run stratified evaluation by encounter type and distance bins."
    )
    parser.add_argument("--pairwise-dataset", required=True, help="Pairwise dataset CSV path.")
    parser.add_argument("--predictions", required=True, help="Benchmark predictions CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for stratified evaluation.")
    parser.add_argument("--models", help="Optional comma-separated model names.")
    args = parser.parse_args()

    model_names = None
    if args.models:
        model_names = [item.strip() for item in args.models.split(",") if item.strip()]
    summary = run_stratified_evaluation(
        pairwise_dataset_csv_path=args.pairwise_dataset,
        predictions_csv_path=args.predictions,
        output_prefix=args.output_prefix,
        model_names=model_names,
    )
    print(f"status={summary['status']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"strata_metrics_csv={summary['strata_metrics_csv_path']}")


if __name__ == "__main__":
    main()
