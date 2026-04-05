from __future__ import annotations

import argparse

from .transfer_override_seed_stress_test import run_transfer_override_seed_stress_test


def _parse_list(raw: str) -> list[str]:
    return [token.strip() for token in str(raw).split(",") if token.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run multi-seed stress test for transfer-only override policy "
            "(baseline model vs override model/method)."
        )
    )
    parser.add_argument("--input-dir", required=True, help="Input pairwise CSV directory.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix path (without extension).")
    parser.add_argument("--source-region", default="houston", help="Source region.")
    parser.add_argument(
        "--target-regions",
        default="nola,seattle",
        help="Comma-separated target regions.",
    )
    parser.add_argument("--baseline-model", default="hgbt", help="Baseline model name.")
    parser.add_argument("--override-model", default="rule_score", help="Override model name.")
    parser.add_argument("--override-method", default="isotonic", help="Override calibration method.")
    parser.add_argument(
        "--seeds",
        default="41,42,43,44,45",
        help="Comma-separated random seeds.",
    )
    parser.add_argument("--split-strategy", default="own_ship", choices=["own_ship", "timestamp"], help="Split strategy.")
    parser.add_argument("--train-fraction", type=float, default=0.6, help="Train fraction.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Validation fraction.")
    parser.add_argument("--threshold-grid-step", type=float, default=0.01, help="Threshold sweep step.")
    parser.add_argument("--ece-gate-max", type=float, default=0.10, help="Target ECE gate threshold.")
    parser.add_argument(
        "--max-negative-pairs-allowed",
        type=int,
        default=1,
        help="Maximum allowed negative transfer pairs in fixed-threshold mode.",
    )
    parser.add_argument("--torch-device", default="auto", help="Torch device.")
    parser.add_argument("--calibration-bins", type=int, default=10, help="Calibration bin count.")
    args = parser.parse_args()

    summary = run_transfer_override_seed_stress_test(
        input_dir=args.input_dir,
        output_prefix=args.output_prefix,
        source_region=args.source_region,
        target_regions=_parse_list(args.target_regions),
        baseline_model=args.baseline_model,
        override_model=args.override_model,
        override_method=args.override_method,
        random_seeds=args.seeds,
        split_strategy=args.split_strategy,
        train_fraction=float(args.train_fraction),
        val_fraction=float(args.val_fraction),
        threshold_grid_step=float(args.threshold_grid_step),
        ece_gate_max=float(args.ece_gate_max),
        max_negative_pairs_allowed=int(args.max_negative_pairs_allowed),
        torch_device=args.torch_device,
        calibration_bins=int(args.calibration_bins),
    )

    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"per_seed_csv={summary['per_seed_csv_path']}")
    print(f"run_root={summary['run_root']}")


if __name__ == "__main__":
    main()

