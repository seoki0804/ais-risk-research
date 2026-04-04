"""Baseline AIS risk mapping starter package."""

from .config import load_config
from .dataset_manifest import build_dataset_id, build_first_dataset_manifest_markdown, save_first_dataset_manifest
from .dma_fetch import fetch_dma_archives
from .noaa_fetch import fetch_noaa_archives
from .noaa_focus_pairwise_bundle import run_noaa_focus_pairwise_bundle
from .benchmark import run_pairwise_benchmark
from .batch_review import build_study_batch_review_from_summary, build_study_batch_review_from_payload
from .batch_trend import build_batch_trend_report
from .focus_compare import run_focus_vs_baseline_sweep_bundle
from .focus_rank_compare import run_focus_rank_compare_bundle
from .focus_mmsi_compare import run_focus_mmsi_compare_bundle
from .focus_seed_compare import run_focus_seed_compare_bundle
from .focus_seed_pipeline import run_focus_seed_pipeline
from .governed_selection import build_governed_selection_matrix
from .scenario_threshold_sweep import run_scenario_threshold_sweep
from .scenario_threshold_tuning import run_scenario_threshold_tuning
from .scenario_threshold_stability import build_scenario_threshold_stability_report
from .calibration_eval import run_calibration_evaluation
from .uncertainty_band import run_uncertainty_band
from .prediction_grid_projection import run_prediction_grid_projection
from .uncertainty_contour_report import build_uncertainty_contour_report
from .error_analysis import run_benchmark_error_analysis
from .csv_tools import (
    build_snapshot_from_curated_csv,
    build_snapshot_from_curated_rows,
    load_curated_csv_rows,
    parse_column_overrides,
    preprocess_ais_csv,
)
from .demo_package import build_recommended_demo_package
from .experiments import run_ablation_experiment, run_baseline_experiment
from .ingestion_bundles import (
    get_ingestion_bundle,
    list_ingestion_bundle_names,
    load_ingestion_bundle_config,
    resolve_ingestion_bundle,
)
from .io import load_snapshot
from .own_ship_case_eval import run_own_ship_case_evaluation
from .own_ship_candidates import rank_own_ship_candidates_rows, recommend_own_ship_candidates_rows
from .paper_assets import build_paper_assets_from_manifest, build_paper_assets_from_manifest_path
from .pairwise_dataset import build_pairwise_learning_dataset_from_csv
from .pipeline import run_snapshot
from .profile import profile_curated_rows
from .research_log import build_benchmark_research_log
from .raw_merge import merge_raw_csv_files
from .schema_probe import inspect_csv_schema
from .source_presets import get_source_preset, list_source_preset_names, resolve_source_preset
from .source_probe import list_public_source_ids, run_public_source_probe
from .study_run import run_dataset_study_from_manifest
from .study_batch import run_study_batch_from_manifest_glob
from .study_journal import build_study_journal_from_summary
from .study_sweep import run_study_modelset_sweep, parse_benchmark_modelsets
from .all_models import run_all_supported_models
from .all_models_seed_sweep import run_all_models_seed_sweep
from .scenario_shift_eval import run_scenario_shift_multi_snapshot
from .sweep_compare import compare_study_sweep_summaries
from .stratified_eval import run_stratified_evaluation
from .validation_suite import run_validation_suite
from .validation_leaderboard import build_validation_leaderboard
from .trajectory import reconstruct_trajectory_csv
from .vessel_types import normalize_vessel_type
from .workflow import run_ingestion_workflow

__all__ = [
    "build_snapshot_from_curated_csv",
    "build_snapshot_from_curated_rows",
    "build_recommended_demo_package",
    "build_dataset_id",
    "build_first_dataset_manifest_markdown",
    "save_first_dataset_manifest",
    "fetch_dma_archives",
    "fetch_noaa_archives",
    "run_noaa_focus_pairwise_bundle",
    "build_pairwise_learning_dataset_from_csv",
    "get_ingestion_bundle",
    "load_config",
    "load_curated_csv_rows",
    "load_ingestion_bundle_config",
    "load_snapshot",
    "list_ingestion_bundle_names",
    "inspect_csv_schema",
    "get_source_preset",
    "list_source_preset_names",
    "list_public_source_ids",
    "run_own_ship_case_evaluation",
    "build_paper_assets_from_manifest",
    "build_paper_assets_from_manifest_path",
    "build_benchmark_research_log",
    "merge_raw_csv_files",
    "normalize_vessel_type",
    "parse_column_overrides",
    "rank_own_ship_candidates_rows",
    "recommend_own_ship_candidates_rows",
    "resolve_ingestion_bundle",
    "resolve_source_preset",
    "run_public_source_probe",
    "profile_curated_rows",
    "preprocess_ais_csv",
    "run_pairwise_benchmark",
    "build_batch_trend_report",
    "run_focus_vs_baseline_sweep_bundle",
    "run_focus_rank_compare_bundle",
    "run_focus_mmsi_compare_bundle",
    "run_focus_seed_compare_bundle",
    "run_focus_seed_pipeline",
    "build_governed_selection_matrix",
    "run_scenario_threshold_sweep",
    "run_scenario_threshold_tuning",
    "build_scenario_threshold_stability_report",
    "run_calibration_evaluation",
    "run_uncertainty_band",
    "run_prediction_grid_projection",
    "build_uncertainty_contour_report",
    "run_benchmark_error_analysis",
    "build_study_batch_review_from_summary",
    "build_study_batch_review_from_payload",
    "run_ablation_experiment",
    "run_ingestion_workflow",
    "run_dataset_study_from_manifest",
    "run_study_batch_from_manifest_glob",
    "build_study_journal_from_summary",
    "run_study_modelset_sweep",
    "parse_benchmark_modelsets",
    "run_all_supported_models",
    "run_all_models_seed_sweep",
    "run_scenario_shift_multi_snapshot",
    "compare_study_sweep_summaries",
    "run_stratified_evaluation",
    "run_validation_suite",
    "build_validation_leaderboard",
    "run_baseline_experiment",
    "reconstruct_trajectory_csv",
    "run_snapshot",
]
