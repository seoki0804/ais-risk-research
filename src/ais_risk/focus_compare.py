from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .study_sweep import run_study_modelset_sweep
from .sweep_compare import compare_study_sweep_summaries
from .workflow import run_ingestion_workflow


def _resolve_journal_template(template: str | None, sweep_type: str) -> str:
    if template is None or not str(template).strip():
        return f"research_logs/{{date}}_{{dataset_id}}_{{modelset_index}}_{sweep_type}_study_journal.md"
    text = str(template)
    if "{sweep_type}" in text:
        return text.replace("{sweep_type}", sweep_type)
    if text.endswith(".md"):
        return f"{text[:-3]}_{sweep_type}.md"
    return f"{text}_{sweep_type}"


def _select_focus_mmsi_from_candidates(
    own_ship_candidates_path: str | Path | None,
    requested_rank: int,
) -> tuple[str | None, int | None]:
    if not own_ship_candidates_path:
        return None, None
    path = Path(str(own_ship_candidates_path))
    if not path.exists():
        return None, None
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    if not rows:
        return None, None
    rank_index = max(1, int(requested_rank)) - 1
    if rank_index >= len(rows):
        rank_index = 0
    selected = rows[rank_index]
    mmsi = str(selected.get("mmsi") or "").strip()
    if not mmsi:
        return None, None
    return mmsi, int(rank_index + 1)


def _load_summary_json(path_value: str | Path) -> dict[str, Any]:
    path = Path(str(path_value))
    if not path.exists():
        raise ValueError(f"Summary JSON does not exist: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Failed to read summary JSON: {path}") from exc


def _resolve_focus_mmsis(
    focus_own_ship_case_eval_mmsis: list[str] | None,
    auto_focus_own_ship: bool,
    auto_focus_rank: int,
    raw_input_path: str | Path,
    config_path: str | Path,
    ingestion_bundle_name: str | None,
    ingestion_config_path: str | Path | None,
    source_preset_name: str | None,
    manual_column_map_text: str | None,
    vessel_types_text: str | None,
    auto_focus_workflow_output_dir: str | Path,
) -> tuple[list[str], dict[str, Any]]:
    focus_mmsis = [item.strip() for item in (focus_own_ship_case_eval_mmsis or []) if str(item).strip()]
    if focus_mmsis:
        return focus_mmsis, {
            "mode": "manual",
            "requested_rank": None,
            "selected_rank": None,
            "selected_mmsi": focus_mmsis[0],
            "workflow_summary_json_path": "",
            "own_ship_candidates_path": "",
        }
    if not auto_focus_own_ship:
        raise ValueError("focus_own_ship_case_eval_mmsis is empty. Provide MMSI list or enable auto_focus_own_ship.")

    requested_rank = max(1, int(auto_focus_rank))
    workflow_summary = run_ingestion_workflow(
        input_path=raw_input_path,
        output_dir=auto_focus_workflow_output_dir,
        project_config_path=config_path,
        ingestion_bundle_name=ingestion_bundle_name,
        ingestion_config_path=ingestion_config_path,
        source_preset_name=source_preset_name,
        manual_column_map_text=manual_column_map_text,
        vessel_types_text=vessel_types_text,
        top_n=max(3, requested_rank),
        min_targets=1,
    )

    selected_mmsi, selected_rank = _select_focus_mmsi_from_candidates(
        own_ship_candidates_path=workflow_summary.get("own_ship_candidates_path"),
        requested_rank=requested_rank,
    )
    if not selected_mmsi:
        top = workflow_summary.get("top_recommendation", {})
        selected_mmsi = str(top.get("mmsi") or "").strip()
        selected_rank = 1 if selected_mmsi else None
    if not selected_mmsi:
        raise ValueError("auto_focus_own_ship=True but no own-ship candidate MMSI was found.")

    return [selected_mmsi], {
        "mode": "auto_top_candidate",
        "requested_rank": requested_rank,
        "selected_rank": selected_rank,
        "selected_mmsi": selected_mmsi,
        "workflow_summary_json_path": workflow_summary.get("summary_json_path", ""),
        "own_ship_candidates_path": workflow_summary.get("own_ship_candidates_path", ""),
    }


def build_focus_vs_baseline_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Focus vs Baseline Sweep Bundle",
        "",
        "## Inputs",
        "",
        f"- manifest_path: `{summary.get('manifest_path', 'n/a')}`",
        f"- raw_input_path: `{summary.get('raw_input_path', 'n/a')}`",
        f"- pairwise_split_strategy: `{summary.get('pairwise_split_strategy', 'n/a')}`",
        f"- focus_own_ship_case_eval_mmsis: `{summary.get('focus_own_ship_case_eval_mmsis', [])}`",
        f"- focus_mmsi_resolution_mode: `{summary.get('focus_mmsi_resolution_mode', 'manual')}`",
        f"- focus_mmsi_requested_rank: `{summary.get('focus_mmsi_requested_rank', 'n/a')}`",
        f"- focus_mmsi_selected_rank: `{summary.get('focus_mmsi_selected_rank', 'n/a')}`",
        f"- focus_mmsi_auto_workflow_summary_json: `{summary.get('focus_mmsi_auto_workflow_summary_json_path', 'n/a')}`",
        f"- random_seed: `{summary.get('random_seed', 'n/a')}`",
        f"- baseline_reused: `{summary.get('baseline_reused', False)}`",
        f"- baseline_reuse_source_summary_json: `{summary.get('baseline_reuse_source_summary_json_path', '') or 'n/a'}`",
        f"- benchmark_modelsets: `{summary.get('benchmark_modelsets', [])}`",
        "",
        "## Outputs",
        "",
        f"- focus_sweep_summary_json: `{summary.get('focus_sweep_summary_json_path', 'n/a')}`",
        f"- baseline_sweep_summary_json: `{summary.get('baseline_sweep_summary_json_path', 'n/a')}`",
        f"- compare_summary_json: `{summary.get('compare_summary_json_path', 'n/a')}`",
        f"- compare_summary_md: `{summary.get('compare_summary_md_path', 'n/a')}`",
        "",
        "## Quick Summary",
        "",
        f"- focus_modelset_count: `{summary.get('focus_modelset_count', 0)}`",
        f"- baseline_modelset_count: `{summary.get('baseline_modelset_count', 0)}`",
        f"- compared_modelset_count: `{summary.get('compared_modelset_count', 0)}`",
        "",
    ]
    return "\n".join(lines)


def run_focus_vs_baseline_sweep_bundle(
    manifest_path: str | Path,
    raw_input_path: str | Path,
    output_prefix: str | Path,
    focus_own_ship_case_eval_mmsis: list[str] | None,
    benchmark_modelsets: list[list[str]],
    config_path: str | Path = "configs/base.toml",
    ingestion_bundle_name: str | None = None,
    ingestion_config_path: str | Path | None = None,
    source_preset_name: str | None = "auto",
    manual_column_map_text: str | None = None,
    vessel_types_text: str | None = None,
    output_root: str | Path = "outputs/focus_vs_baseline",
    pairwise_split_strategy: str = "own_ship",
    run_calibration_eval: bool = True,
    run_own_ship_loo: bool = True,
    run_own_ship_case_eval: bool = True,
    own_ship_case_eval_min_rows: int = 30,
    own_ship_case_eval_repeat_count: int = 3,
    build_study_journals: bool = False,
    study_journal_output_template: str | None = None,
    study_journal_note: str | None = None,
    torch_device: str = "auto",
    compare_epsilon: float = 1e-9,
    focus_label: str = "focused_single_own_ship",
    baseline_label: str = "baseline_multi_own_ship",
    auto_focus_own_ship: bool = False,
    auto_focus_rank: int = 1,
    baseline_sweep_summary_json_path: str | Path | None = None,
    random_seed: int | None = 42,
) -> dict[str, Any]:
    bundle_root = Path(output_root)
    focus_root = bundle_root / "focus_runs"
    baseline_root = bundle_root / "baseline_runs"
    auto_focus_workflow_root = bundle_root / "auto_focus_workflow"
    focus_root.mkdir(parents=True, exist_ok=True)
    baseline_root.mkdir(parents=True, exist_ok=True)

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    focus_sweep_prefix = prefix.with_name(f"{prefix.name}_focus_sweep")
    baseline_sweep_prefix = prefix.with_name(f"{prefix.name}_baseline_sweep")
    compare_prefix = prefix.with_name(f"{prefix.name}_compare")

    focus_journal_template = _resolve_journal_template(study_journal_output_template, "focus")
    baseline_journal_template = _resolve_journal_template(study_journal_output_template, "baseline")
    focus_mmsis, focus_resolution = _resolve_focus_mmsis(
        focus_own_ship_case_eval_mmsis=focus_own_ship_case_eval_mmsis,
        auto_focus_own_ship=bool(auto_focus_own_ship),
        auto_focus_rank=max(1, int(auto_focus_rank)),
        raw_input_path=raw_input_path,
        config_path=config_path,
        ingestion_bundle_name=ingestion_bundle_name,
        ingestion_config_path=ingestion_config_path,
        source_preset_name=source_preset_name,
        manual_column_map_text=manual_column_map_text,
        vessel_types_text=vessel_types_text,
        auto_focus_workflow_output_dir=auto_focus_workflow_root,
    )

    focus_summary = run_study_modelset_sweep(
        manifest_path=manifest_path,
        raw_input_path=raw_input_path,
        output_prefix=focus_sweep_prefix,
        benchmark_modelsets=benchmark_modelsets,
        config_path=config_path,
        ingestion_bundle_name=ingestion_bundle_name,
        ingestion_config_path=ingestion_config_path,
        source_preset_name=source_preset_name,
        manual_column_map_text=manual_column_map_text,
        vessel_types_text=vessel_types_text,
        output_root=focus_root,
        pairwise_split_strategy=pairwise_split_strategy,
        run_calibration_eval=bool(run_calibration_eval),
        run_own_ship_loo=bool(run_own_ship_loo),
        run_own_ship_case_eval=bool(run_own_ship_case_eval),
        own_ship_case_eval_mmsis=focus_mmsis,
        own_ship_case_eval_min_rows=int(own_ship_case_eval_min_rows),
        own_ship_case_eval_repeat_count=max(1, int(own_ship_case_eval_repeat_count)),
        build_study_journals=bool(build_study_journals),
        study_journal_output_template=focus_journal_template,
        study_journal_note=study_journal_note,
        torch_device=torch_device,
        random_seed=random_seed,
    )
    baseline_reused = False
    baseline_reuse_source_summary_json_path = ""
    if baseline_sweep_summary_json_path:
        baseline_summary = _load_summary_json(baseline_sweep_summary_json_path)
        baseline_reused = True
        baseline_reuse_source_summary_json_path = str(baseline_sweep_summary_json_path)
    else:
        baseline_summary = run_study_modelset_sweep(
            manifest_path=manifest_path,
            raw_input_path=raw_input_path,
            output_prefix=baseline_sweep_prefix,
            benchmark_modelsets=benchmark_modelsets,
            config_path=config_path,
            ingestion_bundle_name=ingestion_bundle_name,
            ingestion_config_path=ingestion_config_path,
            source_preset_name=source_preset_name,
            manual_column_map_text=manual_column_map_text,
            vessel_types_text=vessel_types_text,
            output_root=baseline_root,
            pairwise_split_strategy=pairwise_split_strategy,
            run_calibration_eval=bool(run_calibration_eval),
            run_own_ship_loo=bool(run_own_ship_loo),
            run_own_ship_case_eval=bool(run_own_ship_case_eval),
            own_ship_case_eval_mmsis=None,
            own_ship_case_eval_min_rows=int(own_ship_case_eval_min_rows),
            own_ship_case_eval_repeat_count=max(1, int(own_ship_case_eval_repeat_count)),
            build_study_journals=bool(build_study_journals),
            study_journal_output_template=baseline_journal_template,
            study_journal_note=study_journal_note,
            torch_device=torch_device,
            random_seed=random_seed,
        )
    baseline_summary_path = str(
        baseline_summary.get("summary_json_path") or baseline_sweep_summary_json_path or ""
    )
    if not baseline_summary_path:
        raise ValueError("Unable to resolve baseline summary JSON path.")
    compare_summary = compare_study_sweep_summaries(
        focus_summary_path=focus_summary["summary_json_path"],
        baseline_summary_path=baseline_summary_path,
        output_prefix=compare_prefix,
        focus_label=focus_label,
        baseline_label=baseline_label,
        epsilon=float(compare_epsilon),
    )

    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    summary: dict[str, Any] = {
        "status": "completed",
        "manifest_path": str(manifest_path),
        "raw_input_path": str(raw_input_path),
        "pairwise_split_strategy": pairwise_split_strategy,
        "focus_own_ship_case_eval_mmsis": focus_mmsis,
        "random_seed": random_seed,
        "focus_mmsi_resolution_mode": focus_resolution.get("mode", "manual"),
        "focus_mmsi_requested_rank": focus_resolution.get("requested_rank"),
        "focus_mmsi_selected_rank": focus_resolution.get("selected_rank"),
        "focus_mmsi_selected_mmsi": focus_resolution.get("selected_mmsi", ""),
        "focus_mmsi_auto_workflow_summary_json_path": focus_resolution.get("workflow_summary_json_path", ""),
        "focus_mmsi_auto_own_ship_candidates_path": focus_resolution.get("own_ship_candidates_path", ""),
        "baseline_reused": baseline_reused,
        "baseline_reuse_source_summary_json_path": baseline_reuse_source_summary_json_path,
        "benchmark_modelsets": benchmark_modelsets,
        "focus_sweep_summary_json_path": focus_summary.get("summary_json_path"),
        "focus_sweep_summary_md_path": focus_summary.get("summary_md_path"),
        "baseline_sweep_summary_json_path": baseline_summary_path,
        "baseline_sweep_summary_md_path": baseline_summary.get("summary_md_path"),
        "compare_summary_json_path": compare_summary.get("summary_json_path"),
        "compare_summary_md_path": compare_summary.get("summary_md_path"),
        "compare_summary_csv_path": compare_summary.get("summary_csv_path"),
        "focus_modelset_count": focus_summary.get("modelset_count", 0),
        "baseline_modelset_count": baseline_summary.get("modelset_count", 0),
        "compared_modelset_count": compare_summary.get("modelset_count", 0),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_focus_vs_baseline_markdown(summary), encoding="utf-8")
    return summary
