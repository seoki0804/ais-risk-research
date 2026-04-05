from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .batch_review import build_study_batch_review_from_payload
from .batch_trend import build_batch_trend_report
from .study_journal import build_study_journal_from_summary
from .study_batch import run_study_batch_from_manifest_glob


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run study pipeline over multiple manifests and write a batch summary."
    )
    parser.add_argument("--manifest-glob", required=True, help="Glob pattern for manifest markdown files.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for batch summary JSON/MD.")
    parser.add_argument("--raw-input-template", default="data/raw/{source_slug}/{dataset_id}/raw.csv", help="Template for raw input path.")
    parser.add_argument(
        "--auto-merge-glob-template",
        help="Optional template for auto merge CSV glob. Example: data/raw/{source_slug}/{dataset_id}/downloads/**/*.csv",
    )
    parser.add_argument("--config", default="configs/base.toml", help="Project TOML config path.")
    parser.add_argument("--ingestion-bundle", help="Optional named ingestion bundle for workflow step.")
    parser.add_argument("--ingestion-config", help="Optional ingestion TOML config path.")
    parser.add_argument("--source-preset", default="auto", help="Header mapping preset for workflow preprocessing.")
    parser.add_argument("--column-map", help="Optional column overrides like mmsi=ShipId,timestamp=Event Time.")
    parser.add_argument("--vessel-types", help="Optional standardized vessel type filter for workflow preprocessing.")
    parser.add_argument("--output-root", default="outputs", help="Root directory for generated outputs.")
    parser.add_argument("--max-manifests", type=int, help="Optional max number of manifests to process.")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop batch immediately on first failed manifest.")

    parser.add_argument("--workflow-top-n", type=int, default=3, help="Top-N recommendation cases in workflow.")
    parser.add_argument("--workflow-min-targets", type=int, default=1, help="Minimum targets in workflow recommendations.")
    parser.add_argument("--pairwise-label-distance-nm", type=float, default=1.6, help="Positive label threshold.")
    parser.add_argument("--pairwise-top-n-candidates", type=int, default=5, help="Top-N own-ship candidates.")
    parser.add_argument("--pairwise-min-future-points", type=int, default=2, help="Minimum future points for label.")
    parser.add_argument("--pairwise-sample-every", type=int, default=1, help="Use every Nth timestamp.")
    parser.add_argument("--pairwise-min-targets", type=int, default=1, help="Minimum nearby targets.")
    parser.add_argument(
        "--benchmark-models",
        default="rule_score,logreg,hgbt",
        help="Comma-separated models for main benchmark and derived evals (e.g., rule_score,logreg,hgbt,torch_mlp).",
    )
    parser.add_argument(
        "--pairwise-split-strategy",
        default="timestamp",
        choices=["timestamp", "own_ship"],
        help="Train/val/test split strategy for pairwise benchmark.",
    )

    parser.add_argument("--run-error-analysis", action="store_true", help="Run benchmark error analysis.")
    parser.add_argument("--error-analysis-top-k-each", type=int, default=20, help="Top-K FP/FN per model.")
    parser.add_argument("--run-stratified-eval", action="store_true", help="Run stratified evaluation by encounter/distance bins.")
    parser.add_argument("--run-calibration-eval", action="store_true", help="Run calibration evaluation (Brier/ECE/bins).")
    parser.add_argument("--calibration-num-bins", type=int, default=10, help="Reliability bin count for calibration evaluation.")
    parser.add_argument("--run-own-ship-loo", action="store_true", help="Run leave-one-own-ship-out validation.")
    parser.add_argument("--own-ship-loo-holdouts", help="Optional comma-separated own MMSI list.")
    parser.add_argument("--run-own-ship-case-eval", action="store_true", help="Run own-ship fixed-case repeated validation.")
    parser.add_argument("--own-ship-case-eval-mmsis", help="Optional comma-separated own MMSI list for fixed-case evaluation.")
    parser.add_argument("--own-ship-case-eval-min-rows", type=int, default=30, help="Minimum rows per own ship for fixed-case evaluation.")
    parser.add_argument("--own-ship-case-eval-train-fraction", type=float, default=0.6, help="Train fraction for own-ship case timestamp split.")
    parser.add_argument("--own-ship-case-eval-val-fraction", type=float, default=0.2, help="Validation fraction for own-ship case timestamp split.")
    parser.add_argument("--own-ship-case-eval-repeat-count", type=int, default=1, help="Repeat count for rotated timestamp split per own ship.")
    parser.add_argument("--run-validation-suite", action="store_true", help="Run validation suite.")
    parser.add_argument("--update-validation-leaderboard", action="store_true", help="Update validation leaderboard.")
    parser.add_argument("--validation-leaderboard-glob", default="outputs/**/*_study_summary.json", help="Glob for leaderboard.")
    parser.add_argument("--validation-leaderboard-csv", default="outputs/validation_leaderboard.csv", help="Leaderboard CSV path.")
    parser.add_argument("--validation-leaderboard-md", default="outputs/validation_leaderboard.md", help="Leaderboard markdown path.")

    parser.add_argument("--run-mps-benchmark", action="store_true", help="Also run torch_mlp benchmark.")
    parser.add_argument("--torch-device", default="auto", help="Torch device: auto, cpu, mps.")
    parser.add_argument("--force-raw-merge", action="store_true", help="Force raw merge before each manifest run.")
    parser.add_argument("--allow-raw-header-mismatch", action="store_true", help="Allow raw merge header mismatch.")
    parser.add_argument("--build-batch-review", action="store_true", help="Build batch review markdown after run.")
    parser.add_argument("--batch-review-output", help="Output markdown path for batch review.")
    parser.add_argument("--batch-review-author", default="Codex", help="Author for batch review markdown.")
    parser.add_argument("--batch-review-previous-summary", help="Optional previous batch summary JSON for delta comparison.")
    parser.add_argument("--batch-review-own-ship-case-f1-std-threshold", type=float, default=0.10, help="Alert threshold for own_ship_case_f1_std in batch review.")
    parser.add_argument("--batch-review-own-ship-case-f1-ci95-width-threshold", type=float, default=0.20, help="Alert threshold for own_ship_case_f1_ci95_width in batch review.")
    parser.add_argument("--batch-review-calibration-ece-threshold", type=float, default=0.15, help="Alert threshold for calibration ECE in batch review.")
    parser.add_argument("--build-batch-trend-report", action="store_true", help="Build batch trend report after run.")
    parser.add_argument("--batch-trend-output-prefix", help="Output prefix for batch trend report.")
    parser.add_argument("--batch-trend-history-glob", default="outputs/study_batch*_summary.json", help="Glob for historical batch summary JSON files.")
    parser.add_argument("--batch-trend-max-history", type=int, default=8, help="Maximum history files for batch trend report.")
    parser.add_argument("--batch-trend-moving-average-window", type=int, default=3, help="Moving-average window for trend report.")
    parser.add_argument("--batch-trend-delta-loo-f1-drop-threshold", type=float, default=0.02, help="Worsening threshold for own_ship_loo_f1 drop.")
    parser.add_argument("--batch-trend-delta-calibration-ece-rise-threshold", type=float, default=0.02, help="Worsening threshold for calibration ECE rise.")
    parser.add_argument("--batch-trend-delta-own-ship-case-std-rise-threshold", type=float, default=0.02, help="Worsening threshold for own_ship_case_f1_std rise.")
    parser.add_argument("--batch-trend-delta-own-ship-case-f1-ci95-width-rise-threshold", type=float, default=0.02, help="Worsening threshold for own_ship_case_f1_ci95_width rise.")
    parser.add_argument("--build-study-journals", action="store_true", help="Build study journal markdown for each completed dataset in batch.")
    parser.add_argument(
        "--study-journal-output-template",
        default="research_logs/{date}_{dataset_id}_study_journal.md",
        help="Output template for study journals. Supports {date} and {dataset_id}.",
    )
    parser.add_argument("--study-journal-note", help="Optional note line appended to each study journal.")
    args = parser.parse_args()

    own_ship_loo_holdout_mmsis = None
    if args.own_ship_loo_holdouts:
        own_ship_loo_holdout_mmsis = [item.strip() for item in args.own_ship_loo_holdouts.split(",") if item.strip()]
    own_ship_case_eval_mmsis = None
    if args.own_ship_case_eval_mmsis:
        own_ship_case_eval_mmsis = [item.strip() for item in args.own_ship_case_eval_mmsis.split(",") if item.strip()]
    benchmark_models = [item.strip() for item in args.benchmark_models.split(",") if item.strip()]

    summary = run_study_batch_from_manifest_glob(
        manifest_glob=args.manifest_glob,
        output_prefix=args.output_prefix,
        raw_input_template=args.raw_input_template,
        auto_merge_glob_template=args.auto_merge_glob_template,
        config_path=args.config,
        ingestion_bundle_name=args.ingestion_bundle,
        ingestion_config_path=args.ingestion_config,
        source_preset_name=args.source_preset,
        manual_column_map_text=args.column_map,
        vessel_types_text=args.vessel_types,
        output_root=args.output_root,
        max_manifests=args.max_manifests,
        continue_on_error=not bool(args.stop_on_error),
        workflow_top_n=int(args.workflow_top_n),
        workflow_min_targets=int(args.workflow_min_targets),
        pairwise_label_distance_nm=float(args.pairwise_label_distance_nm),
        pairwise_top_n_candidates=int(args.pairwise_top_n_candidates),
        pairwise_min_future_points=int(args.pairwise_min_future_points),
        pairwise_sample_every=int(args.pairwise_sample_every),
        pairwise_min_targets=int(args.pairwise_min_targets),
        pairwise_split_strategy=args.pairwise_split_strategy,
        benchmark_models=benchmark_models,
        run_error_analysis=bool(args.run_error_analysis),
        error_analysis_top_k_each=int(args.error_analysis_top_k_each),
        run_stratified_eval=bool(args.run_stratified_eval),
        run_calibration_eval=bool(args.run_calibration_eval),
        calibration_num_bins=int(args.calibration_num_bins),
        run_own_ship_loo=bool(args.run_own_ship_loo),
        own_ship_loo_holdout_mmsis=own_ship_loo_holdout_mmsis,
        run_own_ship_case_eval=bool(args.run_own_ship_case_eval),
        own_ship_case_eval_mmsis=own_ship_case_eval_mmsis,
        own_ship_case_eval_min_rows=int(args.own_ship_case_eval_min_rows),
        own_ship_case_eval_train_fraction=float(args.own_ship_case_eval_train_fraction),
        own_ship_case_eval_val_fraction=float(args.own_ship_case_eval_val_fraction),
        own_ship_case_eval_repeat_count=max(1, int(args.own_ship_case_eval_repeat_count)),
        run_validation_suite_flag=bool(args.run_validation_suite),
        update_validation_leaderboard=bool(args.update_validation_leaderboard),
        validation_leaderboard_study_glob=args.validation_leaderboard_glob,
        validation_leaderboard_csv_path=args.validation_leaderboard_csv,
        validation_leaderboard_md_path=args.validation_leaderboard_md,
        run_mps_benchmark=bool(args.run_mps_benchmark),
        torch_device=args.torch_device,
        force_raw_merge=bool(args.force_raw_merge),
        allow_raw_header_mismatch=bool(args.allow_raw_header_mismatch),
    )
    if args.build_batch_review:
        review_output = args.batch_review_output or str(
            Path("research_logs") / f"{datetime.now().date().isoformat()}_study_batch_review.md"
        )
        previous_batch_summary = None
        if args.batch_review_previous_summary:
            previous_path = Path(args.batch_review_previous_summary)
            if previous_path.exists():
                previous_batch_summary = json.loads(previous_path.read_text(encoding="utf-8"))
        review_path = build_study_batch_review_from_payload(
            batch_summary=summary,
            output_path=review_output,
            author=args.batch_review_author,
            own_ship_case_f1_std_threshold=float(args.batch_review_own_ship_case_f1_std_threshold),
            own_ship_case_f1_ci95_width_threshold=float(args.batch_review_own_ship_case_f1_ci95_width_threshold),
            calibration_ece_threshold=float(args.batch_review_calibration_ece_threshold),
            previous_batch_summary=previous_batch_summary,
        )
        print(f"batch_review={review_path}")
    if args.build_batch_trend_report:
        trend_output_prefix = args.batch_trend_output_prefix or str(
            Path("research_logs") / f"{datetime.now().date().isoformat()}_study_batch_trend"
        )
        trend_summary = build_batch_trend_report(
            output_prefix=trend_output_prefix,
            history_batch_summary_glob=args.batch_trend_history_glob,
            current_batch_summary_path=summary.get("summary_json_path"),
            max_history=int(args.batch_trend_max_history),
            own_ship_case_f1_std_threshold=float(args.batch_review_own_ship_case_f1_std_threshold),
            own_ship_case_f1_ci95_width_threshold=float(args.batch_review_own_ship_case_f1_ci95_width_threshold),
            calibration_ece_threshold=float(args.batch_review_calibration_ece_threshold),
            delta_loo_f1_drop_threshold=float(args.batch_trend_delta_loo_f1_drop_threshold),
            delta_calibration_ece_rise_threshold=float(args.batch_trend_delta_calibration_ece_rise_threshold),
            delta_own_ship_case_std_rise_threshold=float(args.batch_trend_delta_own_ship_case_std_rise_threshold),
            delta_own_ship_case_ci95_width_rise_threshold=float(
                args.batch_trend_delta_own_ship_case_f1_ci95_width_rise_threshold
            ),
            moving_average_window=int(args.batch_trend_moving_average_window),
        )
        print(f"batch_trend_summary_json={trend_summary['summary_json_path']}")
        print(f"batch_trend_summary_md={trend_summary['summary_md_path']}")
    if args.build_study_journals:
        date_text = datetime.now().date().isoformat()
        built_journal_count = 0
        for item in summary.get("items", []):
            if item.get("status") != "completed":
                continue
            study_summary_json_path = item.get("study_summary_json_path")
            if not study_summary_json_path:
                continue
            output_path = args.study_journal_output_template.format(
                date=date_text,
                dataset_id=item.get("dataset_id", "unknown_dataset"),
            )
            journal_path = build_study_journal_from_summary(
                study_summary_path=study_summary_json_path,
                output_path=output_path,
                author=args.batch_review_author,
                topic=f"{item.get('dataset_id', 'unknown_dataset')}_study_iteration",
                note=args.study_journal_note,
            )
            print(f"study_journal={journal_path}")
            built_journal_count += 1
        print(f"study_journal_count={built_journal_count}")
    print(f"status={summary['status']}")
    print(f"total_manifests={summary['total_manifests']}")
    print(f"completed_count={summary['completed_count']}")
    print(f"failed_count={summary['failed_count']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")


if __name__ == "__main__":
    main()
