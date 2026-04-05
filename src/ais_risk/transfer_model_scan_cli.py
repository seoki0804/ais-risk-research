from __future__ import annotations

import argparse

from .transfer_model_scan import _parse_targets, run_transfer_model_scan


def _parse_models(raw: str) -> list[str]:
    models = [token.strip() for token in str(raw).split(",") if token.strip()]
    if not models:
        raise ValueError("No models parsed.")
    return models


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan multiple candidate models for one source-region transfer robustness.")
    parser.add_argument("--source-region", required=True, help="Source region name.")
    parser.add_argument("--source-input", required=True, help="Source pairwise CSV path.")
    parser.add_argument(
        "--targets",
        required=True,
        help="Comma-separated region:path mappings for targets.",
    )
    parser.add_argument(
        "--models",
        default="rule_score,logreg,hgbt,random_forest,extra_trees,torch_mlp",
        help="Comma-separated model names to scan.",
    )
    parser.add_argument("--output-root", required=True, help="Output root directory.")
    parser.add_argument("--split-strategy", default="own_ship", choices=["own_ship", "timestamp"], help="Source split strategy.")
    parser.add_argument("--train-fraction", type=float, default=0.6, help="Train fraction.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Validation fraction.")
    parser.add_argument("--threshold-grid-step", type=float, default=0.01, help="Threshold sweep step size.")
    parser.add_argument("--torch-device", default="auto", help="Torch device.")
    parser.add_argument("--random-seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--calibration-bins", type=int, default=10, help="Calibration bins.")
    parser.add_argument("--calibration-ece-max", type=float, default=0.10, help="ECE gate upper bound.")
    args = parser.parse_args()

    target_mapping = {region: path for region, path in _parse_targets(args.targets)}
    summary = run_transfer_model_scan(
        source_region=args.source_region,
        source_input_path=args.source_input,
        target_input_paths_by_region=target_mapping,
        model_names=_parse_models(args.models),
        output_root=args.output_root,
        split_strategy=args.split_strategy,
        train_fraction=float(args.train_fraction),
        val_fraction=float(args.val_fraction),
        threshold_grid_step=float(args.threshold_grid_step),
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
        calibration_bins=int(args.calibration_bins),
        calibration_ece_max=float(args.calibration_ece_max),
    )
    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"detail_csv={summary['detail_csv_path']}")
    print(f"model_summary_csv={summary['model_summary_csv_path']}")
    print(f"recommended_model={summary['recommended_model']}")


if __name__ == "__main__":
    main()
