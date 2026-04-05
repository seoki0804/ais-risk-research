from __future__ import annotations

import glob
import json
from pathlib import Path
from typing import Any

from .dataset_manifest import parse_first_dataset_manifest
from .study_run import run_dataset_study_from_manifest


class _SafeFormatDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _format_template(template: str, variables: dict[str, str]) -> str:
    return template.format_map(_SafeFormatDict(variables))


def _resolve_manifest_paths(manifest_glob: str, max_manifests: int | None = None) -> list[Path]:
    paths = sorted(Path(path) for path in glob.glob(manifest_glob))
    if max_manifests is not None:
        paths = paths[: max(0, int(max_manifests))]
    return paths


def build_study_batch_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Study Batch Summary",
        "",
        "## Inputs",
        "",
        f"- manifest_glob: `{summary['manifest_glob']}`",
        f"- ingestion_bundle: `{summary.get('ingestion_bundle_name', 'none') or 'none'}`",
        f"- ingestion_config: `{summary.get('ingestion_config_path', 'none') or 'none'}`",
        f"- source_preset: `{summary.get('source_preset_name', 'auto')}`",
        f"- column_map: `{summary.get('manual_column_map_text', 'auto') or 'auto'}`",
        f"- vessel_types: `{summary.get('vessel_types_text', 'none') or 'none'}`",
        f"- max_manifests: `{summary.get('max_manifests', 'n/a')}`",
        f"- total manifests: `{summary['total_manifests']}`",
        f"- completed: `{summary['completed_count']}`",
        f"- failed: `{summary['failed_count']}`",
        "",
        "## Results",
        "",
        "| # | dataset_id | status | pairwise_rows | positive_rate | study_summary_json |",
        "|---|---|---|---:|---:|---|",
    ]
    for index, item in enumerate(summary.get("items", []), start=1):
        pairwise_rows = item.get("pairwise_row_count")
        pairwise_positive_rate = item.get("pairwise_positive_rate")
        pairwise_rows_text = str(pairwise_rows) if pairwise_rows is not None else "n/a"
        if isinstance(pairwise_positive_rate, float):
            positive_rate_text = f"{pairwise_positive_rate:.4f}"
        else:
            positive_rate_text = "n/a"
        lines.append(
            "| {index} | {dataset_id} | {status} | {rows} | {pr} | `{path}` |".format(
                index=index,
                dataset_id=item.get("dataset_id", "unknown"),
                status=item.get("status", "unknown"),
                rows=pairwise_rows_text,
                pr=positive_rate_text,
                path=item.get("study_summary_json_path", "n/a"),
            )
        )

    failures = [item for item in summary.get("items", []) if item.get("status") == "failed"]
    if failures:
        lines.extend(["", "## Failures", ""])
        for item in failures:
            lines.append(f"- `{item.get('dataset_id', 'unknown')}`: `{item.get('error', 'n/a')}`")
    lines.append("")
    return "\n".join(lines)


def run_study_batch_from_manifest_glob(
    manifest_glob: str,
    output_prefix: str | Path,
    raw_input_template: str = "data/raw/{source_slug}/{dataset_id}/raw.csv",
    auto_merge_glob_template: str | None = None,
    config_path: str | Path = "configs/base.toml",
    ingestion_bundle_name: str | None = None,
    ingestion_config_path: str | Path | None = None,
    source_preset_name: str | None = "auto",
    manual_column_map_text: str | None = None,
    vessel_types_text: str | None = None,
    output_root: str | Path = "outputs",
    max_manifests: int | None = None,
    continue_on_error: bool = True,
    workflow_top_n: int = 3,
    workflow_min_targets: int = 1,
    pairwise_label_distance_nm: float = 1.6,
    pairwise_top_n_candidates: int = 5,
    pairwise_min_future_points: int = 2,
    pairwise_sample_every: int = 1,
    pairwise_min_targets: int = 1,
    pairwise_split_strategy: str = "timestamp",
    benchmark_models: list[str] | None = None,
    run_error_analysis: bool = False,
    error_analysis_top_k_each: int = 20,
    run_stratified_eval: bool = False,
    run_calibration_eval: bool = False,
    calibration_num_bins: int = 10,
    run_own_ship_loo: bool = False,
    own_ship_loo_holdout_mmsis: list[str] | None = None,
    run_own_ship_case_eval: bool = False,
    own_ship_case_eval_mmsis: list[str] | None = None,
    own_ship_case_eval_min_rows: int = 30,
    own_ship_case_eval_train_fraction: float = 0.6,
    own_ship_case_eval_val_fraction: float = 0.2,
    own_ship_case_eval_repeat_count: int = 1,
    run_validation_suite_flag: bool = False,
    update_validation_leaderboard: bool = False,
    validation_leaderboard_study_glob: str = "outputs/**/*_study_summary.json",
    validation_leaderboard_csv_path: str | Path = "outputs/validation_leaderboard.csv",
    validation_leaderboard_md_path: str | Path = "outputs/validation_leaderboard.md",
    run_mps_benchmark: bool = False,
    torch_device: str = "auto",
    force_raw_merge: bool = False,
    allow_raw_header_mismatch: bool = False,
) -> dict[str, Any]:
    manifest_paths = _resolve_manifest_paths(manifest_glob, max_manifests=max_manifests)
    if not manifest_paths:
        raise ValueError(f"No manifest files matched glob: {manifest_glob}")

    items: list[dict[str, Any]] = []
    completed_count = 0
    failed_count = 0
    for manifest_path in manifest_paths:
        manifest_info = parse_first_dataset_manifest(manifest_path)
        dataset_id = str(manifest_info["dataset_id"])
        source_slug = str(manifest_info.get("source_slug") or "dma")
        variables = {
            "dataset_id": dataset_id,
            "source_slug": source_slug,
            "manifest_path": str(manifest_path),
        }
        raw_input_path = _format_template(raw_input_template, variables)
        auto_merge_glob = (
            _format_template(auto_merge_glob_template, variables) if auto_merge_glob_template is not None else None
        )
        raw_merge_summary_path = None
        if auto_merge_glob is not None:
            raw_merge_summary_path = str(Path(output_root) / f"{dataset_id}_raw_merge.json")

        try:
            result = run_dataset_study_from_manifest(
                manifest_path=manifest_path,
                raw_input_path=raw_input_path,
                config_path=config_path,
                ingestion_bundle_name=ingestion_bundle_name,
                ingestion_config_path=ingestion_config_path,
                source_preset_name=source_preset_name,
                manual_column_map_text=manual_column_map_text,
                vessel_types_text=vessel_types_text,
                output_root=output_root,
                workflow_top_n=int(workflow_top_n),
                workflow_min_targets=int(workflow_min_targets),
                pairwise_label_distance_nm=float(pairwise_label_distance_nm),
                pairwise_top_n_candidates=int(pairwise_top_n_candidates),
                pairwise_min_future_points=int(pairwise_min_future_points),
                pairwise_sample_every=int(pairwise_sample_every),
                pairwise_min_targets=int(pairwise_min_targets),
                pairwise_split_strategy=pairwise_split_strategy,
                benchmark_models=benchmark_models,
                run_error_analysis=bool(run_error_analysis),
                error_analysis_top_k_each=int(error_analysis_top_k_each),
                run_stratified_eval=bool(run_stratified_eval),
                run_calibration_eval=bool(run_calibration_eval),
                calibration_num_bins=int(calibration_num_bins),
                run_own_ship_loo=bool(run_own_ship_loo),
                own_ship_loo_holdout_mmsis=own_ship_loo_holdout_mmsis,
                run_own_ship_case_eval=bool(run_own_ship_case_eval),
                own_ship_case_eval_mmsis=own_ship_case_eval_mmsis,
                own_ship_case_eval_min_rows=int(own_ship_case_eval_min_rows),
                own_ship_case_eval_train_fraction=float(own_ship_case_eval_train_fraction),
                own_ship_case_eval_val_fraction=float(own_ship_case_eval_val_fraction),
                own_ship_case_eval_repeat_count=max(1, int(own_ship_case_eval_repeat_count)),
                run_validation_suite_flag=bool(run_validation_suite_flag),
                update_validation_leaderboard=bool(update_validation_leaderboard),
                validation_leaderboard_study_glob=validation_leaderboard_study_glob,
                validation_leaderboard_csv_path=validation_leaderboard_csv_path,
                validation_leaderboard_md_path=validation_leaderboard_md_path,
                run_mps_benchmark=bool(run_mps_benchmark),
                torch_device=torch_device,
                auto_merge_input_glob=auto_merge_glob,
                force_raw_merge=bool(force_raw_merge),
                allow_raw_header_mismatch=bool(allow_raw_header_mismatch),
                raw_merge_summary_path=raw_merge_summary_path,
            )
            completed_count += 1
            items.append(
                {
                    "manifest_path": str(manifest_path),
                    "dataset_id": dataset_id,
                    "status": "completed",
                    "raw_input_path": raw_input_path,
                    "auto_merge_glob": auto_merge_glob,
                    "study_summary_json_path": result.get("summary_json_path"),
                    "study_summary_md_path": result.get("summary_md_path"),
                    "pairwise_row_count": result.get("pairwise", {}).get("row_count"),
                    "pairwise_positive_rate": result.get("pairwise", {}).get("positive_rate"),
                    "benchmark_models": result.get("benchmark_models"),
                    "stratified_eval_summary_json_path": result.get("stratified_eval_summary_json_path"),
                    "calibration_eval_summary_json_path": result.get("calibration_eval_summary_json_path"),
                    "own_ship_case_eval_summary_json_path": result.get("own_ship_case_eval_summary_json_path"),
                    "own_ship_case_eval_repeat_metrics_csv_path": result.get("own_ship_case_eval_repeat_metrics_csv_path"),
                    "research_log_path": result.get("research_log_path"),
                }
            )
        except Exception as exc:
            failed_count += 1
            failure_payload = {
                "manifest_path": str(manifest_path),
                "dataset_id": dataset_id,
                "status": "failed",
                "raw_input_path": raw_input_path,
                "auto_merge_glob": auto_merge_glob,
                "error": repr(exc),
            }
            items.append(failure_payload)
            if not continue_on_error:
                break

    summary: dict[str, Any] = {
        "status": "completed",
        "manifest_glob": manifest_glob,
        "ingestion_bundle_name": ingestion_bundle_name or "",
        "ingestion_config_path": str(ingestion_config_path) if ingestion_config_path else "",
        "source_preset_name": source_preset_name or "auto",
        "manual_column_map_text": manual_column_map_text or "",
        "vessel_types_text": vessel_types_text or "",
        "max_manifests": max_manifests,
        "continue_on_error": bool(continue_on_error),
        "total_manifests": len(manifest_paths),
        "completed_count": completed_count,
        "failed_count": failed_count,
        "items": items,
    }

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_study_batch_summary_markdown(summary), encoding="utf-8")
    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_md_path"] = str(summary_md_path)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
