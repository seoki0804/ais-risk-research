from __future__ import annotations

import argparse

from .focus_seed_pipeline import run_focus_seed_pipeline
from .study_sweep import parse_benchmark_modelsets


def _parse_mmsis(text: str | None) -> list[str]:
    if not text:
        return []
    values: list[str] = []
    for chunk in str(text).split(","):
        item = chunk.strip()
        if not item:
            continue
        values.append(item)
    return values


def _parse_seeds(text: str | None) -> list[int]:
    if not text:
        return [42, 43, 44]
    values: list[int] = []
    for chunk in str(text).split(","):
        item = chunk.strip()
        if not item:
            continue
        values.append(int(item))
    return values or [42, 43, 44]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run focus seed compare with optional automatic own-ship candidate selection."
    )
    parser.add_argument("--manifest", required=True, help="Dataset manifest markdown path.")
    parser.add_argument("--raw-input", required=True, help="Raw AIS CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for pipeline summary.")
    parser.add_argument("--focus-own-ship-mmsis", help="Comma-separated focus own-ship MMSIs. If omitted, auto selection is used.")
    parser.add_argument(
        "--auto-select-focus-mmsis",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="When focus MMSIs are omitted, select top candidates automatically from workflow own-ship ranking.",
    )
    parser.add_argument("--auto-select-count", type=int, default=3, help="Number of focus MMSIs to select from candidate ranking.")
    parser.add_argument("--auto-select-start-rank", type=int, default=1, help="Starting rank (1-based) for automatic MMSI selection.")
    parser.add_argument(
        "--auto-select-workflow-output-dir",
        help="Optional output directory used by the auto-selection workflow run. Defaults to a unique sibling of output-prefix.",
    )
    parser.add_argument(
        "--auto-select-workflow-top-n",
        type=int,
        help="Optional top-N passed to workflow during candidate generation. Defaults to start-rank+count.",
    )
    parser.add_argument(
        "--auto-select-workflow-min-targets",
        type=int,
        default=1,
        help="Minimum nearby targets for auto-selection workflow candidate scoring.",
    )
    parser.add_argument(
        "--auto-select-workflow-radius-nm",
        type=float,
        help="Optional candidate scoring radius for auto-selection workflow.",
    )
    parser.add_argument(
        "--auto-candidate-quality-gate-apply",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Apply own-ship quality gate before automatic focus MMSI selection.",
    )
    parser.add_argument(
        "--auto-candidate-quality-gate-strict",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Fail the run when quality gate removes all automatically generated own-ship candidates.",
    )
    parser.add_argument("--auto-candidate-quality-gate-min-row-count", type=int, default=80)
    parser.add_argument("--auto-candidate-quality-gate-min-observed-row-count", type=int, default=40)
    parser.add_argument("--auto-candidate-quality-gate-max-interpolation-ratio", type=float, default=0.70)
    parser.add_argument("--auto-candidate-quality-gate-min-heading-coverage-ratio", type=float, default=0.50)
    parser.add_argument("--auto-candidate-quality-gate-min-movement-ratio", type=float, default=0.30)
    parser.add_argument("--auto-candidate-quality-gate-min-active-window-ratio", type=float, default=0.10)
    parser.add_argument("--auto-candidate-quality-gate-min-average-nearby-targets", type=float, default=0.50)
    parser.add_argument("--auto-candidate-quality-gate-max-segment-break-count", type=int, default=50)
    parser.add_argument("--auto-candidate-quality-gate-min-candidate-score", type=float, default=0.20)
    parser.add_argument("--auto-candidate-quality-gate-min-recommended-target-count", type=int, default=1)
    parser.add_argument("--seed-values", default="42,43,44", help="Comma-separated seed list.")
    parser.add_argument("--output-root", default="outputs/focus_seed_pipeline", help="Root directory for seed runs.")
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
    parser.add_argument("--compare-epsilon", type=float, default=1e-9, help="Tolerance for compare equal decision.")
    parser.add_argument("--focus-label", default="focused_single_own_ship", help="Focus label used in compare report.")
    parser.add_argument("--baseline-label", default="baseline_multi_own_ship", help="Baseline label used in compare report.")
    parser.add_argument(
        "--reuse-baseline-across-mmsis",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse baseline sweep summary from first MMSI run inside each seed run.",
    )
    parser.add_argument("--validation-gate-min-seed-count", type=int, default=3, help="Minimum seed count required by validation gate.")
    parser.add_argument(
        "--validation-gate-min-mean-aggregate-score",
        type=float,
        default=0.0,
        help="Minimum allowed mean aggregate score for pass.",
    )
    parser.add_argument(
        "--validation-gate-min-delta-case-f1-mean",
        type=float,
        default=0.0,
        help="Minimum allowed mean delta case F1 (focus-baseline) for pass.",
    )
    parser.add_argument(
        "--validation-gate-max-delta-case-f1-std",
        type=float,
        default=0.05,
        help="Maximum allowed std of delta case F1 across seeds.",
    )
    parser.add_argument(
        "--validation-gate-max-delta-repeat-std-mean",
        type=float,
        default=0.02,
        help="Maximum allowed mean delta repeat std (focus-baseline).",
    )
    parser.add_argument(
        "--validation-gate-max-delta-calibration-ece",
        type=float,
        default=0.0,
        help="Maximum allowed mean delta calibration ECE (focus-baseline).",
    )
    parser.add_argument(
        "--validation-gate-require-calibration-metric",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Require calibration delta metric to be present for pass.",
    )
    parser.add_argument(
        "--validation-gate-allow-focus-tilt",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Allow robustness label focus_tilt as pass candidate.",
    )
    parser.add_argument(
        "--validation-gate-allow-mixed",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Allow robustness label mixed as pass candidate.",
    )
    args = parser.parse_args()

    summary = run_focus_seed_pipeline(
        manifest_path=args.manifest,
        raw_input_path=args.raw_input,
        output_prefix=args.output_prefix,
        benchmark_modelsets=parse_benchmark_modelsets(args.benchmark_modelsets),
        focus_own_ship_mmsis=_parse_mmsis(args.focus_own_ship_mmsis),
        seed_values=_parse_seeds(args.seed_values),
        auto_select_focus_mmsis=bool(args.auto_select_focus_mmsis),
        auto_select_count=max(1, int(args.auto_select_count)),
        auto_select_start_rank=max(1, int(args.auto_select_start_rank)),
        auto_select_workflow_output_dir=args.auto_select_workflow_output_dir,
        auto_select_workflow_top_n=args.auto_select_workflow_top_n,
        auto_select_workflow_min_targets=max(1, int(args.auto_select_workflow_min_targets)),
        auto_select_workflow_radius_nm=args.auto_select_workflow_radius_nm,
        auto_candidate_quality_gate_apply=bool(args.auto_candidate_quality_gate_apply),
        auto_candidate_quality_gate_strict=bool(args.auto_candidate_quality_gate_strict),
        auto_candidate_quality_gate_min_row_count=max(1, int(args.auto_candidate_quality_gate_min_row_count)),
        auto_candidate_quality_gate_min_observed_row_count=max(1, int(args.auto_candidate_quality_gate_min_observed_row_count)),
        auto_candidate_quality_gate_max_interpolation_ratio=float(args.auto_candidate_quality_gate_max_interpolation_ratio),
        auto_candidate_quality_gate_min_heading_coverage_ratio=float(args.auto_candidate_quality_gate_min_heading_coverage_ratio),
        auto_candidate_quality_gate_min_movement_ratio=float(args.auto_candidate_quality_gate_min_movement_ratio),
        auto_candidate_quality_gate_min_active_window_ratio=float(args.auto_candidate_quality_gate_min_active_window_ratio),
        auto_candidate_quality_gate_min_average_nearby_targets=float(args.auto_candidate_quality_gate_min_average_nearby_targets),
        auto_candidate_quality_gate_max_segment_break_count=max(0, int(args.auto_candidate_quality_gate_max_segment_break_count)),
        auto_candidate_quality_gate_min_candidate_score=float(args.auto_candidate_quality_gate_min_candidate_score),
        auto_candidate_quality_gate_min_recommended_target_count=max(0, int(args.auto_candidate_quality_gate_min_recommended_target_count)),
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
        own_ship_case_eval_min_rows=max(1, int(args.own_ship_case_eval_min_rows)),
        own_ship_case_eval_repeat_count=max(1, int(args.own_ship_case_eval_repeat_count)),
        build_study_journals=bool(args.build_study_journals),
        study_journal_output_template=args.study_journal_output_template,
        study_journal_note=args.study_journal_note,
        torch_device=args.torch_device,
        compare_epsilon=float(args.compare_epsilon),
        focus_label=args.focus_label,
        baseline_label=args.baseline_label,
        reuse_baseline_across_mmsis=bool(args.reuse_baseline_across_mmsis),
        validation_gate_min_seed_count=max(1, int(args.validation_gate_min_seed_count)),
        validation_gate_min_mean_aggregate_score=float(args.validation_gate_min_mean_aggregate_score),
        validation_gate_min_delta_case_f1_mean=float(args.validation_gate_min_delta_case_f1_mean),
        validation_gate_max_delta_case_f1_std=float(args.validation_gate_max_delta_case_f1_std),
        validation_gate_max_delta_repeat_std_mean=float(args.validation_gate_max_delta_repeat_std_mean),
        validation_gate_max_delta_calibration_ece=float(args.validation_gate_max_delta_calibration_ece),
        validation_gate_require_calibration_metric=bool(args.validation_gate_require_calibration_metric),
        validation_gate_allow_focus_tilt=bool(args.validation_gate_allow_focus_tilt),
        validation_gate_allow_mixed=bool(args.validation_gate_allow_mixed),
    )
    print(f"status={summary['status']}")
    print(f"focus_mmsi_resolution_mode={summary['focus_mmsi_resolution_mode']}")
    print(f"focus_own_ship_mmsis={summary['focus_own_ship_mmsis']}")
    print(f"auto_candidate_quality_gate_applied={summary['auto_candidate_quality_gate_applied']}")
    print(f"auto_candidate_quality_gate_passed_count={summary['auto_candidate_quality_gate_passed_count']}")
    print(f"auto_candidate_quality_gate_fallback_used={summary['auto_candidate_quality_gate_fallback_used']}")
    print(f"validation_gate_overall_decision={summary['validation_gate_overall_decision']}")
    print(f"validation_gate_recommended_modelset_key={summary['validation_gate_recommended_modelset_key']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"selected_focus_mmsis_csv={summary['selected_focus_mmsis_csv_path']}")
    print(f"auto_candidate_quality_gate_summary_md={summary['auto_candidate_quality_gate_summary_md_path']}")
    print(f"focus_seed_compare_summary_json={summary['focus_seed_compare_summary_json_path']}")
    print(f"validation_gate_rows_csv={summary['validation_gate_rows_csv_path']}")


if __name__ == "__main__":
    main()
