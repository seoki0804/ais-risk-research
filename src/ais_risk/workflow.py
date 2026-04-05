from __future__ import annotations

import json
from pathlib import Path

from .config import load_config
from .csv_tools import load_curated_csv_rows, preprocess_ais_csv
from .demo_package import build_recommended_demo_package_from_csv
from .ingestion_bundles import resolve_ingestion_bundle
from .own_ship_candidates import recommend_own_ship_candidates_rows, save_own_ship_candidates
from .profile import profile_curated_rows, save_profile_outputs
from .schema_probe import inspect_csv_schema, save_schema_probe
from .source_presets import resolve_source_preset
from .trajectory import reconstruct_trajectory_csv


def build_workflow_summary_markdown(summary: dict[str, object]) -> str:
    top_recommendation = summary.get("top_recommendation") or {}
    time_range = summary["profile_overview"]["time_range"]
    return f"""# Ingestion Workflow Summary

## Inputs

- Raw input: `{summary['raw_input_path']}`
- Project config: `{summary['project_config_path']}`
- Output directory: `{summary['output_dir']}`
- Radius: `{summary['radius_nm']:.1f}` NM
- Top-N cases: `{summary['top_n']}`
- Minimum targets: `{summary['min_targets']}`

## Resolved Ingestion

- Bundle name: `{summary['resolved_ingestion']['bundle_name'] or 'none'}`
- Bundle config path: `{summary['resolved_ingestion']['bundle_config_path'] or 'none'}`
- Source preset: `{summary['resolved_ingestion']['source_preset']}`
- Vessel types: `{', '.join(summary['resolved_ingestion']['vessel_types']) or 'none'}`
- Column map: `{summary['resolved_ingestion']['column_map_text'] or 'auto'}`

## Schema And Preprocess

- Schema ready: `{summary['schema_ready_for_preprocess']}`
- Missing required: `{', '.join(summary['schema_missing_required']) or 'none'}`
- Curated rows: `{summary['preprocess_stats']['output_rows']}`
- Unique vessels: `{summary['preprocess_stats']['unique_vessels']}`
- Track rows: `{summary['trajectory_stats']['output_rows']}`
- Interpolated rows: `{summary['trajectory_stats']['interpolated_rows']}`

## Dataset Profile

- Time range: `{time_range['start']}` to `{time_range['end']}`
- Profile row count: `{summary['profile_overview']['row_count']}`
- Profile unique vessels: `{summary['profile_overview']['unique_vessels']}`

## Recommendations

- Recommendation count: `{summary['recommendation_count']}`
- Top own ship: `{top_recommendation.get('mmsi', 'none')}`
- Top timestamp: `{top_recommendation.get('recommended_timestamp', 'none')}`
- Top candidate score: `{float(top_recommendation.get('candidate_score', 0.0)):.3f}`

## Outputs

- Schema probe: `{summary['schema_probe_path']}`
- Curated CSV: `{summary['curated_csv_path']}`
- Tracks CSV: `{summary['tracks_csv_path']}`
- Own-ship candidates: `{summary['own_ship_candidates_path']}`
- Demo package manifest: `{summary['demo_package_manifest_path']}`
- Demo package master report: `{summary['demo_package_master_report_path']}`
"""


def run_ingestion_workflow(
    input_path: str | Path,
    output_dir: str | Path,
    project_config_path: str | Path = "configs/base.toml",
    ingestion_bundle_name: str | None = None,
    ingestion_config_path: str | Path | None = None,
    source_preset_name: str | None = "auto",
    manual_column_map_text: str | None = None,
    vessel_types_text: str | None = None,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    split_gap_minutes: float = 10.0,
    max_interp_gap_minutes: float = 2.0,
    step_seconds: int = 30,
    schema_sample_size: int = 50,
    radius_nm: float | None = None,
    top_n: int = 3,
    min_targets: int = 1,
) -> dict[str, object]:
    raw_input_path = Path(input_path)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    config = load_config(project_config_path)
    effective_radius_nm = float(config.grid.radius_nm) if radius_nm is None else float(radius_nm)
    resolved_bundle = resolve_ingestion_bundle(
        bundle_name=ingestion_bundle_name,
        config_path=ingestion_config_path,
        source_preset_name=source_preset_name,
        manual_column_map_text=manual_column_map_text,
        vessel_types_text=vessel_types_text,
    )
    column_overrides = resolve_source_preset(
        str(resolved_bundle["source_preset"]),
        str(resolved_bundle["column_map_text"]),
    )

    schema_probe = inspect_csv_schema(
        raw_input_path,
        sample_size=int(schema_sample_size),
        column_overrides=column_overrides,
    )
    schema_probe_path = save_schema_probe(output_root / "schema_probe.json", schema_probe)
    if not schema_probe["ready_for_preprocess"]:
        missing = ", ".join(schema_probe["missing_required"]) or "unknown"
        raise ValueError(f"Schema probe failed. Missing required columns: {missing}")

    curated_csv_path = output_root / "curated.csv"
    preprocess_stats = preprocess_ais_csv(
        input_path=raw_input_path,
        output_path=curated_csv_path,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
        start_time=start_time,
        end_time=end_time,
        allowed_vessel_types=set(resolved_bundle["vessel_types"]) or None,
        column_overrides=column_overrides,
    )

    tracks_csv_path = output_root / "tracks.csv"
    trajectory_stats = reconstruct_trajectory_csv(
        input_path=curated_csv_path,
        output_path=tracks_csv_path,
        split_gap_minutes=split_gap_minutes,
        max_interp_gap_minutes=max_interp_gap_minutes,
        step_seconds=step_seconds,
    )

    track_rows = load_curated_csv_rows(tracks_csv_path)
    profile = profile_curated_rows(track_rows)
    profile_json_path, profile_md_path = save_profile_outputs(output_root / "dataset", profile)

    recommendations = recommend_own_ship_candidates_rows(
        rows=track_rows,
        config=config,
        radius_nm=effective_radius_nm,
        top_n=top_n,
        min_targets=min_targets,
    )
    if not recommendations:
        raise ValueError("No own-ship recommendation candidates were produced from the reconstructed tracks.")

    own_ship_candidates_path = output_root / "own_ship_candidates.csv"
    save_own_ship_candidates(own_ship_candidates_path, recommendations)

    demo_package_dir = output_root / "demo_package"
    demo_package_manifest = build_recommended_demo_package_from_csv(
        input_path=tracks_csv_path,
        config=config,
        output_dir=demo_package_dir,
        radius_nm=effective_radius_nm,
        top_n=top_n,
        min_targets=min_targets,
    )

    summary = {
        "status": "completed",
        "raw_input_path": str(raw_input_path),
        "project_config_path": str(project_config_path),
        "output_dir": str(output_root),
        "radius_nm": effective_radius_nm,
        "top_n": int(top_n),
        "min_targets": int(min_targets),
        "resolved_ingestion": {
            "bundle_name": resolved_bundle["bundle_name"],
            "bundle_description": resolved_bundle["bundle_description"],
            "bundle_config_path": resolved_bundle["bundle_config_path"],
            "source_preset": resolved_bundle["source_preset"],
            "column_map_text": resolved_bundle["column_map_text"],
            "vessel_types": list(resolved_bundle["vessel_types"]),
            "notes": list(resolved_bundle["notes"]),
        },
        "schema_ready_for_preprocess": bool(schema_probe["ready_for_preprocess"]),
        "schema_missing_required": list(schema_probe["missing_required"]),
        "schema_probe_path": str(schema_probe_path),
        "curated_csv_path": str(curated_csv_path),
        "tracks_csv_path": str(tracks_csv_path),
        "profile_json_path": str(profile_json_path),
        "profile_md_path": str(profile_md_path),
        "own_ship_candidates_path": str(own_ship_candidates_path),
        "preprocess_stats": preprocess_stats,
        "trajectory_stats": trajectory_stats,
        "profile_overview": {
            "row_count": profile["row_count"],
            "unique_vessels": profile["unique_vessels"],
            "time_range": profile["time_range"],
        },
        "recommendation_count": len(recommendations),
        "top_recommendation": recommendations[0],
        "demo_package_dir": str(demo_package_dir),
        "demo_package_case_count": int(demo_package_manifest["case_count"]),
        "demo_package_manifest_path": str(demo_package_manifest["manifest_path"]),
        "demo_package_index_path": str(demo_package_manifest["index_path"]),
        "demo_package_summary_path": str(demo_package_manifest["summary_path"]),
        "demo_package_master_report_path": str(demo_package_manifest["master_report_path"]),
        "demo_package_figure_bundle_manifest_path": str(demo_package_manifest["figure_bundle_manifest_path"]),
        "demo_package_figure_bundle_html_path": str(demo_package_manifest["figure_bundle_html_path"]),
        "demo_package_figure_bundle_md_path": str(demo_package_manifest["figure_bundle_md_path"]),
        "demo_package_paper_assets_manifest_path": str(demo_package_manifest["paper_assets_manifest_path"]),
        "demo_package_artifact_catalog_path": str(demo_package_manifest["artifact_catalog_md_path"]),
        "demo_package_artifact_catalog_ko_path": str(demo_package_manifest["artifact_catalog_ko_md_path"]),
        "demo_package_audience_guide_path": str(demo_package_manifest["audience_guide_path"]),
        "demo_package_audience_guide_ko_path": str(demo_package_manifest["audience_guide_ko_path"]),
        "demo_package_handoff_checklist_path": str(demo_package_manifest["handoff_checklist_path"]),
        "demo_package_handoff_checklist_ko_path": str(demo_package_manifest["handoff_checklist_ko_path"]),
        "demo_package_deliverable_readiness_path": str(demo_package_manifest["deliverable_readiness_path"]),
        "demo_package_deliverable_readiness_ko_path": str(demo_package_manifest["deliverable_readiness_ko_path"]),
        "demo_package_paper_case_table_path": str(demo_package_manifest["paper_case_csv_path"]),
        "demo_package_paper_scenario_table_path": str(demo_package_manifest["paper_scenario_csv_path"]),
        "demo_package_paper_ablation_table_path": str(demo_package_manifest["paper_ablation_csv_path"]),
        "demo_package_paper_case_latex_path": str(demo_package_manifest["paper_case_tex_path"]),
        "demo_package_paper_scenario_latex_path": str(demo_package_manifest["paper_scenario_tex_path"]),
        "demo_package_paper_ablation_latex_path": str(demo_package_manifest["paper_ablation_tex_path"]),
        "demo_package_paper_claim_matrix_path": str(demo_package_manifest["paper_claim_matrix_md_path"]),
        "demo_package_paper_claim_matrix_ko_path": str(demo_package_manifest["paper_claim_matrix_ko_md_path"]),
        "demo_package_paper_reviewer_faq_path": str(demo_package_manifest["paper_reviewer_faq_path"]),
        "demo_package_paper_reviewer_faq_ko_path": str(demo_package_manifest["paper_reviewer_faq_ko_path"]),
        "demo_package_presentation_outline_path": str(demo_package_manifest["presentation_outline_path"]),
        "demo_package_presentation_outline_ko_path": str(demo_package_manifest["presentation_outline_ko_path"]),
        "demo_package_demo_talk_track_path": str(demo_package_manifest["demo_talk_track_path"]),
        "demo_package_demo_talk_track_ko_path": str(demo_package_manifest["demo_talk_track_ko_path"]),
        "demo_package_defense_packet_path": str(demo_package_manifest["defense_packet_path"]),
        "demo_package_defense_packet_ko_path": str(demo_package_manifest["defense_packet_ko_path"]),
        "demo_package_portfolio_case_study_path": str(demo_package_manifest["portfolio_case_study_path"]),
        "demo_package_portfolio_case_study_ko_path": str(demo_package_manifest["portfolio_case_study_ko_path"]),
        "demo_package_interview_answer_bank_path": str(demo_package_manifest["interview_answer_bank_path"]),
        "demo_package_interview_answer_bank_ko_path": str(demo_package_manifest["interview_answer_bank_ko_path"]),
        "demo_package_advisor_review_pack_path": str(demo_package_manifest["advisor_review_pack_path"]),
        "demo_package_reviewer_pack_path": str(demo_package_manifest["reviewer_pack_path"]),
        "demo_package_interview_pack_path": str(demo_package_manifest["interview_pack_path"]),
        "demo_package_portfolio_pack_path": str(demo_package_manifest["portfolio_pack_path"]),
        "demo_package_paper_captions_path": str(demo_package_manifest["paper_figure_captions_path"]),
        "demo_package_paper_captions_ko_path": str(demo_package_manifest["paper_figure_captions_ko_path"]),
        "demo_package_paper_summary_path": str(demo_package_manifest["paper_summary_note_path"]),
        "demo_package_paper_summary_ko_path": str(demo_package_manifest["paper_summary_note_ko_path"]),
        "demo_package_paper_full_draft_path": str(demo_package_manifest["paper_full_draft_path"]),
        "demo_package_paper_full_draft_ko_path": str(demo_package_manifest["paper_full_draft_ko_path"]),
        "demo_package_paper_full_draft_tex_path": str(demo_package_manifest["paper_full_draft_tex_path"]),
        "demo_package_paper_results_path": str(demo_package_manifest["paper_results_section_path"]),
        "demo_package_paper_results_ko_path": str(demo_package_manifest["paper_results_section_ko_path"]),
        "demo_package_paper_results_tex_path": str(demo_package_manifest["paper_results_section_tex_path"]),
        "demo_package_paper_methods_path": str(demo_package_manifest["paper_methods_section_path"]),
        "demo_package_paper_methods_ko_path": str(demo_package_manifest["paper_methods_section_ko_path"]),
        "demo_package_paper_methods_tex_path": str(demo_package_manifest["paper_methods_section_tex_path"]),
        "demo_package_paper_discussion_path": str(demo_package_manifest["paper_discussion_section_path"]),
        "demo_package_paper_discussion_ko_path": str(demo_package_manifest["paper_discussion_section_ko_path"]),
        "demo_package_paper_discussion_tex_path": str(demo_package_manifest["paper_discussion_section_tex_path"]),
        "demo_package_paper_appendix_md_path": str(demo_package_manifest["paper_appendix_md_path"]),
        "demo_package_paper_appendix_ko_md_path": str(demo_package_manifest["paper_appendix_ko_md_path"]),
        "demo_package_paper_appendix_tex_path": str(demo_package_manifest["paper_appendix_tex_path"]),
    }
    summary_json_path = output_root / "workflow_summary.json"
    summary_md_path = output_root / "workflow_summary.md"
    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_md_path"] = str(summary_md_path)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_workflow_summary_markdown(summary), encoding="utf-8")
    return summary
