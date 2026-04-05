from __future__ import annotations

import argparse

from .regional_raster_cnn import run_regional_raster_cnn_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small regional raster CNN baseline on pairwise AIS rows.")
    parser.add_argument("--input", required=True, help="Pairwise dataset CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for summary and predictions.")
    parser.add_argument("--split-strategy", default="own_ship", choices=["timestamp", "own_ship"], help="Train/val/test split strategy.")
    parser.add_argument("--train-fraction", type=float, default=0.6, help="Train fraction.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Validation fraction.")
    parser.add_argument("--half-width-nm", type=float, default=3.0, help="Half width of own-ship centered raster window.")
    parser.add_argument("--raster-size", type=int, default=64, help="Square raster resolution.")
    parser.add_argument("--epochs", type=int, default=20, help="Training epochs.")
    parser.add_argument("--batch-size", type=int, default=64, help="Training batch size.")
    parser.add_argument("--learning-rate", type=float, default=1e-3, help="Adam learning rate.")
    parser.add_argument("--loss-type", default="weighted_bce", choices=["weighted_bce", "focal"], help="Training loss.")
    parser.add_argument("--focal-gamma", type=float, default=2.0, help="Gamma for focal loss.")
    parser.add_argument("--no-balanced-batches", action="store_true", help="Disable weighted batch sampling.")
    parser.add_argument("--torch-device", default="auto", help="Torch device: auto, cpu, or mps.")
    parser.add_argument("--random-seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--max-train-rows", type=int, default=0, help="Optional train-row cap for smoke runs.")
    parser.add_argument("--max-val-rows", type=int, default=0, help="Optional validation-row cap for smoke runs.")
    parser.add_argument("--max-test-rows", type=int, default=0, help="Optional test-row cap for smoke runs.")
    args = parser.parse_args()

    summary = run_regional_raster_cnn_benchmark(
        input_path=args.input,
        output_prefix=args.output_prefix,
        split_strategy=args.split_strategy,
        train_fraction=float(args.train_fraction),
        val_fraction=float(args.val_fraction),
        half_width_nm=float(args.half_width_nm),
        raster_size=int(args.raster_size),
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
        epochs=int(args.epochs),
        batch_size=int(args.batch_size),
        learning_rate=float(args.learning_rate),
        loss_type=str(args.loss_type),
        focal_gamma=float(args.focal_gamma),
        balance_batches=not bool(args.no_balanced_batches),
        max_train_rows=int(args.max_train_rows) or None,
        max_val_rows=int(args.max_val_rows) or None,
        max_test_rows=int(args.max_test_rows) or None,
    )
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"predictions_csv={summary['predictions_csv_path']}")


if __name__ == "__main__":
    main()
