from __future__ import annotations

import argparse

from .study_sweep import parse_benchmark_modelsets, run_study_modelset_sweep


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a modelset sweep over study_run pipeline and build comparison summary artifacts."
    )
    parser.add_argument("--manifest", required=True, help="Dataset manifest markdown path.")
    parser.add_argument("--raw-input", required=True, help="Raw AIS CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for sweep summary files.")
    parser.add_argument("--output-root", default="outputs/study_sweep", help="Root directory for per-modelset study outputs.")
    parser.add_argument("--config", default="configs/base.toml", help="Project TOML config path.")
    parser.add_argument("--ingestion-bundle", help="Optional named ingestion bundle for workflow step.")
    parser.add_argument("--ingestion-config", help="Optional ingestion TOML config path.")
    parser.add_argument("--source-preset", default="auto", help="Header mapping preset for workflow preprocessing.")
    parser.add_argument("--column-map", help="Optional column overrides like mmsi=ShipId,timestamp=Event Time.")
    parser.add_argument("--vessel-types", help="Optional standardized vessel type filter for workflow preprocessing.")
    parser.add_argument(
        "--benchmark-modelsets",
        default="rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp",
        help="Semicolon-separated modelsets. Example: rule_score,logreg,hgbt;rule_score,logreg,hgbt,torch_mlp",
    )
    parser.add_argument(
        "--pairwise-split-strategy",
        default="own_ship",
        choices=["timestamp", "own_ship"],
        help="Train/val/test split strategy for pairwise benchmark.",
    )
    parser.add_argument("--run-calibration-eval", action=argparse.BooleanOptionalAction, default=True, help="Enable calibration evaluation for each modelset.")
    parser.add_argument("--run-own-ship-loo", action=argparse.BooleanOptionalAction, default=True, help="Enable own-ship LOO for each modelset.")
    parser.add_argument("--run-own-ship-case-eval", action=argparse.BooleanOptionalAction, default=True, help="Enable own-ship fixed-case repeated eval for each modelset.")
    parser.add_argument("--own-ship-case-eval-mmsis", help="Optional comma-separated own MMSI list for fixed-case evaluation.")
    parser.add_argument("--own-ship-case-eval-min-rows", type=int, default=30, help="Minimum rows per own ship for fixed-case evaluation.")
    parser.add_argument("--own-ship-case-eval-repeat-count", type=int, default=3, help="Repeat count for fixed-case evaluation.")
    parser.add_argument(
        "--build-study-journals",
        action="store_true",
        help="Build study journal markdown per modelset run.",
    )
    parser.add_argument(
        "--study-journal-output-template",
        help="Output template for per-modelset study journals. Supported keys: {date}, {dataset_id}, {modelset_index}, {modelset_key}.",
    )
    parser.add_argument(
        "--study-journal-note",
        help="Optional note appended to every generated study journal.",
    )
    parser.add_argument("--torch-device", default="auto", help="Torch device: auto, cpu, mps.")
    parser.add_argument("--random-seed", type=int, default=42, help="Base random seed for reproducible training/evaluation.")
    args = parser.parse_args()

    own_ship_case_eval_mmsis = None
    if args.own_ship_case_eval_mmsis:
        own_ship_case_eval_mmsis = [item.strip() for item in args.own_ship_case_eval_mmsis.split(",") if item.strip()]

    summary = run_study_modelset_sweep(
        manifest_path=args.manifest,
        raw_input_path=args.raw_input,
        output_prefix=args.output_prefix,
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
        own_ship_case_eval_mmsis=own_ship_case_eval_mmsis,
        own_ship_case_eval_min_rows=int(args.own_ship_case_eval_min_rows),
        own_ship_case_eval_repeat_count=max(1, int(args.own_ship_case_eval_repeat_count)),
        build_study_journals=bool(args.build_study_journals),
        study_journal_output_template=args.study_journal_output_template,
        study_journal_note=args.study_journal_note,
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
    )

    print(f"status={summary['status']}")
    print(f"modelset_count={summary['modelset_count']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_csv={summary['summary_csv_path']}")


if __name__ == "__main__":
    main()
