from __future__ import annotations

import argparse

from .own_ship_case_eval import run_own_ship_case_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run own-ship fixed-case repeated validation from pairwise AIS dataset."
    )
    parser.add_argument("--input", required=True, help="Pairwise learning dataset CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for own-ship case eval.")
    parser.add_argument(
        "--models",
        default="rule_score,logreg,hgbt",
        help="Comma-separated model names. Supported: rule_score,logreg,hgbt,torch_mlp",
    )
    parser.add_argument(
        "--own-mmsis",
        help="Optional comma-separated own MMSI list. If omitted, evaluates all own MMSI values.",
    )
    parser.add_argument("--min-rows-per-ship", type=int, default=30, help="Minimum row count per own ship.")
    parser.add_argument("--train-fraction", type=float, default=0.6, help="Train fraction for timestamp split.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Validation fraction for timestamp split.")
    parser.add_argument("--repeat-count", type=int, default=1, help="Repeat count for rotated timestamp split per own ship.")
    parser.add_argument("--torch-device", default="auto", help="Torch device for torch_mlp: auto, cpu, or mps.")
    parser.add_argument("--random-seed", type=int, default=42, help="Base random seed for reproducible training.")
    args = parser.parse_args()

    own_mmsis = None
    if args.own_mmsis:
        own_mmsis = [item.strip() for item in args.own_mmsis.split(",") if item.strip()]

    summary = run_own_ship_case_evaluation(
        input_path=args.input,
        output_prefix=args.output_prefix,
        model_names=[item.strip() for item in args.models.split(",") if item.strip()],
        own_mmsis=own_mmsis,
        min_rows_per_ship=int(args.min_rows_per_ship),
        train_fraction=float(args.train_fraction),
        val_fraction=float(args.val_fraction),
        repeat_count=max(1, int(args.repeat_count)),
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
    )
    print(f"status={summary['status']}")
    print(f"candidate_own_ship_count={summary['candidate_own_ship_count']}")
    print(f"evaluated_own_ship_count={summary['evaluated_own_ship_count']}")
    print(f"completed_own_ship_count={summary['completed_own_ship_count']}")
    print(f"completed_repeats_total={summary.get('completed_repeats_total', 0)}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"ship_metrics_csv={summary['ship_metrics_csv_path']}")
    print(f"repeat_metrics_csv={summary['repeat_metrics_csv_path']}")


if __name__ == "__main__":
    main()
