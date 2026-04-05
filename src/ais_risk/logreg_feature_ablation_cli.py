from __future__ import annotations

import argparse

from .logreg_feature_ablation import run_logreg_feature_ablation


def _parse_variants(spec: str) -> list[tuple[str, set[str]]]:
    variants: list[tuple[str, set[str]]] = []
    for chunk in [item.strip() for item in spec.split(";") if item.strip()]:
        if "=" not in chunk:
            name = chunk
            fields: set[str] = set()
        else:
            name, raw_fields = chunk.split("=", 1)
            fields = {field.strip() for field in raw_fields.split(",") if field.strip()}
        variants.append((name.strip(), fields))
    return variants


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run logistic-regression feature ablation on a pairwise AIS dataset."
    )
    parser.add_argument("--input", required=True, help="Pairwise learning dataset CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for ablation summary.")
    parser.add_argument(
        "--variants",
        default="baseline=;drop_target_vessel_type=target_vessel_type;drop_all_vessel_type=target_vessel_type,own_vessel_type;drop_vessel_and_encounter=target_vessel_type,own_vessel_type,encounter_type",
        help=(
            "Semicolon-separated variant spec. "
            "Example: baseline=;drop_target_vessel_type=target_vessel_type;drop_all_vessel_type=target_vessel_type,own_vessel_type"
        ),
    )
    parser.add_argument(
        "--split-strategy",
        default="own_ship",
        choices=["timestamp", "own_ship"],
        help="Split strategy for train/val/test partition.",
    )
    parser.add_argument("--train-fraction", type=float, default=0.6, help="Train fraction.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Validation fraction.")
    parser.add_argument("--random-seed", type=int, default=42, help="Random seed.")
    args = parser.parse_args()

    summary = run_logreg_feature_ablation(
        input_path=args.input,
        output_prefix=args.output_prefix,
        variants=_parse_variants(args.variants),
        split_strategy=args.split_strategy,
        train_fraction=float(args.train_fraction),
        val_fraction=float(args.val_fraction),
        random_seed=int(args.random_seed),
    )
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")


if __name__ == "__main__":
    main()
