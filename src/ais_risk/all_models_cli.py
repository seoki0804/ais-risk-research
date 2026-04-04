from __future__ import annotations

import argparse

from .all_models import run_all_supported_models


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train all supported AIS risk models on one pairwise dataset and export a unified leaderboard."
    )
    parser.add_argument("--input", required=True, help="Pairwise dataset CSV path.")
    parser.add_argument("--output-dir", required=True, help="Output directory for summaries and leaderboard.")
    parser.add_argument(
        "--split-strategy",
        default="own_ship",
        choices=["timestamp", "own_ship"],
        help="Train/val/test split strategy.",
    )
    parser.add_argument("--train-fraction", type=float, default=0.6, help="Train fraction.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Validation fraction.")
    parser.add_argument("--torch-device", default="auto", help="Torch device for torch_mlp/CNN: auto, cpu, or mps.")
    parser.add_argument("--random-seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--calibration-bins", type=int, default=10, help="Calibration bin count.")
    parser.add_argument("--min-positive-support", type=int, default=10, help="Minimum positive support for stable interpretation warnings.")
    parser.add_argument(
        "--auto-adjust-split-for-support",
        action="store_true",
        help="Auto-adjust train/val fractions to satisfy minimum positive support on test split when possible.",
    )

    parser.add_argument("--include-regional-cnn", action="store_true", help="Also train regional raster CNN variants.")
    parser.add_argument(
        "--cnn-losses",
        default="weighted_bce,focal",
        help="Comma-separated CNN losses to run (weighted_bce,focal).",
    )
    parser.add_argument("--cnn-half-width-nm", type=float, default=3.0, help="CNN raster half-width (nm).")
    parser.add_argument("--cnn-raster-size", type=int, default=64, help="CNN raster side length.")
    parser.add_argument("--cnn-epochs", type=int, default=20, help="CNN epochs.")
    parser.add_argument("--cnn-batch-size", type=int, default=64, help="CNN batch size.")
    parser.add_argument("--cnn-learning-rate", type=float, default=1e-3, help="CNN learning rate.")
    parser.add_argument("--cnn-focal-gamma", type=float, default=2.0, help="Focal gamma when loss=focal.")
    parser.add_argument("--cnn-no-balanced-batches", action="store_true", help="Disable weighted batch sampling.")
    parser.add_argument("--cnn-max-train-rows", type=int, default=0, help="Optional train-row cap for CNN.")
    parser.add_argument("--cnn-max-val-rows", type=int, default=0, help="Optional val-row cap for CNN.")
    parser.add_argument("--cnn-max-test-rows", type=int, default=0, help="Optional test-row cap for CNN.")
    parser.add_argument(
        "--fail-on-optional-model-error",
        action="store_true",
        help="Fail instead of continuing when optional models (e.g., CNN) error out.",
    )
    args = parser.parse_args()

    cnn_losses = [item.strip() for item in str(args.cnn_losses).split(",") if item.strip()]
    summary = run_all_supported_models(
        input_path=args.input,
        output_dir=args.output_dir,
        split_strategy=args.split_strategy,
        train_fraction=float(args.train_fraction),
        val_fraction=float(args.val_fraction),
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
        include_regional_cnn=bool(args.include_regional_cnn),
        cnn_losses=cnn_losses,
        cnn_half_width_nm=float(args.cnn_half_width_nm),
        cnn_raster_size=int(args.cnn_raster_size),
        cnn_epochs=int(args.cnn_epochs),
        cnn_batch_size=int(args.cnn_batch_size),
        cnn_learning_rate=float(args.cnn_learning_rate),
        cnn_focal_gamma=float(args.cnn_focal_gamma),
        cnn_balance_batches=not bool(args.cnn_no_balanced_batches),
        cnn_max_train_rows=int(args.cnn_max_train_rows) or None,
        cnn_max_val_rows=int(args.cnn_max_val_rows) or None,
        cnn_max_test_rows=int(args.cnn_max_test_rows) or None,
        calibration_bins=int(args.calibration_bins),
        min_positive_support=int(args.min_positive_support),
        auto_adjust_split_for_support=bool(args.auto_adjust_split_for_support),
        continue_on_optional_model_error=not bool(args.fail_on_optional_model_error),
    )

    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"leaderboard_csv={summary['leaderboard_csv_path']}")
    print(f"leaderboard_md={summary['leaderboard_md_path']}")


if __name__ == "__main__":
    main()
