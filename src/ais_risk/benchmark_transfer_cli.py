from __future__ import annotations

import argparse

from .benchmark import run_pairwise_transfer_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train on one pairwise AIS dataset and export transfer predictions on another dataset."
    )
    parser.add_argument("--train-input", required=True, help="Source pairwise learning dataset CSV path.")
    parser.add_argument("--target-input", required=True, help="Target pairwise learning dataset CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for source/target transfer outputs.")
    parser.add_argument(
        "--models",
        default="rule_score,logreg,hgbt",
        help="Comma-separated model names. Supported: rule_score,logreg,hgbt,random_forest,extra_trees,torch_mlp",
    )
    parser.add_argument("--train-fraction", type=float, default=0.6, help="Ordered fraction for source-train split.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Ordered fraction for source-validation split.")
    parser.add_argument(
        "--split-strategy",
        default="own_ship",
        choices=["timestamp", "own_ship"],
        help="Split strategy applied to the source dataset.",
    )
    parser.add_argument(
        "--threshold-grid-step",
        type=float,
        default=0.05,
        help="Threshold sweep step size for source validation F1 selection (default: 0.05).",
    )
    parser.add_argument("--torch-device", default="auto", help="Torch device for torch_mlp: auto, cpu, or mps.")
    parser.add_argument("--random-seed", type=int, default=42, help="Base random seed for reproducible training.")
    args = parser.parse_args()

    summary = run_pairwise_transfer_benchmark(
        train_input_path=args.train_input,
        target_input_path=args.target_input,
        output_prefix=args.output_prefix,
        model_names=[item.strip() for item in args.models.split(",") if item.strip()],
        train_fraction=float(args.train_fraction),
        val_fraction=float(args.val_fraction),
        split_strategy=args.split_strategy,
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
        threshold_grid_step=float(args.threshold_grid_step),
    )
    print(f"source_summary_json={summary['source_summary_json_path']}")
    print(f"source_val_predictions_csv={summary['source_val_predictions_csv_path']}")
    print(f"target_predictions_csv={summary['target_predictions_csv_path']}")
    print(f"transfer_summary_json={summary['transfer_summary_json_path']}")
    print(f"transfer_summary_md={summary['transfer_summary_md_path']}")


if __name__ == "__main__":
    main()
