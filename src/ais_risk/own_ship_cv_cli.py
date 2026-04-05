from __future__ import annotations

import argparse

from .own_ship_cv import run_leave_one_own_ship_out_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run leave-one-own-ship-out validation on pairwise AIS learning dataset."
    )
    parser.add_argument("--input", required=True, help="Pairwise learning dataset CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for LOO validation summary files.")
    parser.add_argument(
        "--models",
        default="rule_score,logreg,hgbt",
        help="Comma-separated model names. Supported: rule_score,logreg,hgbt,torch_mlp",
    )
    parser.add_argument(
        "--holdout-own-mmsis",
        help="Optional comma-separated holdout own MMSI list. If omitted, all own MMSIs are evaluated.",
    )
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Validation fraction from non-holdout timestamps.")
    parser.add_argument("--torch-device", default="auto", help="Torch device for torch_mlp: auto, cpu, or mps.")
    parser.add_argument("--random-seed", type=int, default=42, help="Base random seed for reproducible training.")
    args = parser.parse_args()

    holdout_own_mmsis = None
    if args.holdout_own_mmsis:
        holdout_own_mmsis = [item.strip() for item in args.holdout_own_mmsis.split(",") if item.strip()]
    summary = run_leave_one_own_ship_out_benchmark(
        input_path=args.input,
        output_prefix=args.output_prefix,
        model_names=[item.strip() for item in args.models.split(",") if item.strip()],
        holdout_own_mmsis=holdout_own_mmsis,
        val_fraction=float(args.val_fraction),
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
    )
    print(f"status={summary['status']}")
    print(f"evaluated_holdouts={summary['evaluated_holdouts']}")
    print(f"completed_folds={summary['completed_fold_count']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"fold_metrics_csv={summary['fold_metrics_csv_path']}")


if __name__ == "__main__":
    main()
