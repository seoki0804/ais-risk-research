from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Any

from .focus_mmsi_compare import run_focus_mmsi_compare_bundle
from .sweep_compare import _safe_float, _fmt, _fmt_delta


def _parse_seed_list(values: list[int] | None) -> list[int]:
    if not values:
        return [42, 43, 44]
    unique: list[int] = []
    seen: set[int] = set()
    for value in values:
        item = int(value)
        if item in seen:
            continue
        unique.append(item)
        seen.add(item)
    if not unique:
        return [42, 43, 44]
    return unique


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


def _robustness_label(
    focus_favor_count: int,
    baseline_favor_count: int,
    seed_count: int,
) -> str:
    if seed_count <= 0:
        return "insufficient_seeds"
    if focus_favor_count == seed_count and baseline_favor_count == 0:
        return "focus_robust"
    if baseline_favor_count == seed_count and focus_favor_count == 0:
        return "baseline_robust"
    if focus_favor_count > baseline_favor_count:
        return "focus_tilt"
    if baseline_favor_count > focus_favor_count:
        return "baseline_tilt"
    return "mixed"


def build_focus_seed_compare_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Focus Seed Compare Report",
        "",
        "## Inputs",
        "",
        f"- manifest_path: `{summary.get('manifest_path', 'n/a')}`",
        f"- raw_input_path: `{summary.get('raw_input_path', 'n/a')}`",
        f"- focus_own_ship_mmsis: `{summary.get('focus_own_ship_mmsis', [])}`",
        f"- seed_values: `{summary.get('seed_values', [])}`",
        f"- benchmark_modelsets: `{summary.get('benchmark_modelsets', [])}`",
        f"- run_count: `{summary.get('run_count', 0)}`",
        "",
        "## Seed Runs",
        "",
        "| Seed | Compared Modelsets | Output Summary |",
        "|---:|---:|---|",
    ]
    for row in summary.get("seed_rows", []):
        lines.append(
            "| {seed} | {count} | `{path}` |".format(
                seed=row.get("seed", "n/a"),
                count=row.get("compared_modelset_count", 0),
                path=row.get("focus_mmsi_compare_summary_json_path", "n/a"),
            )
        )

    lines.extend(
        [
            "",
            "## Modelset Robustness",
            "",
            "| Modelset | Seed Count | Focus-Favor Count | Baseline-Favor Count | Mixed Count | Mean Score | Std Score | Mean Delta Case F1 | Std Delta Case F1 | Robustness Label | Consensus Judgement |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in summary.get("aggregate_by_modelset", []):
        lines.append(
            "| {modelset} | {seed_count} | {focus_favor} | {baseline_favor} | {mixed_count} | {mean_score} | {std_score} | {mean_delta_case_f1} | {std_delta_case_f1} | {robustness} | {consensus} |".format(
                modelset=row.get("modelset_key", "unknown"),
                seed_count=row.get("seed_count", 0),
                focus_favor=row.get("focus_favor_count", 0),
                baseline_favor=row.get("baseline_favor_count", 0),
                mixed_count=row.get("mixed_count", 0),
                mean_score=_fmt(row.get("mean_aggregate_score")),
                std_score=_fmt(row.get("std_aggregate_score")),
                mean_delta_case_f1=_fmt_delta(row.get("mean_delta_case_f1_mean")),
                std_delta_case_f1=_fmt(row.get("std_delta_case_f1_mean")),
                robustness=row.get("robustness_label", "n/a"),
                consensus=row.get("consensus_judgement", "n/a"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def run_focus_seed_compare_bundle(
    manifest_path: str | Path,
    raw_input_path: str | Path,
    output_prefix: str | Path,
    focus_own_ship_mmsis: list[str],
    seed_values: list[int] | None,
    benchmark_modelsets: list[list[str]],
    config_path: str | Path = "configs/base.toml",
    ingestion_bundle_name: str | None = None,
    ingestion_config_path: str | Path | None = None,
    source_preset_name: str | None = "auto",
    manual_column_map_text: str | None = None,
    vessel_types_text: str | None = None,
    output_root: str | Path = "outputs/focus_seed_compare",
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
) -> dict[str, Any]:
    seeds = _parse_seed_list(seed_values)
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    output_root_path = Path(output_root)
    output_root_path.mkdir(parents=True, exist_ok=True)

    seed_rows: list[dict[str, Any]] = []
    modelset_seed_rows: list[dict[str, Any]] = []

    for seed in seeds:
        seed_prefix = prefix.with_name(f"{prefix.name}_seed_{seed}")
        seed_root = output_root_path / f"seed_{seed}"
        bundle_summary = run_focus_mmsi_compare_bundle(
            manifest_path=manifest_path,
            raw_input_path=raw_input_path,
            output_prefix=seed_prefix,
            focus_own_ship_mmsis=focus_own_ship_mmsis,
            benchmark_modelsets=benchmark_modelsets,
            config_path=config_path,
            ingestion_bundle_name=ingestion_bundle_name,
            ingestion_config_path=ingestion_config_path,
            source_preset_name=source_preset_name,
            manual_column_map_text=manual_column_map_text,
            vessel_types_text=vessel_types_text,
            output_root=seed_root,
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
            reuse_baseline_across_mmsis=bool(reuse_baseline_across_mmsis),
            random_seed=int(seed),
        )

        seed_rows.append(
            {
                "seed": int(seed),
                "compared_modelset_count": int(len(bundle_summary.get("aggregate_by_modelset", []))),
                "focus_mmsi_compare_summary_json_path": bundle_summary.get("summary_json_path"),
            }
        )

        for row in bundle_summary.get("aggregate_by_modelset", []):
            modelset_seed_rows.append(
                {
                    "seed": int(seed),
                    "modelset_key": row.get("modelset_key"),
                    "aggregate_judgement": row.get("aggregate_judgement"),
                    "aggregate_score": _safe_float(row.get("aggregate_score")),
                    "mean_delta_case_f1_mean": _safe_float(row.get("mean_delta_best_case_f1_mean")),
                    "std_delta_case_f1_mean": _safe_float(row.get("std_delta_best_case_f1_mean")),
                    "mean_delta_repeat_std_mean": _safe_float(row.get("mean_delta_best_case_f1_std_repeat_mean")),
                    "mean_delta_calibration_ece": _safe_float(row.get("mean_delta_best_calibration_ece")),
                }
            )

    seed_rows.sort(key=lambda item: int(item.get("seed", 0)))
    modelset_seed_rows.sort(key=lambda item: (str(item.get("modelset_key", "")), int(item.get("seed", 0))))

    aggregate_by_modelset: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in modelset_seed_rows:
        grouped.setdefault(str(row.get("modelset_key") or "unknown"), []).append(row)

    for modelset_key, rows in grouped.items():
        seed_count = len(rows)
        focus_favor_count = sum(
            1
            for row in rows
            if str(row.get("aggregate_judgement")) in {"focus_consistent", "focus_leaning"}
        )
        baseline_favor_count = sum(
            1
            for row in rows
            if str(row.get("aggregate_judgement")) in {"baseline_consistent", "baseline_leaning"}
        )
        mixed_count = seed_count - focus_favor_count - baseline_favor_count

        score_values = [value for value in (_safe_float(row.get("aggregate_score")) for row in rows) if value is not None]
        delta_case_values = [
            value for value in (_safe_float(row.get("mean_delta_case_f1_mean")) for row in rows) if value is not None
        ]
        delta_repeat_values = [
            value for value in (_safe_float(row.get("mean_delta_repeat_std_mean")) for row in rows) if value is not None
        ]
        delta_ece_values = [
            value for value in (_safe_float(row.get("mean_delta_calibration_ece")) for row in rows) if value is not None
        ]

        judgement_counts: dict[str, int] = {}
        for row in rows:
            key = str(row.get("aggregate_judgement") or "unknown")
            judgement_counts[key] = judgement_counts.get(key, 0) + 1
        consensus_judgement = sorted(judgement_counts.items(), key=lambda item: (item[1], item[0]), reverse=True)[0][0]

        aggregate_by_modelset.append(
            {
                "modelset_key": modelset_key,
                "seed_count": seed_count,
                "focus_favor_count": focus_favor_count,
                "baseline_favor_count": baseline_favor_count,
                "mixed_count": mixed_count,
                "mean_aggregate_score": _mean(score_values),
                "std_aggregate_score": _std(score_values),
                "mean_delta_case_f1_mean": _mean(delta_case_values),
                "std_delta_case_f1_mean": _std(delta_case_values),
                "mean_delta_repeat_std_mean": _mean(delta_repeat_values),
                "std_delta_repeat_std_mean": _std(delta_repeat_values),
                "mean_delta_calibration_ece": _mean(delta_ece_values),
                "std_delta_calibration_ece": _std(delta_ece_values),
                "consensus_judgement": consensus_judgement,
                "robustness_label": _robustness_label(
                    focus_favor_count=focus_favor_count,
                    baseline_favor_count=baseline_favor_count,
                    seed_count=seed_count,
                ),
            }
        )
    aggregate_by_modelset.sort(key=lambda item: str(item.get("modelset_key", "")))

    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    seed_rows_csv_path = prefix.with_name(f"{prefix.name}_seed_rows.csv")
    modelset_seed_rows_csv_path = prefix.with_name(f"{prefix.name}_modelset_seed_rows.csv")
    aggregate_csv_path = prefix.with_name(f"{prefix.name}_aggregate_by_modelset.csv")

    with seed_rows_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "seed",
            "compared_modelset_count",
            "focus_mmsi_compare_summary_json_path",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in seed_rows:
            writer.writerow(row)

    with modelset_seed_rows_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "seed",
            "modelset_key",
            "aggregate_judgement",
            "aggregate_score",
            "mean_delta_case_f1_mean",
            "std_delta_case_f1_mean",
            "mean_delta_repeat_std_mean",
            "mean_delta_calibration_ece",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in modelset_seed_rows:
            writer.writerow(row)

    with aggregate_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "modelset_key",
            "seed_count",
            "focus_favor_count",
            "baseline_favor_count",
            "mixed_count",
            "mean_aggregate_score",
            "std_aggregate_score",
            "mean_delta_case_f1_mean",
            "std_delta_case_f1_mean",
            "mean_delta_repeat_std_mean",
            "std_delta_repeat_std_mean",
            "mean_delta_calibration_ece",
            "std_delta_calibration_ece",
            "consensus_judgement",
            "robustness_label",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in aggregate_by_modelset:
            writer.writerow(row)

    summary: dict[str, Any] = {
        "status": "completed",
        "manifest_path": str(manifest_path),
        "raw_input_path": str(raw_input_path),
        "focus_own_ship_mmsis": [str(item) for item in focus_own_ship_mmsis],
        "seed_values": seeds,
        "benchmark_modelsets": benchmark_modelsets,
        "run_count": len(seed_rows),
        "seed_rows": seed_rows,
        "modelset_seed_rows": modelset_seed_rows,
        "aggregate_by_modelset": aggregate_by_modelset,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "seed_rows_csv_path": str(seed_rows_csv_path),
        "modelset_seed_rows_csv_path": str(modelset_seed_rows_csv_path),
        "aggregate_csv_path": str(aggregate_csv_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_focus_seed_compare_markdown(summary), encoding="utf-8")
    return summary
