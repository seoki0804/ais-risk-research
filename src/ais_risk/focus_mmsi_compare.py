from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Any

from .focus_compare import run_focus_vs_baseline_sweep_bundle
from .sweep_compare import _safe_float, _fmt, _fmt_delta


def _parse_mmsi_list(values: list[str] | None) -> list[str]:
    if not values:
        raise ValueError("focus_own_ship_mmsis is empty. Provide at least one MMSI.")
    seen: set[str] = set()
    ordered: list[str] = []
    for item in values:
        mmsi = str(item).strip()
        if not mmsi or mmsi in seen:
            continue
        ordered.append(mmsi)
        seen.add(mmsi)
    if not ordered:
        raise ValueError("focus_own_ship_mmsis has no valid MMSI after normalization.")
    return ordered


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _std(values: list[float]) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return 0.0
    return float(statistics.stdev(values))


def _aggregate_judgement(
    focus_leaning_or_advantage_count: int,
    baseline_leaning_or_advantage_count: int,
    compared_run_count: int,
) -> str:
    if compared_run_count <= 0:
        return "insufficient_runs"
    if focus_leaning_or_advantage_count == compared_run_count and baseline_leaning_or_advantage_count == 0:
        return "focus_consistent"
    if baseline_leaning_or_advantage_count == compared_run_count and focus_leaning_or_advantage_count == 0:
        return "baseline_consistent"
    if focus_leaning_or_advantage_count > baseline_leaning_or_advantage_count:
        return "focus_leaning"
    if baseline_leaning_or_advantage_count > focus_leaning_or_advantage_count:
        return "baseline_leaning"
    return "mixed"


def build_focus_mmsi_compare_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Focus MMSI Compare Report",
        "",
        "## Inputs",
        "",
        f"- manifest_path: `{summary.get('manifest_path', 'n/a')}`",
        f"- raw_input_path: `{summary.get('raw_input_path', 'n/a')}`",
        f"- focus_own_ship_mmsis: `{summary.get('focus_own_ship_mmsis', [])}`",
        f"- reuse_baseline_across_mmsis: `{summary.get('reuse_baseline_across_mmsis', True)}`",
        f"- random_seed: `{summary.get('random_seed', 'n/a')}`",
        f"- shared_baseline_summary_json_path: `{summary.get('shared_baseline_summary_json_path', 'n/a')}`",
        f"- benchmark_modelsets: `{summary.get('benchmark_modelsets', [])}`",
        f"- run_count: `{summary.get('run_count', 0)}`",
        "",
        "## MMSI Runs",
        "",
        "| MMSI | Baseline Reused | Compared Modelsets | Focus-Leaning Count | Mixed Count | Baseline-Leaning Count | Bundle Summary | Compare Summary |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in summary.get("mmsi_rows", []):
        lines.append(
            "| {mmsi} | {reused} | {compared} | {focus_leaning} | {mixed} | {baseline_leaning} | `{bundle}` | `{compare}` |".format(
                mmsi=row.get("focus_mmsi", "n/a"),
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
            "## Modelset Aggregate",
            "",
            "| Modelset | Runs | Focus-Leaning/Advantage | Baseline-Leaning/Advantage | Mixed | Score (focus-baseline) | Aggregate Judgement | Mean Delta Case F1 | Std Delta Case F1 | Mean Delta Repeat Std | Mean Delta Cal ECE |",
            "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary.get("aggregate_by_modelset", []):
        lines.append(
            "| {modelset} | {runs} | {focus_count} | {baseline_count} | {mixed_count} | {score} | {judgement} | {delta_case_f1_mean} | {delta_case_f1_std} | {delta_repeat_std_mean} | {delta_ece_mean} |".format(
                modelset=row.get("modelset_key", "unknown"),
                runs=row.get("run_count", 0),
                focus_count=row.get("focus_leaning_or_advantage_count", 0),
                baseline_count=row.get("baseline_leaning_or_advantage_count", 0),
                mixed_count=row.get("mixed_count", 0),
                score=row.get("aggregate_score", 0),
                judgement=row.get("aggregate_judgement", "n/a"),
                delta_case_f1_mean=_fmt_delta(row.get("mean_delta_best_case_f1_mean")),
                delta_case_f1_std=_fmt(row.get("std_delta_best_case_f1_mean")),
                delta_repeat_std_mean=_fmt_delta(row.get("mean_delta_best_case_f1_std_repeat_mean")),
                delta_ece_mean=_fmt_delta(row.get("mean_delta_best_calibration_ece")),
            )
        )
    lines.append("")
    return "\n".join(lines)


def run_focus_mmsi_compare_bundle(
    manifest_path: str | Path,
    raw_input_path: str | Path,
    output_prefix: str | Path,
    focus_own_ship_mmsis: list[str] | None,
    benchmark_modelsets: list[list[str]],
    config_path: str | Path = "configs/base.toml",
    ingestion_bundle_name: str | None = None,
    ingestion_config_path: str | Path | None = None,
    source_preset_name: str | None = "auto",
    manual_column_map_text: str | None = None,
    vessel_types_text: str | None = None,
    output_root: str | Path = "outputs/focus_mmsi_compare",
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
    reuse_baseline_across_mmsis: bool = True,
    random_seed: int | None = 42,
) -> dict[str, Any]:
    mmsis = _parse_mmsi_list(focus_own_ship_mmsis)
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    mmsi_rows: list[dict[str, Any]] = []
    modelset_rows: list[dict[str, Any]] = []
    shared_baseline_summary_json_path = ""

    for mmsi in mmsis:
        mmsi_prefix = prefix.with_name(f"{prefix.name}_mmsi_{mmsi}")
        mmsi_root = output_root_path / f"mmsi_{mmsi}"
        baseline_input_path: str | None = None
        if reuse_baseline_across_mmsis and shared_baseline_summary_json_path:
            baseline_input_path = shared_baseline_summary_json_path
        bundle_summary = run_focus_vs_baseline_sweep_bundle(
            manifest_path=manifest_path,
            raw_input_path=raw_input_path,
            output_prefix=mmsi_prefix,
            focus_own_ship_case_eval_mmsis=[mmsi],
            benchmark_modelsets=benchmark_modelsets,
            config_path=config_path,
            ingestion_bundle_name=ingestion_bundle_name,
            ingestion_config_path=ingestion_config_path,
            source_preset_name=source_preset_name,
            manual_column_map_text=manual_column_map_text,
            vessel_types_text=vessel_types_text,
            output_root=mmsi_root,
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
            auto_focus_own_ship=False,
            auto_focus_rank=1,
            baseline_sweep_summary_json_path=baseline_input_path,
            random_seed=random_seed,
        )
        if reuse_baseline_across_mmsis and not shared_baseline_summary_json_path:
            shared_baseline_summary_json_path = str(bundle_summary.get("baseline_sweep_summary_json_path") or "")

        compare_summary = _read_json(bundle_summary["compare_summary_json_path"])
        compare_rows = compare_summary.get("rows", [])
        focus_leaning_count = sum(1 for item in compare_rows if str(item.get("judgement")) in {"focus_leaning", "focus_advantage"})
        baseline_leaning_count = sum(
            1 for item in compare_rows if str(item.get("judgement")) in {"baseline_leaning", "baseline_advantage"}
        )
        mixed_count = sum(1 for item in compare_rows if str(item.get("judgement")) == "mixed")

        mmsi_row = {
            "focus_mmsi": mmsi,
            "selected_mmsi": bundle_summary.get("focus_mmsi_selected_mmsi"),
            "baseline_reused": bool(bundle_summary.get("baseline_reused", False)),
            "compared_modelset_count": int(bundle_summary.get("compared_modelset_count", 0)),
            "focus_leaning_count": focus_leaning_count,
            "baseline_leaning_count": baseline_leaning_count,
            "mixed_count": mixed_count,
            "bundle_summary_json_path": bundle_summary.get("summary_json_path"),
            "compare_summary_json_path": bundle_summary.get("compare_summary_json_path"),
        }
        mmsi_rows.append(mmsi_row)

        for item in compare_rows:
            modelset_rows.append(
                {
                    "focus_mmsi": mmsi,
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

    mmsi_rows.sort(key=lambda item: str(item.get("focus_mmsi", "")))
    modelset_rows.sort(
        key=lambda item: (str(item.get("modelset_key", "")), str(item.get("focus_mmsi", "")))
    )

    aggregate_by_modelset: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in modelset_rows:
        grouped.setdefault(str(row.get("modelset_key") or "unknown"), []).append(row)
    for modelset_key, rows in grouped.items():
        focus_count = sum(
            1 for row in rows if str(row.get("judgement")) in {"focus_leaning", "focus_advantage"}
        )
        baseline_count = sum(
            1 for row in rows if str(row.get("judgement")) in {"baseline_leaning", "baseline_advantage"}
        )
        mixed_count = sum(1 for row in rows if str(row.get("judgement")) == "mixed")
        case_f1_deltas = [value for value in (_safe_float(row.get("delta_best_case_f1_mean")) for row in rows) if value is not None]
        repeat_std_deltas = [
            value for value in (_safe_float(row.get("delta_best_case_f1_std_repeat_mean")) for row in rows) if value is not None
        ]
        ece_deltas = [value for value in (_safe_float(row.get("delta_best_calibration_ece")) for row in rows) if value is not None]

        aggregate_by_modelset.append(
            {
                "modelset_key": modelset_key,
                "run_count": len(rows),
                "focus_leaning_or_advantage_count": focus_count,
                "baseline_leaning_or_advantage_count": baseline_count,
                "mixed_count": mixed_count,
                "aggregate_score": focus_count - baseline_count,
                "aggregate_judgement": _aggregate_judgement(
                    focus_leaning_or_advantage_count=focus_count,
                    baseline_leaning_or_advantage_count=baseline_count,
                    compared_run_count=len(rows),
                ),
                "mean_delta_best_case_f1_mean": _mean(case_f1_deltas),
                "std_delta_best_case_f1_mean": _std(case_f1_deltas),
                "mean_delta_best_case_f1_std_repeat_mean": _mean(repeat_std_deltas),
                "mean_delta_best_calibration_ece": _mean(ece_deltas),
            }
        )
    aggregate_by_modelset.sort(key=lambda item: str(item.get("modelset_key", "")))

    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    mmsi_rows_csv_path = prefix.with_name(f"{prefix.name}_mmsi_rows.csv")
    modelset_rows_csv_path = prefix.with_name(f"{prefix.name}_modelset_rows.csv")
    aggregate_csv_path = prefix.with_name(f"{prefix.name}_aggregate_by_modelset.csv")

    with mmsi_rows_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "focus_mmsi",
            "selected_mmsi",
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
        for row in mmsi_rows:
            writer.writerow(row)

    with modelset_rows_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "focus_mmsi",
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

    with aggregate_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "modelset_key",
            "run_count",
            "focus_leaning_or_advantage_count",
            "baseline_leaning_or_advantage_count",
            "mixed_count",
            "aggregate_score",
            "aggregate_judgement",
            "mean_delta_best_case_f1_mean",
            "std_delta_best_case_f1_mean",
            "mean_delta_best_case_f1_std_repeat_mean",
            "mean_delta_best_calibration_ece",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in aggregate_by_modelset:
            writer.writerow(row)

    summary: dict[str, Any] = {
        "status": "completed",
        "manifest_path": str(manifest_path),
        "raw_input_path": str(raw_input_path),
        "focus_own_ship_mmsis": mmsis,
        "reuse_baseline_across_mmsis": bool(reuse_baseline_across_mmsis),
        "random_seed": random_seed,
        "shared_baseline_summary_json_path": shared_baseline_summary_json_path,
        "benchmark_modelsets": benchmark_modelsets,
        "run_count": len(mmsi_rows),
        "mmsi_rows": mmsi_rows,
        "modelset_rows": modelset_rows,
        "aggregate_by_modelset": aggregate_by_modelset,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "mmsi_rows_csv_path": str(mmsi_rows_csv_path),
        "modelset_rows_csv_path": str(modelset_rows_csv_path),
        "aggregate_csv_path": str(aggregate_csv_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_focus_mmsi_compare_markdown(summary), encoding="utf-8")
    return summary
