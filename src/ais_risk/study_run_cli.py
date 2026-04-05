from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .dataset_manifest import infer_source_slug_from_dataset_id, parse_first_dataset_manifest
from .dma_fetch import fetch_dma_archives
from .noaa_fetch import fetch_noaa_archives
from .study_journal import build_study_journal_from_summary
from .study_run import run_dataset_study_from_manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run full dataset study from a manifest: workflow, pairwise benchmark, and research log."
    )
    parser.add_argument("--manifest", required=True, help="Dataset manifest markdown path.")
    parser.add_argument("--raw-input", help="Raw AIS CSV path. Defaults to data/raw/{source}/{dataset_id}/raw.csv.")
    parser.add_argument("--config", default="configs/base.toml", help="Project TOML config path.")
    parser.add_argument("--ingestion-bundle", help="Optional named ingestion bundle for workflow step.")
    parser.add_argument("--ingestion-config", help="Optional ingestion TOML config path.")
    parser.add_argument("--source-preset", default="auto", help="Header mapping preset for workflow preprocessing.")
    parser.add_argument("--column-map", help="Optional column overrides like mmsi=ShipId,timestamp=Event Time.")
    parser.add_argument("--vessel-types", help="Optional standardized vessel type filter for workflow preprocessing.")
    parser.add_argument("--output-root", default="outputs", help="Root directory for generated outputs.")
    parser.add_argument("--workflow-top-n", type=int, default=3, help="Top-N recommendation cases in workflow.")
    parser.add_argument("--workflow-min-targets", type=int, default=1, help="Minimum targets in workflow recommendations.")
    parser.add_argument("--pairwise-label-distance-nm", type=float, default=1.6, help="Positive label threshold on future minimum separation.")
    parser.add_argument("--pairwise-top-n-candidates", type=int, default=5, help="Top-N own-ship candidates used for pairwise dataset generation.")
    parser.add_argument("--pairwise-min-future-points", type=int, default=2, help="Minimum shared future timestamps for label creation.")
    parser.add_argument("--pairwise-sample-every", type=int, default=1, help="Use every Nth timestamp in pairwise dataset building.")
    parser.add_argument("--pairwise-min-targets", type=int, default=1, help="Minimum nearby targets required to keep own-ship timestamps.")
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
    parser.add_argument("--run-own-ship-loo", action="store_true", help="Run leave-one-own-ship-out validation after main benchmark.")
    parser.add_argument("--own-ship-loo-holdouts", help="Optional comma-separated own MMSI list for LOO holdouts.")
    parser.add_argument("--run-own-ship-case-eval", action="store_true", help="Run own-ship fixed-case repeated validation.")
    parser.add_argument("--own-ship-case-eval-mmsis", help="Optional comma-separated own MMSI list for fixed-case evaluation.")
    parser.add_argument("--own-ship-case-eval-min-rows", type=int, default=30, help="Minimum rows per own ship for fixed-case evaluation.")
    parser.add_argument("--own-ship-case-eval-train-fraction", type=float, default=0.6, help="Train fraction for own-ship case timestamp split.")
    parser.add_argument("--own-ship-case-eval-val-fraction", type=float, default=0.2, help="Validation fraction for own-ship case timestamp split.")
    parser.add_argument("--own-ship-case-eval-repeat-count", type=int, default=1, help="Repeat count for rotated timestamp split per own ship.")
    parser.add_argument("--run-validation-suite", action="store_true", help="Run unified validation suite (timestamp/own_ship/LOO) after benchmark.")
    parser.add_argument("--run-error-analysis", action="store_true", help="Run benchmark error analysis (FP/FN case extraction).")
    parser.add_argument("--error-analysis-top-k-each", type=int, default=20, help="Top-K FP and top-K FN rows per model.")
    parser.add_argument("--run-stratified-eval", action="store_true", help="Run stratified evaluation (encounter/distance bins).")
    parser.add_argument("--run-calibration-eval", action="store_true", help="Run calibration evaluation (Brier/ECE/reliability bins).")
    parser.add_argument("--calibration-num-bins", type=int, default=10, help="Reliability bin count for calibration evaluation.")
    parser.add_argument("--update-validation-leaderboard", action="store_true", help="Update cumulative validation leaderboard CSV/MD after run.")
    parser.add_argument("--validation-leaderboard-glob", default="outputs/**/*_study_summary.json", help="Glob for collecting study summaries into leaderboard.")
    parser.add_argument("--validation-leaderboard-csv", default="outputs/validation_leaderboard.csv", help="Output CSV path for leaderboard.")
    parser.add_argument("--validation-leaderboard-md", default="outputs/validation_leaderboard.md", help="Output markdown path for leaderboard.")
    parser.add_argument("--run-mps-benchmark", action="store_true", help="Also run torch_mlp benchmark (uses torch-device).")
    parser.add_argument("--torch-device", default="auto", help="Torch device for optional MPS benchmark: auto, cpu, or mps.")
    parser.add_argument("--random-seed", type=int, default=42, help="Base random seed for reproducible training/evaluation.")
    parser.add_argument("--auto-merge-glob", help="Optional CSV glob for auto-building raw.csv when raw-input is missing.")
    parser.add_argument("--force-raw-merge", action="store_true", help="Force raw CSV rebuild from --auto-merge-glob before study run.")
    parser.add_argument("--allow-raw-header-mismatch", action="store_true", help="Allow raw merge with differing headers.")
    parser.add_argument("--raw-merge-summary-json", help="Optional path to save raw merge summary JSON.")
    parser.add_argument("--fetch-dma", action="store_true", help="Fetch DMA zip archives before running the study.")
    parser.add_argument("--fetch-noaa", action="store_true", help="Fetch NOAA zip archives before running the study.")
    parser.add_argument("--fetch-output-dir", help="Override fetch output dir (default: data/raw/{source}/{dataset_id}/downloads).")
    parser.add_argument("--fetch-base-url", help="Base URL for selected fetch provider.")
    parser.add_argument(
        "--fetch-fallback-base-urls",
        help="Optional comma-separated fallback base URLs for archive fetch retry.",
    )
    parser.add_argument(
        "--fetch-filename-template",
        help=(
            "Archive filename template. DMA default: aisdk-{date}.zip. "
            "NOAA default: AIS_{year}_{month}_{day}.zip."
        ),
    )
    parser.add_argument(
        "--fetch-year-dir-template",
        default="{year}",
        help="NOAA year-directory template (default: {year}). Ignored for DMA fetch.",
    )
    parser.add_argument("--fetch-timeout-sec", type=int, default=90, help="Archive download timeout seconds per attempt.")
    parser.add_argument("--fetch-max-attempts", type=int, default=3, help="Archive max retry attempts per candidate URL.")
    parser.add_argument("--fetch-extract", action="store_true", help="Extract downloaded zip files.")
    parser.add_argument("--fetch-dry-run", action="store_true", help="Only plan archive fetch URLs, do not download.")
    parser.add_argument("--fetch-no-skip-existing", action="store_true", help="Re-download existing archive zip files.")
    parser.add_argument("--fetch-summary-json", help="Optional path to save archive fetch summary JSON.")
    parser.add_argument("--build-study-journal", action="store_true", help="Build study journal markdown after study run.")
    parser.add_argument("--study-journal-output", help="Optional output path for study journal markdown.")
    parser.add_argument("--study-journal-topic", help="Optional topic for study journal title.")
    parser.add_argument("--study-journal-note", help="Optional note line appended to study journal.")
    args = parser.parse_args()

    manifest_info = parse_first_dataset_manifest(args.manifest)
    dataset_id = str(manifest_info["dataset_id"])
    source_slug = infer_source_slug_from_dataset_id(dataset_id)
    default_raw_input = Path("data/raw") / source_slug / dataset_id / "raw.csv"
    raw_input_path = args.raw_input or str(default_raw_input)

    fetch_output_dir = args.fetch_output_dir or str(Path("data/raw") / source_slug / dataset_id / "downloads")
    fallback_base_urls = []
    if args.fetch_fallback_base_urls:
        fallback_base_urls = [item.strip() for item in args.fetch_fallback_base_urls.split(",") if item.strip()]
    fetch_summary: dict[str, object] | None = None
    fetch_provider = ""
    if args.fetch_dma and args.fetch_noaa:
        raise ValueError("Choose exactly one fetch provider: --fetch-dma or --fetch-noaa")
    if args.fetch_dma:
        fetch_provider = "dma"
        start_date = manifest_info.get("start_date")
        end_date = manifest_info.get("end_date")
        if not start_date or not end_date:
            raise ValueError(
                "fetch-dma requires 시작 시각/종료 시각 in manifest or explicit date arguments in a separate fetch step."
            )
        dma_base_url = args.fetch_base_url or "https://web.ais.dk/aisdata"
        dma_filename_template = args.fetch_filename_template or "aisdk-{date}.zip"
        fetch_summary = fetch_dma_archives(
            start_date=str(start_date),
            end_date=str(end_date),
            output_dir=fetch_output_dir,
            base_url=dma_base_url,
            fallback_base_urls=fallback_base_urls,
            filename_template=dma_filename_template,
            extract=bool(args.fetch_extract),
            dry_run=bool(args.fetch_dry_run),
            skip_existing=not bool(args.fetch_no_skip_existing),
            timeout_sec=max(1, int(args.fetch_timeout_sec)),
            max_attempts=max(1, int(args.fetch_max_attempts)),
        )
    elif args.fetch_noaa:
        fetch_provider = "noaa"
        start_date = manifest_info.get("start_date")
        end_date = manifest_info.get("end_date")
        if not start_date or not end_date:
            raise ValueError(
                "fetch-noaa requires 시작 시각/종료 시각 in manifest or explicit date arguments in a separate fetch step."
            )
        noaa_base_url = args.fetch_base_url or "https://coast.noaa.gov/htdata/CMSP/AISDataHandler"
        noaa_filename_template = args.fetch_filename_template or "AIS_{year}_{month}_{day}.zip"
        fetch_summary = fetch_noaa_archives(
            start_date=str(start_date),
            end_date=str(end_date),
            output_dir=fetch_output_dir,
            base_url=noaa_base_url,
            fallback_base_urls=fallback_base_urls,
            year_dir_template=args.fetch_year_dir_template,
            filename_template=noaa_filename_template,
            extract=bool(args.fetch_extract),
            dry_run=bool(args.fetch_dry_run),
            skip_existing=not bool(args.fetch_no_skip_existing),
            timeout_sec=max(1, int(args.fetch_timeout_sec)),
            max_attempts=max(1, int(args.fetch_max_attempts)),
        )
    if fetch_summary is not None and args.fetch_summary_json:
        fetch_summary_path = Path(args.fetch_summary_json)
        fetch_summary_path.parent.mkdir(parents=True, exist_ok=True)
        fetch_summary_path.write_text(json.dumps(fetch_summary, indent=2), encoding="utf-8")

    resolved_auto_merge_glob = args.auto_merge_glob
    if resolved_auto_merge_glob is None and (args.fetch_dma or args.fetch_noaa):
        resolved_auto_merge_glob = str(Path(fetch_output_dir) / "**/*.csv")
    own_ship_loo_holdouts = None
    if args.own_ship_loo_holdouts:
        own_ship_loo_holdouts = [item.strip() for item in args.own_ship_loo_holdouts.split(",") if item.strip()]
    own_ship_case_eval_mmsis = None
    if args.own_ship_case_eval_mmsis:
        own_ship_case_eval_mmsis = [item.strip() for item in args.own_ship_case_eval_mmsis.split(",") if item.strip()]
    benchmark_models = [item.strip() for item in args.benchmark_models.split(",") if item.strip()]

    summary = run_dataset_study_from_manifest(
        manifest_path=args.manifest,
        raw_input_path=raw_input_path,
        config_path=args.config,
        ingestion_bundle_name=args.ingestion_bundle,
        ingestion_config_path=args.ingestion_config,
        source_preset_name=args.source_preset,
        manual_column_map_text=args.column_map,
        vessel_types_text=args.vessel_types,
        output_root=args.output_root,
        workflow_top_n=int(args.workflow_top_n),
        workflow_min_targets=int(args.workflow_min_targets),
        pairwise_label_distance_nm=float(args.pairwise_label_distance_nm),
        pairwise_top_n_candidates=int(args.pairwise_top_n_candidates),
        pairwise_min_future_points=int(args.pairwise_min_future_points),
        pairwise_sample_every=int(args.pairwise_sample_every),
        pairwise_min_targets=int(args.pairwise_min_targets),
        pairwise_split_strategy=args.pairwise_split_strategy,
        benchmark_models=benchmark_models,
        run_own_ship_loo=bool(args.run_own_ship_loo),
        own_ship_loo_holdout_mmsis=own_ship_loo_holdouts,
        run_own_ship_case_eval=bool(args.run_own_ship_case_eval),
        own_ship_case_eval_mmsis=own_ship_case_eval_mmsis,
        own_ship_case_eval_min_rows=int(args.own_ship_case_eval_min_rows),
        own_ship_case_eval_train_fraction=float(args.own_ship_case_eval_train_fraction),
        own_ship_case_eval_val_fraction=float(args.own_ship_case_eval_val_fraction),
        own_ship_case_eval_repeat_count=max(1, int(args.own_ship_case_eval_repeat_count)),
        run_validation_suite_flag=bool(args.run_validation_suite),
        run_error_analysis=bool(args.run_error_analysis),
        error_analysis_top_k_each=int(args.error_analysis_top_k_each),
        run_stratified_eval=bool(args.run_stratified_eval),
        run_calibration_eval=bool(args.run_calibration_eval),
        calibration_num_bins=int(args.calibration_num_bins),
        update_validation_leaderboard=bool(args.update_validation_leaderboard),
        validation_leaderboard_study_glob=args.validation_leaderboard_glob,
        validation_leaderboard_csv_path=args.validation_leaderboard_csv,
        validation_leaderboard_md_path=args.validation_leaderboard_md,
        run_mps_benchmark=bool(args.run_mps_benchmark),
        torch_device=args.torch_device,
        random_seed=int(args.random_seed),
        auto_merge_input_glob=resolved_auto_merge_glob,
        force_raw_merge=bool(args.force_raw_merge),
        allow_raw_header_mismatch=bool(args.allow_raw_header_mismatch),
        raw_merge_summary_path=args.raw_merge_summary_json,
    )
    print(f"dataset_id={summary['dataset_id']}")
    print(f"raw_input={summary['raw_input_path']}")
    print(f"study_summary_json={summary['summary_json_path']}")
    print(f"study_summary_md={summary['summary_md_path']}")
    print(f"workflow_summary_json={summary['workflow']['summary_json_path']}")
    print(f"pairwise_dataset={summary['pairwise']['dataset_path']}")
    print(f"benchmark_summary_json={summary['benchmark']['summary_json_path']}")
    print(f"research_log={summary['research_log_path']}")
    print(f"pairwise_split_strategy={summary['pairwise_split_strategy']}")
    if summary.get("error_analysis_summary_json_path"):
        print(f"error_analysis_summary_json={summary['error_analysis_summary_json_path']}")
        print(f"error_analysis_cases_csv={summary['error_analysis_cases_csv_path']}")
    if summary.get("stratified_eval_summary_json_path"):
        print(f"stratified_eval_summary_json={summary['stratified_eval_summary_json_path']}")
        print(f"stratified_eval_metrics_csv={summary['stratified_eval_metrics_csv_path']}")
    if summary.get("calibration_eval_summary_json_path"):
        print(f"calibration_eval_summary_json={summary['calibration_eval_summary_json_path']}")
        print(f"calibration_eval_bins_csv={summary['calibration_eval_bins_csv_path']}")
    if summary.get("own_ship_loo_summary_json_path"):
        print(f"own_ship_loo_summary_json={summary['own_ship_loo_summary_json_path']}")
        print(f"own_ship_loo_fold_metrics_csv={summary['own_ship_loo_fold_metrics_csv_path']}")
    if summary.get("own_ship_case_eval_summary_json_path"):
        print(f"own_ship_case_eval_summary_json={summary['own_ship_case_eval_summary_json_path']}")
        print(f"own_ship_case_eval_ship_metrics_csv={summary['own_ship_case_eval_ship_metrics_csv_path']}")
        print(f"own_ship_case_eval_repeat_metrics_csv={summary.get('own_ship_case_eval_repeat_metrics_csv_path', '')}")
    if summary.get("validation_suite_summary_json_path"):
        print(f"validation_suite_summary_json={summary['validation_suite_summary_json_path']}")
        print(f"validation_suite_summary_md={summary['validation_suite_summary_md_path']}")
    if summary.get("validation_leaderboard_csv_path"):
        print(f"validation_leaderboard_csv={summary['validation_leaderboard_csv_path']}")
        print(f"validation_leaderboard_md={summary['validation_leaderboard_md_path']}")
    if fetch_summary is not None:
        if args.fetch_summary_json:
            print(f"fetch_summary_json={args.fetch_summary_json}")
        if fetch_provider:
            print(f"fetch_provider={fetch_provider}")
        print(f"fetch_status={fetch_summary['status']}")
        print(f"fetch_planned={fetch_summary['planned_count']}")
        print(f"fetch_downloaded={fetch_summary['downloaded_count']}")
        print(f"fetch_skipped={fetch_summary['skipped_count']}")
        print(f"fetch_failed={fetch_summary['failed_count']}")
        print(f"fetch_timeout_sec={max(1, int(args.fetch_timeout_sec))}")
        print(f"fetch_max_attempts={max(1, int(args.fetch_max_attempts))}")
        if fallback_base_urls:
            print(f"fetch_fallback_base_urls={','.join(fallback_base_urls)}")
    if summary.get("mps_benchmark_summary_json_path"):
        print(f"mps_benchmark_summary_json={summary['mps_benchmark_summary_json_path']}")
    if args.build_study_journal:
        journal_output = args.study_journal_output
        if not journal_output:
            journal_output = str(
                Path("research_logs")
                / f"{date.today().isoformat()}_{summary.get('dataset_id', 'unknown_dataset')}_study_journal.md"
            )
        journal_path = build_study_journal_from_summary(
            study_summary_path=summary["summary_json_path"],
            output_path=journal_output,
            author="Codex",
            topic=args.study_journal_topic,
            note=args.study_journal_note,
        )
        print(f"study_journal={journal_path}")


if __name__ == "__main__":
    main()
