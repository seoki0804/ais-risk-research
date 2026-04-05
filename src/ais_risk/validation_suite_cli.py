from __future__ import annotations

import argparse

from .validation_suite import run_validation_suite


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run validation suite on pairwise AIS dataset: timestamp split, own-ship split, "
            "and leave-one-own-ship-out."
        )
    )
    parser.add_argument("--input", required=True, help="Pairwise learning dataset CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for suite summary and sub-runs.")
    parser.add_argument(
        "--models",
        default="rule_score,logreg,hgbt",
        help="Comma-separated model names. Supported: rule_score,logreg,hgbt,torch_mlp",
    )
    parser.add_argument("--torch-device", default="auto", help="Torch device for torch_mlp: auto, cpu, or mps.")
    parser.add_argument("--random-seed", type=int, default=42, help="Base random seed for reproducible model training.")
    parser.add_argument("--own-ship-loo-holdouts", help="Optional comma-separated own MMSI list for LOO holdouts.")
    parser.add_argument("--own-ship-loo-val-fraction", type=float, default=0.2, help="Validation fraction for non-holdout rows.")
    args = parser.parse_args()

    holdouts = None
    if args.own_ship_loo_holdouts:
        holdouts = [item.strip() for item in args.own_ship_loo_holdouts.split(",") if item.strip()]

    summary = run_validation_suite(
        input_path=args.input,
        output_prefix=args.output_prefix,
        model_names=[item.strip() for item in args.models.split(",") if item.strip()],
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
        own_ship_loo_holdout_mmsis=holdouts,
        own_ship_loo_val_fraction=float(args.own_ship_loo_val_fraction),
    )
    print(f"status={summary['status']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    for strategy_name, strategy in summary["strategies"].items():
        print(f"{strategy_name}_status={strategy.get('status', 'unknown')}")


if __name__ == "__main__":
    main()
