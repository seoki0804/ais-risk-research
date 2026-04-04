from __future__ import annotations

import argparse
from pathlib import Path

from .all_models_seed_sweep import run_all_models_seed_sweep


def _parse_int_list(text: str) -> list[int]:
    items: list[int] = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        items.append(int(token))
    if not items:
        raise ValueError("Expected at least one integer.")
    return items


def _parse_str_list(text: str) -> list[str]:
    items = [token.strip() for token in text.split(",") if token.strip()]
    if not items:
        raise ValueError("Expected at least one item.")
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all-model benchmarking for multiple random seeds and aggregate stability metrics.")
    parser.add_argument(
        "--input-dir",
        default="/Users/seoki/Desktop/research/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix",
        help="Directory containing <region>_pooled_pairwise.csv files.",
    )
    parser.add_argument("--output-root", required=True, help="Output directory for sweep artifacts.")
    parser.add_argument("--regions", default="houston,nola,seattle", help="Comma-separated region names.")
    parser.add_argument("--seeds", default="41,42,43", help="Comma-separated random seeds.")
    parser.add_argument("--split-strategy", default="own_ship", choices=["timestamp", "own_ship"], help="Train/val/test split strategy.")
    parser.add_argument("--train-fraction", type=float, default=0.6, help="Requested train fraction.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Requested validation fraction.")
    parser.add_argument("--torch-device", default="auto", help="Torch device for torch_mlp/CNN.")
    parser.add_argument("--include-regional-cnn", action="store_true", help="Include CNN family models.")
    parser.add_argument("--cnn-losses", default="weighted_bce,focal", help="Comma-separated CNN losses.")
    parser.add_argument("--min-positive-support", type=int, default=10, help="Minimum positive support for warning/adjustment logic.")
    parser.add_argument(
        "--recommendation-f1-tolerance",
        type=float,
        default=0.01,
        help="F1 tolerance band for recommendation tie-break (then choose lower ECE).",
    )
    parser.add_argument(
        "--recommendation-max-ece-mean",
        type=float,
        default=0.10,
        help="Calibration hard gate for recommendation (ECE mean <= value).",
    )
    parser.add_argument(
        "--disable-recommendation-ece-gate",
        action="store_true",
        help="Disable recommendation ECE hard gate.",
    )
    parser.add_argument("--disable-auto-adjust-split", action="store_true", help="Disable split auto-adjustment for positive support.")
    args = parser.parse_args()

    regions = _parse_str_list(args.regions)
    seeds = _parse_int_list(args.seeds)
    cnn_losses = _parse_str_list(args.cnn_losses)
    input_dir = Path(args.input_dir).resolve()
    input_paths = {region: input_dir / f"{region}_pooled_pairwise.csv" for region in regions}

    summary = run_all_models_seed_sweep(
        input_paths_by_region=input_paths,
        output_root=args.output_root,
        seeds=seeds,
        split_strategy=args.split_strategy,
        train_fraction=float(args.train_fraction),
        val_fraction=float(args.val_fraction),
        torch_device=args.torch_device,
        include_regional_cnn=bool(args.include_regional_cnn),
        cnn_losses=cnn_losses,
        min_positive_support=int(args.min_positive_support),
        auto_adjust_split_for_support=not bool(args.disable_auto_adjust_split),
        recommendation_f1_tolerance=float(args.recommendation_f1_tolerance),
        recommendation_max_ece_mean=(None if bool(args.disable_recommendation_ece_gate) else float(args.recommendation_max_ece_mean)),
    )

    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"aggregate_csv={summary['aggregate_csv_path']}")
    print(f"winner_summary_csv={summary['winner_summary_csv_path']}")
    print(f"recommendation_csv={summary['recommendation_csv_path']}")
    print(f"recommendation_md={summary['recommendation_md_path']}")


if __name__ == "__main__":
    main()
