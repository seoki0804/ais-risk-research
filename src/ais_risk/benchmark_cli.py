from __future__ import annotations

import argparse

from .benchmark import run_pairwise_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run train/validation/test benchmarks on a pairwise AIS learning dataset."
    )
    parser.add_argument("--input", required=True, help="Pairwise learning dataset CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for benchmark summary and predictions.")
    parser.add_argument(
        "--models",
        default="rule_score,logreg,hgbt",
        help="Comma-separated model names. Supported: rule_score,logreg,hgbt,random_forest,extra_trees,torch_mlp",
    )
    parser.add_argument("--train-fraction", type=float, default=0.6, help="Ordered timestamp fraction for train split.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Ordered timestamp fraction for validation split.")
    parser.add_argument(
        "--split-strategy",
        default="timestamp",
        choices=["timestamp", "own_ship"],
        help="Split strategy for train/val/test: timestamp (default) or own_ship holdout.",
    )
    parser.add_argument(
        "--threshold-grid-step",
        type=float,
        default=0.05,
        help="Threshold sweep step size for validation F1 selection (default: 0.05).",
    )
    parser.add_argument("--torch-device", default="auto", help="Torch device for torch_mlp: auto, cpu, or mps.")
    parser.add_argument("--random-seed", type=int, default=42, help="Base random seed for reproducible model training.")
    args = parser.parse_args()

    summary = run_pairwise_benchmark(
        input_path=args.input,
        output_prefix=args.output_prefix,
        model_names=[item.strip() for item in args.models.split(",") if item.strip()],
        train_fraction=float(args.train_fraction),
        val_fraction=float(args.val_fraction),
        split_strategy=args.split_strategy,
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
        threshold_grid_step=float(args.threshold_grid_step),
    )
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"predictions_csv={summary['predictions_csv_path']}")


if __name__ == "__main__":
    main()
