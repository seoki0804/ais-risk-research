from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import replace
from pathlib import Path
from typing import Any

from .config import load_config
from .io import load_snapshot, save_result
from .models import ThresholdConfig
from .pipeline import run_snapshot


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def _sanitize_key(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in str(value))


def _build_metric_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "min": None,
            "max": None,
            "positive_count": 0,
            "negative_count": 0,
            "zero_count": 0,
        }
    return {
        "count": len(values),
        "mean": float(statistics.fmean(values)),
        "std": float(statistics.pstdev(values)) if len(values) > 1 else 0.0,
        "min": float(min(values)),
        "max": float(max(values)),
        "positive_count": int(sum(1 for item in values if item > 0.0)),
        "negative_count": int(sum(1 for item in values if item < 0.0)),
        "zero_count": int(sum(1 for item in values if math.isclose(item, 0.0, abs_tol=1e-12))),
    }


def _extract_scenarios(snapshot_result: Any) -> dict[str, dict[str, Any]]:
    scenarios: dict[str, dict[str, Any]] = {}
    for scenario in snapshot_result.scenarios:
        summary = scenario.summary
        scenarios[str(summary.scenario_name)] = {
            "speed_multiplier": float(summary.speed_multiplier),
            "max_risk": float(summary.max_risk),
            "mean_risk": float(summary.mean_risk),
            "warning_area_nm2": float(summary.warning_area_nm2),
            "caution_area_nm2": float(summary.caution_area_nm2),
            "dominant_sector": str(summary.dominant_sector),
        }
    return scenarios


def _compute_deltas_vs_current(
    scenarios: dict[str, dict[str, Any]],
    current_scenario_name: str,
) -> dict[str, float]:
    current = scenarios.get(current_scenario_name)
    if not current:
        return {}
    deltas: dict[str, float] = {}
    for name, metrics in scenarios.items():
        if name == current_scenario_name:
            continue
        for metric in ("max_risk", "mean_risk", "warning_area_nm2", "caution_area_nm2"):
            lhs = _safe_float(metrics.get(metric))
            rhs = _safe_float(current.get(metric))
            if lhs is None or rhs is None:
                continue
            deltas[f"{name}_{metric}_delta"] = float(lhs - rhs)
    return deltas


def _parse_threshold_profiles(
    threshold_profiles: list[dict[str, Any]] | None,
    default_safe: float,
    default_warning: float,
) -> list[dict[str, Any]]:
    if not threshold_profiles:
        threshold_profiles = [
            {"name": "base", "safe": default_safe, "warning": default_warning},
            {"name": "conservative", "safe": min(default_safe + 0.05, 0.95), "warning": min(default_warning + 0.05, 0.99)},
            {"name": "sensitive", "safe": max(default_safe - 0.05, 0.05), "warning": max(default_warning - 0.05, 0.10)},
        ]

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in threshold_profiles:
        name = str(raw.get("name") or "").strip()
        safe = _safe_float(raw.get("safe"))
        warning = _safe_float(raw.get("warning"))
        if not name:
            raise ValueError("Each threshold profile requires non-empty name.")
        if name in seen:
            raise ValueError(f"Duplicate threshold profile name: {name}")
        if safe is None or warning is None:
            raise ValueError(f"Invalid threshold values for profile: {name}")
        if not (0.0 <= safe < warning <= 1.0):
            raise ValueError(f"Threshold constraint violated for profile {name}: require 0 <= safe < warning <= 1.")
        normalized.append(
            {
                "name": name,
                "safe": float(safe),
                "warning": float(warning),
            }
        )
        seen.add(name)
    return normalized


def _build_stats_for_rows(
    rows: list[dict[str, Any]],
    current_scenario_name: str,
) -> dict[str, dict[str, Any]]:
    metrics_to_collect = [
        f"{current_scenario_name}_max_risk",
        f"{current_scenario_name}_mean_risk",
        f"{current_scenario_name}_warning_area_nm2",
        f"{current_scenario_name}_caution_area_nm2",
        "slowdown_mean_risk_delta",
        "speedup_mean_risk_delta",
        "slowdown_warning_area_nm2_delta",
        "speedup_warning_area_nm2_delta",
        "slowdown_caution_area_nm2_delta",
        "speedup_caution_area_nm2_delta",
    ]
    values: dict[str, list[float]] = {metric: [] for metric in metrics_to_collect}
    for row in rows:
        for metric in metrics_to_collect:
            numeric = _safe_float(row.get(metric))
            if numeric is None:
                continue
            values[metric].append(float(numeric))

    stats: dict[str, dict[str, Any]] = {}
    for metric, metric_values in values.items():
        stats[metric] = _build_metric_stats(metric_values)
    return stats


def _build_vs_baseline_rows(
    rows: list[dict[str, Any]],
    baseline_profile: str,
) -> list[dict[str, Any]]:
    by_run_profile: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        run_label = str(row.get("run_label", ""))
        profile_name = str(row.get("profile_name", ""))
        if not run_label or not profile_name:
            continue
        key = (run_label, profile_name)
        if key not in by_run_profile:
            by_run_profile[key] = {
                "run_label": run_label,
                "profile_name": profile_name,
                "speedup_mean_risk_delta_values": [],
                "speedup_caution_area_nm2_delta_values": [],
                "speedup_warning_area_nm2_delta_values": [],
            }
        bucket = by_run_profile[key]
        for metric in (
            "speedup_mean_risk_delta",
            "speedup_caution_area_nm2_delta",
            "speedup_warning_area_nm2_delta",
        ):
            numeric = _safe_float(row.get(metric))
            if numeric is not None:
                bucket[f"{metric}_values"].append(float(numeric))

    mean_by_run_profile: dict[tuple[str, str], dict[str, float | None]] = {}
    for key, bucket in by_run_profile.items():
        mean_by_run_profile[key] = {
            "speedup_mean_risk_delta_mean": (
                float(statistics.fmean(bucket["speedup_mean_risk_delta_values"]))
                if bucket["speedup_mean_risk_delta_values"]
                else None
            ),
            "speedup_caution_area_nm2_delta_mean": (
                float(statistics.fmean(bucket["speedup_caution_area_nm2_delta_values"]))
                if bucket["speedup_caution_area_nm2_delta_values"]
                else None
            ),
            "speedup_warning_area_nm2_delta_mean": (
                float(statistics.fmean(bucket["speedup_warning_area_nm2_delta_values"]))
                if bucket["speedup_warning_area_nm2_delta_values"]
                else None
            ),
        }

    comparisons: list[dict[str, Any]] = []
    run_labels = sorted({run_label for run_label, _ in mean_by_run_profile.keys()})
    for run_label in run_labels:
        baseline_metrics = mean_by_run_profile.get((run_label, baseline_profile), {})
        for (label, profile_name), metrics in sorted(mean_by_run_profile.items()):
            if label != run_label or profile_name == baseline_profile:
                continue
            comparison = {
                "run_label": run_label,
                "baseline_profile": baseline_profile,
                "profile_name": profile_name,
            }
            for metric in (
                "speedup_mean_risk_delta_mean",
                "speedup_caution_area_nm2_delta_mean",
                "speedup_warning_area_nm2_delta_mean",
            ):
                base = _safe_float(baseline_metrics.get(metric))
                current = _safe_float(metrics.get(metric))
                comparison[metric] = current
                comparison[f"{metric}_vs_baseline"] = (
                    float(current - base) if current is not None and base is not None else None
                )
            comparisons.append(comparison)
    return comparisons


def _write_rows_csv(path_value: str | Path, rows: list[dict[str, Any]]) -> str:
    destination = Path(path_value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_label",
        "sample_rank",
        "own_mmsi",
        "timestamp",
        "profile_name",
        "safe_threshold",
        "warning_threshold",
        "target_count",
        "current_max_risk",
        "current_mean_risk",
        "current_warning_area_nm2",
        "current_caution_area_nm2",
        "slowdown_mean_risk_delta",
        "speedup_mean_risk_delta",
        "slowdown_warning_area_nm2_delta",
        "speedup_warning_area_nm2_delta",
        "slowdown_caution_area_nm2_delta",
        "speedup_caution_area_nm2_delta",
        "snapshot_json",
        "result_json",
    ]
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in fieldnames})
    return str(destination)


def build_scenario_threshold_sweep_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Scenario Threshold Sweep Summary",
        "",
        f"- source_scenario_shift_summary: `{summary.get('scenario_shift_summary_path', '')}`",
        f"- sample_count: `{summary.get('sample_count', 0)}`",
        f"- profile_count: `{summary.get('profile_count', 0)}`",
        f"- baseline_profile: `{summary.get('baseline_profile', '')}`",
        "",
        "| profile | safe | warning |",
        "|---|---:|---:|",
    ]
    for profile in summary.get("threshold_profiles", []):
        lines.append(f"| {profile.get('name')} | {profile.get('safe')} | {profile.get('warning')} |")

    for run in summary.get("runs", []):
        lines.extend(
            [
                "",
                f"## {run.get('label', 'unknown')}",
                "",
                "| profile | samples | speedup_mean_risk_delta_mean | speedup_caution_area_delta_mean | speedup_warning_area_delta_mean |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for profile_stats in run.get("profiles", []):
            delta_stats = profile_stats.get("delta_stats", {})
            lines.append(
                "| {profile} | {count} | {mean_risk} | {caution} | {warning} |".format(
                    profile=profile_stats.get("name", ""),
                    count=profile_stats.get("sample_count", 0),
                    mean_risk=_fmt((delta_stats.get("speedup_mean_risk_delta") or {}).get("mean")),
                    caution=_fmt((delta_stats.get("speedup_caution_area_nm2_delta") or {}).get("mean")),
                    warning=_fmt((delta_stats.get("speedup_warning_area_nm2_delta") or {}).get("mean")),
                )
            )

        lines.extend(
            [
                "",
                "| profile_vs_baseline | speedup_mean_risk_delta_delta | speedup_caution_area_delta_delta | speedup_warning_area_delta_delta |",
                "|---|---:|---:|---:|",
            ]
        )
        for item in run.get("profile_comparison_vs_baseline", []):
            lines.append(
                "| {profile} | {mean_risk_delta} | {caution_delta} | {warning_delta} |".format(
                    profile=item.get("profile_name", ""),
                    mean_risk_delta=_fmt(item.get("speedup_mean_risk_delta_mean_vs_baseline")),
                    caution_delta=_fmt(item.get("speedup_caution_area_nm2_delta_mean_vs_baseline")),
                    warning_delta=_fmt(item.get("speedup_warning_area_nm2_delta_mean_vs_baseline")),
                )
            )

    lines.append("")
    return "\n".join(lines)


def run_scenario_threshold_sweep(
    scenario_shift_summary_path: str | Path,
    output_prefix: str | Path,
    config_path: str | Path = "configs/base.toml",
    threshold_profiles: list[dict[str, Any]] | None = None,
    baseline_profile: str = "base",
    current_scenario_name: str = "current",
    save_profile_results: bool = False,
) -> dict[str, Any]:
    scenario_shift_summary = json.loads(Path(scenario_shift_summary_path).read_text(encoding="utf-8"))
    config = load_config(Path(config_path))
    profiles = _parse_threshold_profiles(
        threshold_profiles=threshold_profiles,
        default_safe=float(config.thresholds.safe),
        default_warning=float(config.thresholds.warning),
    )
    profile_names = {profile["name"] for profile in profiles}
    effective_baseline = baseline_profile if baseline_profile in profile_names else profiles[0]["name"]

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    rows_csv_path = prefix.with_name(f"{prefix.name}_rows.csv")

    all_rows: list[dict[str, Any]] = []
    run_payloads: list[dict[str, Any]] = []
    result_root = prefix.with_name(f"{prefix.name}_results")
    if save_profile_results:
        result_root.mkdir(parents=True, exist_ok=True)

    for run in scenario_shift_summary.get("runs", []):
        run_label = str(run.get("label") or "unknown")
        sample_rows = [row for row in run.get("samples", []) if str(row.get("status")) == "completed" and row.get("snapshot_json")]
        run_rows: list[dict[str, Any]] = []
        for sample in sample_rows:
            sample_rank = int(sample.get("selected_rank") or 0)
            own_mmsi = str(sample.get("own_mmsi") or "")
            timestamp = str(sample.get("timestamp") or "")
            snapshot_json = str(sample.get("snapshot_json") or "")
            snapshot = load_snapshot(snapshot_json)

            for profile in profiles:
                threshold_cfg = ThresholdConfig(
                    safe=float(profile["safe"]),
                    warning=float(profile["warning"]),
                    density_radius_nm=float(config.thresholds.density_radius_nm),
                    density_reference_count=float(config.thresholds.density_reference_count),
                )
                config_for_profile = replace(config, thresholds=threshold_cfg)
                result = run_snapshot(snapshot=snapshot, config=config_for_profile)
                scenarios = _extract_scenarios(result)
                deltas = _compute_deltas_vs_current(scenarios, current_scenario_name=str(current_scenario_name))
                current_metrics = scenarios.get(current_scenario_name, {})

                result_json_path = ""
                if save_profile_results:
                    result_name = (
                        f"{_sanitize_key(run_label)}_s{sample_rank:02d}_{_sanitize_key(own_mmsi)}_"
                        f"{_sanitize_key(timestamp)}_{_sanitize_key(str(profile['name']))}_result.json"
                    )
                    result_path = result_root / result_name
                    save_result(result_path, result)
                    result_json_path = str(result_path)

                row = {
                    "run_label": run_label,
                    "sample_rank": sample_rank,
                    "own_mmsi": own_mmsi,
                    "timestamp": timestamp,
                    "profile_name": profile["name"],
                    "safe_threshold": profile["safe"],
                    "warning_threshold": profile["warning"],
                    "target_count": len(snapshot.targets),
                    "current_max_risk": _safe_float(current_metrics.get("max_risk")),
                    "current_mean_risk": _safe_float(current_metrics.get("mean_risk")),
                    "current_warning_area_nm2": _safe_float(current_metrics.get("warning_area_nm2")),
                    "current_caution_area_nm2": _safe_float(current_metrics.get("caution_area_nm2")),
                    "slowdown_mean_risk_delta": _safe_float(deltas.get("slowdown_mean_risk_delta")),
                    "speedup_mean_risk_delta": _safe_float(deltas.get("speedup_mean_risk_delta")),
                    "slowdown_warning_area_nm2_delta": _safe_float(deltas.get("slowdown_warning_area_nm2_delta")),
                    "speedup_warning_area_nm2_delta": _safe_float(deltas.get("speedup_warning_area_nm2_delta")),
                    "slowdown_caution_area_nm2_delta": _safe_float(deltas.get("slowdown_caution_area_nm2_delta")),
                    "speedup_caution_area_nm2_delta": _safe_float(deltas.get("speedup_caution_area_nm2_delta")),
                    "snapshot_json": snapshot_json,
                    "result_json": result_json_path,
                }
                all_rows.append(row)
                run_rows.append(row)

        profile_payloads: list[dict[str, Any]] = []
        for profile in profiles:
            profile_name = str(profile["name"])
            rows_for_profile = [row for row in run_rows if str(row.get("profile_name")) == profile_name]
            profile_payloads.append(
                {
                    "name": profile_name,
                    "safe": float(profile["safe"]),
                    "warning": float(profile["warning"]),
                    "sample_count": len(rows_for_profile),
                    "delta_stats": _build_stats_for_rows(rows_for_profile, current_scenario_name=current_scenario_name),
                }
            )
        run_comparisons = [
            row
            for row in _build_vs_baseline_rows(run_rows, baseline_profile=effective_baseline)
            if row.get("run_label") == run_label
        ]
        run_payloads.append(
            {
                "label": run_label,
                "sample_count": len(sample_rows),
                "profiles": profile_payloads,
                "profile_comparison_vs_baseline": run_comparisons,
            }
        )

    rows_csv_written = _write_rows_csv(rows_csv_path, all_rows)
    summary: dict[str, Any] = {
        "status": "completed",
        "scenario_shift_summary_path": str(scenario_shift_summary_path),
        "config_path": str(config_path),
        "sample_count": len({(row["run_label"], row["sample_rank"], row["timestamp"]) for row in all_rows}),
        "row_count": len(all_rows),
        "profile_count": len(profiles),
        "threshold_profiles": profiles,
        "baseline_profile": effective_baseline,
        "current_scenario_name": str(current_scenario_name),
        "save_profile_results": bool(save_profile_results),
        "runs": run_payloads,
        "rows_csv_path": rows_csv_written,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_scenario_threshold_sweep_markdown(summary), encoding="utf-8")
    return summary
