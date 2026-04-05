from __future__ import annotations

import argparse

from .focus_rank_compare import run_focus_rank_compare_bundle
from .study_sweep import parse_benchmark_modelsets


def _parse_ranks(text: str | None) -> list[int]:
    if not text:
        return [1, 2, 3]
    values: list[int] = []
    for chunk in str(text).split(","):
        item = chunk.strip()
        if not item:
            continue
        values.append(max(1, int(item)))
    if not values:
        return [1, 2, 3]
    return values


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run focus-vs-baseline bundle across multiple auto-focus ranks and summarize best rank per modelset."
    )
    parser.add_argument("--manifest", required=True, help="Dataset manifest markdown path.")
    parser.add_argument("--raw-input", required=True, help="Raw AIS CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for rank-compare summary.")
    parser.add_argument("--auto-focus-ranks", default="1,2,3", help="Comma-separated auto-focus candidate ranks.")
    parser.add_argument("--output-root", default="outputs/focus_rank_compare", help="Root directory for rank runs.")
    parser.add_argument("--config", default="configs/base.toml", help="Project TOML config path.")
    parser.add_argument("--ingestion-bundle", help="Optional named ingestion bundle for workflow step.")
    parser.add_argument("--ingestion-config", help="Optional ingestion TOML config path.")
    parser.add_argument("--source-preset", default="auto", help="Header mapping preset for workflow preprocessing.")
    parser.add_argument("--column-map", help="Optional column overrides like mmsi=ShipId,timestamp=Event Time.")
    parser.add_argument("--vessel-types", help="Optional standardized vessel type filter for workflow preprocessing.")
    parser.add_argument(
        "--benchmark-modelsets",
        default="rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp",
        help="Semicolon-separated modelsets.",
    )
    parser.add_argument(
        "--pairwise-split-strategy",
        default="own_ship",
        choices=["timestamp", "own_ship"],
        help="Train/val/test split strategy for pairwise benchmark.",
    )
    parser.add_argument("--run-calibration-eval", action=argparse.BooleanOptionalAction, default=True, help="Enable calibration evaluation.")
    parser.add_argument("--run-own-ship-loo", action=argparse.BooleanOptionalAction, default=True, help="Enable own-ship LOO.")
    parser.add_argument("--run-own-ship-case-eval", action=argparse.BooleanOptionalAction, default=True, help="Enable own-ship fixed-case repeated eval.")
    parser.add_argument("--own-ship-case-eval-min-rows", type=int, default=30, help="Minimum rows per own ship for fixed-case evaluation.")
    parser.add_argument("--own-ship-case-eval-repeat-count", type=int, default=3, help="Repeat count for fixed-case evaluation.")
    parser.add_argument("--build-study-journals", action="store_true", help="Build study journal markdown per run/modelset.")
    parser.add_argument(
        "--study-journal-output-template",
        help="Output template for study journals. Supports {date}, {dataset_id}, {modelset_index}, {modelset_key}, {sweep_type}.",
    )
    parser.add_argument("--study-journal-note", help="Optional note appended to generated study journals.")
    parser.add_argument("--torch-device", default="auto", help="Torch device: auto, cpu, mps.")
    parser.add_argument("--random-seed", type=int, default=42, help="Base random seed for reproducible training/evaluation.")
    parser.add_argument("--compare-epsilon", type=float, default=1e-9, help="Tolerance for compare equal decision.")
    parser.add_argument("--focus-label", default="focused_single_own_ship", help="Focus label used in compare report.")
    parser.add_argument("--baseline-label", default="baseline_multi_own_ship", help="Baseline label used in compare report.")
    parser.add_argument(
        "--reuse-baseline-across-ranks",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse baseline sweep summary from first rank for remaining rank runs.",
    )
    args = parser.parse_args()

    summary = run_focus_rank_compare_bundle(
        manifest_path=args.manifest,
        raw_input_path=args.raw_input,
        output_prefix=args.output_prefix,
        auto_focus_ranks=_parse_ranks(args.auto_focus_ranks),
        benchmark_modelsets=parse_benchmark_modelsets(args.benchmark_modelsets),
        config_path=args.config,
        ingestion_bundle_name=args.ingestion_bundle,
        ingestion_config_path=args.ingestion_config,
        source_preset_name=args.source_preset,
        manual_column_map_text=args.column_map,
        vessel_types_text=args.vessel_types,
        output_root=args.output_root,
        pairwise_split_strategy=args.pairwise_split_strategy,
        run_calibration_eval=bool(args.run_calibration_eval),
        run_own_ship_loo=bool(args.run_own_ship_loo),
        run_own_ship_case_eval=bool(args.run_own_ship_case_eval),
        own_ship_case_eval_min_rows=int(args.own_ship_case_eval_min_rows),
        own_ship_case_eval_repeat_count=max(1, int(args.own_ship_case_eval_repeat_count)),
        build_study_journals=bool(args.build_study_journals),
        study_journal_output_template=args.study_journal_output_template,
        study_journal_note=args.study_journal_note,
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
        compare_epsilon=float(args.compare_epsilon),
        focus_label=args.focus_label,
        baseline_label=args.baseline_label,
        reuse_baseline_across_ranks=bool(args.reuse_baseline_across_ranks),
    )
    print(f"status={summary['status']}")
    print(f"run_count={summary['run_count']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"rank_rows_csv={summary['rank_rows_csv_path']}")
    print(f"modelset_rows_csv={summary['modelset_rows_csv_path']}")


if __name__ == "__main__":
    main()
