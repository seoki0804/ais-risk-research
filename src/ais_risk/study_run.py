from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .benchmark import run_pairwise_benchmark
from .calibration_eval import run_calibration_evaluation
from .config import load_config
from .dataset_manifest import parse_first_dataset_manifest
from .error_analysis import run_benchmark_error_analysis
from .own_ship_case_eval import run_own_ship_case_evaluation
from .own_ship_cv import run_leave_one_own_ship_out_benchmark
from .pairwise_dataset import build_pairwise_learning_dataset_from_csv
from .raw_merge import merge_raw_csv_files
from .research_log import build_benchmark_research_log
from .stratified_eval import run_stratified_evaluation
from .validation_suite import run_validation_suite
from .validation_leaderboard import build_validation_leaderboard
from .workflow import run_ingestion_workflow


def parse_dataset_manifest(path: str | Path) -> dict[str, str]:
    parsed = parse_first_dataset_manifest(path)
    return {
        "dataset_id": str(parsed["dataset_id"]),
        "area": str(parsed.get("area", "TBD")),
        "manifest_path": str(parsed["manifest_path"]),
        "start_date": str(parsed.get("start_date") or ""),
        "end_date": str(parsed.get("end_date") or ""),
        "source_slug": str(parsed.get("source_slug") or ""),
    }


def build_study_run_summary_markdown(summary: dict[str, Any]) -> str:
    benchmark = summary["benchmark"]
    raw_merge = summary.get("raw_merge")
    return f"""# Dataset Study Run Summary

## Inputs

- dataset_id: `{summary['dataset_id']}`
- manifest: `{summary['manifest_path']}`
- period: `{summary.get('start_date', 'n/a')} ~ {summary.get('end_date', 'n/a')}`
- raw input: `{summary['raw_input_path']}`
- config: `{summary['config_path']}`
- ingestion bundle: `{summary.get('ingestion_bundle_name', 'none') or 'none'}`
- ingestion config: `{summary.get('ingestion_config_path', 'none') or 'none'}`
- source preset: `{summary.get('ingestion_source_preset', 'auto')}`
- column map: `{summary.get('ingestion_column_map_text', 'auto') or 'auto'}`
- vessel types: `{summary.get('ingestion_vessel_types_text', 'none') or 'none'}`

## Raw Merge

- auto merge glob: `{summary.get('raw_auto_merge_glob', 'n/a')}`
- raw merge executed: `{bool(raw_merge)}`
- raw merge rows: `{raw_merge['output_rows'] if raw_merge else 'n/a'}`
- raw merge summary path: `{summary.get('raw_merge_summary_path', 'n/a')}`

## Workflow

- workflow summary: `{summary['workflow']['summary_json_path']}`
- tracks csv: `{summary['workflow']['tracks_csv_path']}`
- own ship candidates: `{summary['workflow']['own_ship_candidates_path']}`

## Pairwise Dataset

- pairwise dataset: `{summary['pairwise']['dataset_path']}`
- pairwise stats: `{summary['pairwise']['stats_path']}`
- row count: `{summary['pairwise']['row_count']}`
- positive rate: `{float(summary['pairwise']['positive_rate']):.4f}`

## Benchmark

- benchmark summary json: `{benchmark['summary_json_path']}`
- benchmark summary md: `{benchmark['summary_md_path']}`
- predictions csv: `{benchmark['predictions_csv_path']}`
- models: `{", ".join(summary['benchmark_models'])}`
- split strategy: `{summary.get('pairwise_split_strategy', 'timestamp')}`
- random seed: `{summary.get('random_seed', 'n/a')}`

## Error Analysis

- enabled: `{summary.get('error_analysis_enabled', False)}`
- summary json: `{summary.get('error_analysis_summary_json_path', 'n/a')}`
- summary md: `{summary.get('error_analysis_summary_md_path', 'n/a')}`
- cases csv: `{summary.get('error_analysis_cases_csv_path', 'n/a')}`

## Stratified Evaluation

- enabled: `{summary.get('stratified_eval_enabled', False)}`
- summary json: `{summary.get('stratified_eval_summary_json_path', 'n/a')}`
- summary md: `{summary.get('stratified_eval_summary_md_path', 'n/a')}`
- strata metrics csv: `{summary.get('stratified_eval_metrics_csv_path', 'n/a')}`

## Calibration Evaluation

- enabled: `{summary.get('calibration_eval_enabled', False)}`
- summary json: `{summary.get('calibration_eval_summary_json_path', 'n/a')}`
- summary md: `{summary.get('calibration_eval_summary_md_path', 'n/a')}`
- bins csv: `{summary.get('calibration_eval_bins_csv_path', 'n/a')}`

## Own-Ship LOO Validation

- enabled: `{summary.get('own_ship_loo_enabled', False)}`
- summary json: `{summary.get('own_ship_loo_summary_json_path', 'n/a')}`
- summary md: `{summary.get('own_ship_loo_summary_md_path', 'n/a')}`
- fold metrics csv: `{summary.get('own_ship_loo_fold_metrics_csv_path', 'n/a')}`

## Own-Ship Case Evaluation

- enabled: `{summary.get('own_ship_case_eval_enabled', False)}`
- summary json: `{summary.get('own_ship_case_eval_summary_json_path', 'n/a')}`
- summary md: `{summary.get('own_ship_case_eval_summary_md_path', 'n/a')}`
- ship metrics csv: `{summary.get('own_ship_case_eval_ship_metrics_csv_path', 'n/a')}`
- repeat metrics csv: `{summary.get('own_ship_case_eval_repeat_metrics_csv_path', 'n/a')}`
- repeat count: `{summary.get('own_ship_case_eval_repeat_count', 'n/a')}`

## Validation Suite

- enabled: `{summary.get('validation_suite_enabled', False)}`
- summary json: `{summary.get('validation_suite_summary_json_path', 'n/a')}`
- summary md: `{summary.get('validation_suite_summary_md_path', 'n/a')}`

## Validation Leaderboard

- updated: `{summary.get('validation_leaderboard_updated', False)}`
- leaderboard csv: `{summary.get('validation_leaderboard_csv_path', 'n/a')}`
- leaderboard md: `{summary.get('validation_leaderboard_md_path', 'n/a')}`

## Research Log

- log markdown: `{summary['research_log_path']}`

## Optional MPS Benchmark

- enabled: `{summary['mps_benchmark_enabled']}`
- summary path: `{summary.get('mps_benchmark_summary_json_path', 'n/a')}`
"""


def run_dataset_study_from_manifest(
    manifest_path: str | Path,
    raw_input_path: str | Path,
    config_path: str | Path = "configs/base.toml",
    ingestion_bundle_name: str | None = None,
    ingestion_config_path: str | Path | None = None,
    source_preset_name: str | None = "auto",
    manual_column_map_text: str | None = None,
    vessel_types_text: str | None = None,
    output_root: str | Path = "outputs",
    workflow_top_n: int = 3,
    workflow_min_targets: int = 1,
    pairwise_label_distance_nm: float = 1.6,
    pairwise_top_n_candidates: int = 5,
    pairwise_min_future_points: int = 2,
    pairwise_sample_every: int = 1,
    pairwise_min_targets: int = 1,
    pairwise_split_strategy: str = "timestamp",
    benchmark_models: list[str] | None = None,
    run_own_ship_loo: bool = False,
    own_ship_loo_holdout_mmsis: list[str] | None = None,
    run_validation_suite_flag: bool = False,
    run_error_analysis: bool = False,
    error_analysis_top_k_each: int = 20,
    run_stratified_eval: bool = False,
    run_calibration_eval: bool = False,
    calibration_num_bins: int = 10,
    run_own_ship_case_eval: bool = False,
    own_ship_case_eval_mmsis: list[str] | None = None,
    own_ship_case_eval_min_rows: int = 30,
    own_ship_case_eval_train_fraction: float = 0.6,
    own_ship_case_eval_val_fraction: float = 0.2,
    own_ship_case_eval_repeat_count: int = 1,
    update_validation_leaderboard: bool = False,
    validation_leaderboard_study_glob: str = "outputs/**/*_study_summary.json",
    validation_leaderboard_csv_path: str | Path = "outputs/validation_leaderboard.csv",
    validation_leaderboard_md_path: str | Path = "outputs/validation_leaderboard.md",
    run_mps_benchmark: bool = False,
    torch_device: str = "auto",
    random_seed: int | None = 42,
    auto_merge_input_glob: str | None = None,
    force_raw_merge: bool = False,
    allow_raw_header_mismatch: bool = False,
    raw_merge_summary_path: str | Path | None = None,
) -> dict[str, Any]:
    manifest_info = parse_dataset_manifest(manifest_path)
    dataset_id = manifest_info["dataset_id"]
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    raw_input = Path(raw_input_path)
    resolved_merge_glob = auto_merge_input_glob
    if resolved_merge_glob is None and dataset_id.startswith("dma_"):
        resolved_merge_glob = f"data/raw/dma/{dataset_id}/downloads/**/*.csv"

    raw_merge_summary: dict[str, Any] | None = None
    if force_raw_merge:
        if not resolved_merge_glob:
            raise ValueError("force_raw_merge=True requires auto_merge_input_glob or dma dataset_id.")
        raw_merge_summary = merge_raw_csv_files(
            input_glob=resolved_merge_glob,
            output_path=raw_input,
            require_header_match=not allow_raw_header_mismatch,
        )
    elif not raw_input.exists():
        if not resolved_merge_glob:
            raise FileNotFoundError(
                f"Raw input not found: {raw_input}. "
                "Provide auto_merge_input_glob or place a raw.csv at the requested path."
            )
        raw_merge_summary = merge_raw_csv_files(
            input_glob=resolved_merge_glob,
            output_path=raw_input,
            require_header_match=not allow_raw_header_mismatch,
        )

    if raw_merge_summary is not None and raw_merge_summary_path is not None:
        raw_merge_summary_file = Path(raw_merge_summary_path)
        raw_merge_summary_file.parent.mkdir(parents=True, exist_ok=True)
        raw_merge_summary_file.write_text(json.dumps(raw_merge_summary, indent=2), encoding="utf-8")

    workflow_output_dir = output_root_path / f"{dataset_id}_workflow"
    workflow_summary = run_ingestion_workflow(
        input_path=raw_input,
        output_dir=workflow_output_dir,
        project_config_path=config_path,
        ingestion_bundle_name=ingestion_bundle_name,
        ingestion_config_path=ingestion_config_path,
        source_preset_name=source_preset_name,
        manual_column_map_text=manual_column_map_text,
        vessel_types_text=vessel_types_text,
        top_n=int(workflow_top_n),
        min_targets=int(workflow_min_targets),
    )

    config = load_config(config_path)
    pairwise_dataset_path = output_root_path / f"{dataset_id}_pairwise_dataset.csv"
    pairwise_stats_path = output_root_path / f"{dataset_id}_pairwise_dataset_stats.json"
    pairwise_payload = build_pairwise_learning_dataset_from_csv(
        input_path=workflow_summary["tracks_csv_path"],
        output_path=pairwise_dataset_path,
        config=config,
        own_candidates_path=workflow_summary["own_ship_candidates_path"],
        top_n_candidates=int(pairwise_top_n_candidates),
        label_distance_nm=float(pairwise_label_distance_nm),
        sample_every_nth_timestamp=max(1, int(pairwise_sample_every)),
        min_future_points=max(1, int(pairwise_min_future_points)),
        min_targets=max(1, int(pairwise_min_targets)),
        stats_output_path=pairwise_stats_path,
    )

    benchmark_prefix = output_root_path / f"{dataset_id}_pairwise_benchmark"
    benchmark_models = [str(item).strip() for item in (benchmark_models or ["rule_score", "logreg", "hgbt"]) if str(item).strip()]
    if not benchmark_models:
        raise ValueError("benchmark_models must include at least one model.")
    benchmark_summary = run_pairwise_benchmark(
        input_path=pairwise_dataset_path,
        output_prefix=benchmark_prefix,
        model_names=benchmark_models,
        split_strategy=pairwise_split_strategy,
        torch_device=torch_device,
        random_seed=random_seed,
    )

    mps_benchmark_summary: dict[str, Any] | None = None
    if run_mps_benchmark:
        mps_prefix = output_root_path / f"{dataset_id}_pairwise_benchmark_mps"
        mps_models = benchmark_models.copy()
        if "torch_mlp" not in mps_models:
            mps_models.append("torch_mlp")
        mps_benchmark_summary = run_pairwise_benchmark(
            input_path=pairwise_dataset_path,
            output_prefix=mps_prefix,
            model_names=mps_models,
            split_strategy=pairwise_split_strategy,
            torch_device=torch_device,
            random_seed=random_seed,
        )

    error_analysis_summary: dict[str, Any] | None = None
    if run_error_analysis:
        error_analysis_summary = run_benchmark_error_analysis(
            predictions_csv_path=benchmark_summary["predictions_csv_path"],
            output_prefix=output_root_path / f"{dataset_id}_pairwise_error_analysis",
            model_names=benchmark_models,
            top_k_each=int(error_analysis_top_k_each),
        )

    stratified_eval_summary: dict[str, Any] | None = None
    if run_stratified_eval:
        stratified_eval_summary = run_stratified_evaluation(
            pairwise_dataset_csv_path=pairwise_dataset_path,
            predictions_csv_path=benchmark_summary["predictions_csv_path"],
            output_prefix=output_root_path / f"{dataset_id}_pairwise_stratified_eval",
            model_names=benchmark_models,
        )

    calibration_eval_summary: dict[str, Any] | None = None
    if run_calibration_eval:
        calibration_eval_summary = run_calibration_evaluation(
            predictions_csv_path=benchmark_summary["predictions_csv_path"],
            output_prefix=output_root_path / f"{dataset_id}_pairwise_calibration_eval",
            model_names=benchmark_models,
            num_bins=int(calibration_num_bins),
        )

    validation_models = benchmark_models.copy()
    if run_mps_benchmark and "torch_mlp" not in validation_models:
        validation_models.append("torch_mlp")

    own_ship_loo_summary: dict[str, Any] | None = None
    if run_own_ship_loo:
        own_ship_loo_summary = run_leave_one_own_ship_out_benchmark(
            input_path=pairwise_dataset_path,
            output_prefix=output_root_path / f"{dataset_id}_pairwise_benchmark",
            model_names=validation_models,
            holdout_own_mmsis=own_ship_loo_holdout_mmsis,
            torch_device=torch_device,
            random_seed=random_seed,
        )

    own_ship_case_eval_summary: dict[str, Any] | None = None
    if run_own_ship_case_eval:
        own_ship_case_eval_summary = run_own_ship_case_evaluation(
            input_path=pairwise_dataset_path,
            output_prefix=output_root_path / f"{dataset_id}_pairwise_own_ship_case_eval",
            model_names=validation_models,
            own_mmsis=own_ship_case_eval_mmsis,
            min_rows_per_ship=int(own_ship_case_eval_min_rows),
            train_fraction=float(own_ship_case_eval_train_fraction),
            val_fraction=float(own_ship_case_eval_val_fraction),
            repeat_count=max(1, int(own_ship_case_eval_repeat_count)),
            torch_device=torch_device,
            random_seed=random_seed,
        )

    validation_suite_summary: dict[str, Any] | None = None
    if run_validation_suite_flag:
        validation_suite_summary = run_validation_suite(
            input_path=pairwise_dataset_path,
            output_prefix=output_root_path / f"{dataset_id}_pairwise_validation_suite",
            model_names=validation_models,
            torch_device=torch_device,
            own_ship_loo_holdout_mmsis=own_ship_loo_holdout_mmsis,
            random_seed=random_seed,
        )

    validation_leaderboard_summary: dict[str, Any] | None = None
    if update_validation_leaderboard:
        validation_leaderboard_summary = build_validation_leaderboard(
            study_summary_glob=validation_leaderboard_study_glob,
            output_csv_path=validation_leaderboard_csv_path,
            output_md_path=validation_leaderboard_md_path,
            sort_by="own_ship_loo_f1_mean",
            descending=True,
        )

    log_path = Path("research_logs") / f"{date.today().isoformat()}_{dataset_id}_benchmark.md"
    research_log_path = build_benchmark_research_log(
        benchmark_summary_path=benchmark_summary["summary_json_path"],
        pairwise_stats_path=pairwise_payload.get("stats_path", str(pairwise_stats_path)),
        dataset_manifest_path=manifest_path,
        output_path=log_path,
        date_text=date.today().isoformat(),
        topic=f"{dataset_id}_benchmark",
        area_text=manifest_info["area"],
        config_text=str(config_path),
    )

    summary: dict[str, Any] = {
        "status": "completed",
        "dataset_id": dataset_id,
        "manifest_path": str(manifest_path),
        "start_date": manifest_info.get("start_date"),
        "end_date": manifest_info.get("end_date"),
        "source_slug": manifest_info.get("source_slug"),
        "raw_input_path": str(raw_input),
        "config_path": str(config_path),
        "ingestion_bundle_name": ingestion_bundle_name or "",
        "ingestion_config_path": str(ingestion_config_path) if ingestion_config_path else "",
        "ingestion_source_preset": source_preset_name or "auto",
        "ingestion_column_map_text": manual_column_map_text or "",
        "ingestion_vessel_types_text": vessel_types_text or "",
        "output_root": str(output_root_path),
        "raw_auto_merge_glob": resolved_merge_glob,
        "workflow": workflow_summary,
        "pairwise": {
            "dataset_path": pairwise_payload["dataset_path"],
            "stats_path": pairwise_payload.get("stats_path", str(pairwise_stats_path)),
            "row_count": pairwise_payload["row_count"],
            "positive_rate": pairwise_payload["positive_rate"],
            "positive_rows": pairwise_payload["positive_rows"],
            "negative_rows": pairwise_payload["negative_rows"],
        },
        "benchmark": benchmark_summary,
        "benchmark_models": benchmark_models,
        "validation_models_effective": validation_models,
        "pairwise_split_strategy": pairwise_split_strategy,
        "random_seed": random_seed,
        "error_analysis_enabled": bool(run_error_analysis),
        "stratified_eval_enabled": bool(run_stratified_eval),
        "calibration_eval_enabled": bool(run_calibration_eval),
        "own_ship_loo_enabled": bool(run_own_ship_loo),
        "own_ship_case_eval_enabled": bool(run_own_ship_case_eval),
        "own_ship_case_eval_repeat_count": max(1, int(own_ship_case_eval_repeat_count)),
        "validation_suite_enabled": bool(run_validation_suite_flag),
        "validation_leaderboard_updated": bool(update_validation_leaderboard),
        "mps_benchmark_enabled": bool(run_mps_benchmark),
        "research_log_path": str(research_log_path),
    }
    if raw_merge_summary is not None:
        summary["raw_merge"] = raw_merge_summary
    if raw_merge_summary is not None and raw_merge_summary_path is not None:
        summary["raw_merge_summary_path"] = str(raw_merge_summary_path)
    if mps_benchmark_summary is not None:
        summary["mps_benchmark_summary_json_path"] = mps_benchmark_summary["summary_json_path"]
        summary["mps_benchmark_summary_md_path"] = mps_benchmark_summary["summary_md_path"]
        summary["mps_benchmark_predictions_csv_path"] = mps_benchmark_summary["predictions_csv_path"]
    if error_analysis_summary is not None:
        summary["error_analysis_summary_json_path"] = error_analysis_summary["summary_json_path"]
        summary["error_analysis_summary_md_path"] = error_analysis_summary["summary_md_path"]
        summary["error_analysis_cases_csv_path"] = error_analysis_summary["error_cases_csv_path"]
    if stratified_eval_summary is not None:
        summary["stratified_eval_summary_json_path"] = stratified_eval_summary["summary_json_path"]
        summary["stratified_eval_summary_md_path"] = stratified_eval_summary["summary_md_path"]
        summary["stratified_eval_metrics_csv_path"] = stratified_eval_summary["strata_metrics_csv_path"]
    if calibration_eval_summary is not None:
        summary["calibration_eval_summary_json_path"] = calibration_eval_summary["summary_json_path"]
        summary["calibration_eval_summary_md_path"] = calibration_eval_summary["summary_md_path"]
        summary["calibration_eval_bins_csv_path"] = calibration_eval_summary["calibration_bins_csv_path"]
    if own_ship_loo_summary is not None:
        summary["own_ship_loo_summary_json_path"] = own_ship_loo_summary["summary_json_path"]
        summary["own_ship_loo_summary_md_path"] = own_ship_loo_summary["summary_md_path"]
        summary["own_ship_loo_fold_metrics_csv_path"] = own_ship_loo_summary["fold_metrics_csv_path"]
    if own_ship_case_eval_summary is not None:
        summary["own_ship_case_eval_summary_json_path"] = own_ship_case_eval_summary["summary_json_path"]
        summary["own_ship_case_eval_summary_md_path"] = own_ship_case_eval_summary["summary_md_path"]
        summary["own_ship_case_eval_ship_metrics_csv_path"] = own_ship_case_eval_summary["ship_metrics_csv_path"]
        summary["own_ship_case_eval_repeat_metrics_csv_path"] = own_ship_case_eval_summary["repeat_metrics_csv_path"]
    if validation_suite_summary is not None:
        summary["validation_suite_summary_json_path"] = validation_suite_summary["summary_json_path"]
        summary["validation_suite_summary_md_path"] = validation_suite_summary["summary_md_path"]
    if validation_leaderboard_summary is not None:
        summary["validation_leaderboard_csv_path"] = validation_leaderboard_summary["output_csv_path"]
        summary["validation_leaderboard_md_path"] = validation_leaderboard_summary["output_md_path"]

    summary_json_path = output_root_path / f"{dataset_id}_study_summary.json"
    summary_md_path = output_root_path / f"{dataset_id}_study_summary.md"
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_study_run_summary_markdown(summary), encoding="utf-8")
    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_md_path"] = str(summary_md_path)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
