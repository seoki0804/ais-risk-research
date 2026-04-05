from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .focus_compare import run_focus_vs_baseline_sweep_bundle
from .sweep_compare import _safe_float, _fmt, _fmt_delta


def _parse_rank_list(values: list[int] | None) -> list[int]:
    if not values:
        return [1, 2, 3]
    unique = sorted({max(1, int(item)) for item in values})
    return unique


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_focus_rank_compare_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Focus Rank Compare Report",
        "",
        "## Inputs",
        "",
        f"- manifest_path: `{summary.get('manifest_path', 'n/a')}`",
        f"- raw_input_path: `{summary.get('raw_input_path', 'n/a')}`",
        f"- auto_focus_ranks: `{summary.get('auto_focus_ranks', [])}`",
        f"- reuse_baseline_across_ranks: `{summary.get('reuse_baseline_across_ranks', True)}`",
        f"- random_seed: `{summary.get('random_seed', 'n/a')}`",
        f"- shared_baseline_summary_json_path: `{summary.get('shared_baseline_summary_json_path', 'n/a')}`",
        f"- benchmark_modelsets: `{summary.get('benchmark_modelsets', [])}`",
        f"- run_count: `{summary.get('run_count', 0)}`",
        "",
        "## Rank Runs",
        "",
        "| Rank | Selected MMSI | Resolution Mode | Baseline Reused | Compared Modelsets | Focus-Leaning Count | Mixed Count | Baseline-Leaning Count | Bundle Summary | Compare Summary |",
        "|---:|---|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in summary.get("rank_rows", []):
        lines.append(
            "| {rank} | {mmsi} | {mode} | {reused} | {compared} | {focus_leaning} | {mixed} | {baseline_leaning} | `{bundle}` | `{compare}` |".format(
                rank=row.get("auto_focus_rank", "n/a"),
                mmsi=row.get("selected_mmsi", "n/a"),
                mode=row.get("focus_mmsi_resolution_mode", "n/a"),
                reused="yes" if bool(row.get("baseline_reused", False)) else "no",
                compared=row.get("compared_modelset_count", 0),
                focus_leaning=row.get("focus_leaning_count", 0),
                mixed=row.get("mixed_count", 0),
                baseline_leaning=row.get("baseline_leaning_count", 0),
                bundle=row.get("bundle_summary_json_path", "n/a"),
                compare=row.get("compare_summary_json_path", "n/a"),
            )
        )

    lines.extend(
        [
            "",
            "## Modelset Best Rank",
            "",
            "| Modelset | Best Rank | Best MMSI | Score (focus-baseline) | Judgement | Focus Case F1 | Base Case F1 | Delta Case F1 | Focus Repeat Std Mean | Base Repeat Std Mean | Delta Repeat Std Mean | Focus Cal ECE | Base Cal ECE | Delta Cal ECE |",
            "|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary.get("best_rank_by_modelset", []):
        lines.append(
            "| {modelset} | {rank} | {mmsi} | {score} | {judgement} | {focus_case_f1} | {base_case_f1} | {delta_case_f1} | {focus_repeat_std} | {base_repeat_std} | {delta_repeat_std} | {focus_ece} | {base_ece} | {delta_ece} |".format(
                modelset=row.get("modelset_key", "unknown"),
                rank=row.get("best_rank", "n/a"),
                mmsi=row.get("best_selected_mmsi", "n/a"),
                score=row.get("best_score", 0),
                judgement=row.get("best_judgement", "n/a"),
                focus_case_f1=_fmt(row.get("best_focus_best_case_f1_mean")),
                base_case_f1=_fmt(row.get("best_baseline_best_case_f1_mean")),
                delta_case_f1=_fmt_delta(row.get("best_delta_best_case_f1_mean")),
                focus_repeat_std=_fmt(row.get("best_focus_best_case_f1_std_repeat_mean")),
                base_repeat_std=_fmt(row.get("best_baseline_best_case_f1_std_repeat_mean")),
                delta_repeat_std=_fmt_delta(row.get("best_delta_best_case_f1_std_repeat_mean")),
                focus_ece=_fmt(row.get("best_focus_best_calibration_ece")),
                base_ece=_fmt(row.get("best_baseline_best_calibration_ece")),
                delta_ece=_fmt_delta(row.get("best_delta_best_calibration_ece")),
            )
        )
    lines.append("")
    return "\n".join(lines)


def run_focus_rank_compare_bundle(
    manifest_path: str | Path,
    raw_input_path: str | Path,
    output_prefix: str | Path,
    auto_focus_ranks: list[int] | None,
    benchmark_modelsets: list[list[str]],
    config_path: str | Path = "configs/base.toml",
    ingestion_bundle_name: str | None = None,
    ingestion_config_path: str | Path | None = None,
    source_preset_name: str | None = "auto",
    manual_column_map_text: str | None = None,
    vessel_types_text: str | None = None,
    output_root: str | Path = "outputs/focus_rank_compare",
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
    reuse_baseline_across_ranks: bool = True,
    random_seed: int | None = 42,
) -> dict[str, Any]:
    ranks = _parse_rank_list(auto_focus_ranks)
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    rank_rows: list[dict[str, Any]] = []
    modelset_rows: list[dict[str, Any]] = []
    shared_baseline_summary_json_path = ""

    for rank in ranks:
        rank_prefix = prefix.with_name(f"{prefix.name}_rank_{rank:02d}")
        rank_root = output_root_path / f"rank_{rank:02d}"
        baseline_input_path: str | None = None
        if reuse_baseline_across_ranks and shared_baseline_summary_json_path:
            baseline_input_path = shared_baseline_summary_json_path
        bundle_summary = run_focus_vs_baseline_sweep_bundle(
            manifest_path=manifest_path,
            raw_input_path=raw_input_path,
            output_prefix=rank_prefix,
            focus_own_ship_case_eval_mmsis=None,
            benchmark_modelsets=benchmark_modelsets,
            config_path=config_path,
            ingestion_bundle_name=ingestion_bundle_name,
            ingestion_config_path=ingestion_config_path,
            source_preset_name=source_preset_name,
            manual_column_map_text=manual_column_map_text,
            vessel_types_text=vessel_types_text,
            output_root=rank_root,
            pairwise_split_strategy=pairwise_split_strategy,
            run_calibration_eval=bool(run_calibration_eval),
            run_own_ship_loo=bool(run_own_ship_loo),
            run_own_ship_case_eval=bool(run_own_ship_case_eval),
            own_ship_case_eval_min_rows=int(own_ship_case_eval_min_rows),
            own_ship_case_eval_repeat_count=max(1, int(own_ship_case_eval_repeat_count)),
            build_study_journals=bool(build_study_journals),
            study_journal_output_template=study_journal_output_template,
            study_journal_note=study_journal_note,
            torch_device=torch_device,
            compare_epsilon=float(compare_epsilon),
            focus_label=focus_label,
            baseline_label=baseline_label,
            auto_focus_own_ship=True,
            auto_focus_rank=rank,
            baseline_sweep_summary_json_path=baseline_input_path,
            random_seed=random_seed,
        )
        if reuse_baseline_across_ranks and not shared_baseline_summary_json_path:
            shared_baseline_summary_json_path = str(bundle_summary.get("baseline_sweep_summary_json_path") or "")

        compare_summary = _read_json(bundle_summary["compare_summary_json_path"])
        compare_rows = compare_summary.get("rows", [])
        focus_leaning_count = sum(1 for item in compare_rows if str(item.get("judgement")) in {"focus_leaning", "focus_advantage"})
        baseline_leaning_count = sum(
            1 for item in compare_rows if str(item.get("judgement")) in {"baseline_leaning", "baseline_advantage"}
        )
        mixed_count = sum(1 for item in compare_rows if str(item.get("judgement")) == "mixed")

        rank_row = {
            "auto_focus_rank": rank,
            "selected_mmsi": bundle_summary.get("focus_mmsi_selected_mmsi"),
            "focus_mmsi_resolution_mode": bundle_summary.get("focus_mmsi_resolution_mode"),
            "focus_mmsi_selected_rank": bundle_summary.get("focus_mmsi_selected_rank"),
            "baseline_reused": bool(bundle_summary.get("baseline_reused", False)),
            "compared_modelset_count": int(bundle_summary.get("compared_modelset_count", 0)),
            "focus_leaning_count": focus_leaning_count,
            "baseline_leaning_count": baseline_leaning_count,
            "mixed_count": mixed_count,
            "bundle_summary_json_path": bundle_summary.get("summary_json_path"),
            "compare_summary_json_path": bundle_summary.get("compare_summary_json_path"),
        }
        rank_rows.append(rank_row)

        for item in compare_rows:
            modelset_rows.append(
                {
                    "auto_focus_rank": rank,
                    "selected_mmsi": bundle_summary.get("focus_mmsi_selected_mmsi"),
                    "modelset_key": item.get("modelset_key"),
                    "focus_better_count": int(item.get("focus_better_count", 0)),
                    "baseline_better_count": int(item.get("baseline_better_count", 0)),
                    "compared_metric_count": int(item.get("compared_metric_count", 0)),
                    "judgement": item.get("judgement"),
                    "focus_best_case_f1_mean": _safe_float(item.get("focus_best_case_f1_mean")),
                    "baseline_best_case_f1_mean": _safe_float(item.get("baseline_best_case_f1_mean")),
                    "delta_best_case_f1_mean": _safe_float(item.get("delta_best_case_f1_mean")),
                    "focus_best_case_f1_std_repeat_mean": _safe_float(item.get("focus_best_case_f1_std_repeat_mean")),
                    "baseline_best_case_f1_std_repeat_mean": _safe_float(item.get("baseline_best_case_f1_std_repeat_mean")),
                    "delta_best_case_f1_std_repeat_mean": _safe_float(item.get("delta_best_case_f1_std_repeat_mean")),
                    "focus_best_calibration_ece": _safe_float(item.get("focus_best_calibration_ece")),
                    "baseline_best_calibration_ece": _safe_float(item.get("baseline_best_calibration_ece")),
                    "delta_best_calibration_ece": _safe_float(item.get("delta_best_calibration_ece")),
                }
            )

    rank_rows.sort(key=lambda item: int(item.get("auto_focus_rank", 0)))
    modelset_rows.sort(
        key=lambda item: (str(item.get("modelset_key", "")), int(item.get("auto_focus_rank", 0)))
    )

    best_rank_by_modelset: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in modelset_rows:
        grouped.setdefault(str(row.get("modelset_key") or "unknown"), []).append(row)
    for modelset_key, rows in grouped.items():
        rows.sort(
            key=lambda item: (
                int(item.get("focus_better_count", 0)) - int(item.get("baseline_better_count", 0)),
                _safe_float(item.get("delta_best_case_f1_mean")) or -999.0,
                -(_safe_float(item.get("delta_best_case_f1_std_repeat_mean")) or 999.0),
                -(_safe_float(item.get("delta_best_calibration_ece")) or 999.0),
                -int(item.get("compared_metric_count", 0)),
            ),
            reverse=True,
        )
        best = rows[0]
        best_rank_by_modelset.append(
            {
                "modelset_key": modelset_key,
                "best_rank": best.get("auto_focus_rank"),
                "best_selected_mmsi": best.get("selected_mmsi"),
                "best_score": int(best.get("focus_better_count", 0)) - int(best.get("baseline_better_count", 0)),
                "best_judgement": best.get("judgement"),
                "best_focus_best_case_f1_mean": best.get("focus_best_case_f1_mean"),
                "best_baseline_best_case_f1_mean": best.get("baseline_best_case_f1_mean"),
                "best_delta_best_case_f1_mean": best.get("delta_best_case_f1_mean"),
                "best_focus_best_case_f1_std_repeat_mean": best.get("focus_best_case_f1_std_repeat_mean"),
                "best_baseline_best_case_f1_std_repeat_mean": best.get("baseline_best_case_f1_std_repeat_mean"),
                "best_delta_best_case_f1_std_repeat_mean": best.get("delta_best_case_f1_std_repeat_mean"),
                "best_focus_best_calibration_ece": best.get("focus_best_calibration_ece"),
                "best_baseline_best_calibration_ece": best.get("baseline_best_calibration_ece"),
                "best_delta_best_calibration_ece": best.get("delta_best_calibration_ece"),
            }
        )
    best_rank_by_modelset.sort(key=lambda item: str(item.get("modelset_key", "")))

    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    rank_rows_csv_path = prefix.with_name(f"{prefix.name}_rank_rows.csv")
    modelset_rows_csv_path = prefix.with_name(f"{prefix.name}_modelset_rows.csv")

    with rank_rows_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "auto_focus_rank",
            "selected_mmsi",
            "focus_mmsi_resolution_mode",
            "focus_mmsi_selected_rank",
            "baseline_reused",
            "compared_modelset_count",
            "focus_leaning_count",
            "mixed_count",
            "baseline_leaning_count",
            "bundle_summary_json_path",
            "compare_summary_json_path",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rank_rows:
            writer.writerow(row)

    with modelset_rows_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "auto_focus_rank",
            "selected_mmsi",
            "modelset_key",
            "focus_better_count",
            "baseline_better_count",
            "compared_metric_count",
            "judgement",
            "focus_best_case_f1_mean",
            "baseline_best_case_f1_mean",
            "delta_best_case_f1_mean",
            "focus_best_case_f1_std_repeat_mean",
            "baseline_best_case_f1_std_repeat_mean",
            "delta_best_case_f1_std_repeat_mean",
            "focus_best_calibration_ece",
            "baseline_best_calibration_ece",
            "delta_best_calibration_ece",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in modelset_rows:
            writer.writerow(row)

    summary: dict[str, Any] = {
        "status": "completed",
        "manifest_path": str(manifest_path),
        "raw_input_path": str(raw_input_path),
        "auto_focus_ranks": ranks,
        "reuse_baseline_across_ranks": bool(reuse_baseline_across_ranks),
        "random_seed": random_seed,
        "shared_baseline_summary_json_path": shared_baseline_summary_json_path,
        "benchmark_modelsets": benchmark_modelsets,
        "run_count": len(rank_rows),
        "rank_rows": rank_rows,
        "modelset_rows": modelset_rows,
        "best_rank_by_modelset": best_rank_by_modelset,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "rank_rows_csv_path": str(rank_rows_csv_path),
        "modelset_rows_csv_path": str(modelset_rows_csv_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_focus_rank_compare_markdown(summary), encoding="utf-8")
    return summary
