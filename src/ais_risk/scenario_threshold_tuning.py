from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Any

from .config import load_config
from .scenario_threshold_sweep import run_scenario_threshold_sweep


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


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _frange(start: float, stop: float, step: float) -> list[float]:
    if step <= 0.0:
        raise ValueError("step must be positive.")
    values: list[float] = []
    current = float(start)
    guard = 0
    while current <= float(stop) + 1e-9:
        values.append(round(current, 6))
        current += float(step)
        guard += 1
        if guard > 100000:
            raise RuntimeError("frange guard overflow.")
    return values


def _range_penalty(value: float, min_value: float, max_value: float) -> float:
    if value < min_value:
        return min_value - value
    if value > max_value:
        return value - max_value
    return 0.0


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if q <= 0.0:
        return float(values[0])
    if q >= 1.0:
        return float(values[-1])
    index = int(round((len(values) - 1) * q))
    index = max(0, min(index, len(values) - 1))
    return float(values[index])


def _build_profiles(
    safe_min: float,
    safe_max: float,
    safe_step: float,
    warning_min: float,
    warning_max: float,
    warning_step: float,
) -> list[dict[str, float | str]]:
    safe_values = _frange(safe_min, safe_max, safe_step)
    warning_values = _frange(warning_min, warning_max, warning_step)
    profiles: list[dict[str, float | str]] = []
    for safe in safe_values:
        for warning in warning_values:
            if safe >= warning:
                continue
            name = f"s{safe:.2f}_w{warning:.2f}".replace(".", "p")
            profiles.append(
                {
                    "name": name,
                    "safe": float(round(safe, 4)),
                    "warning": float(round(warning, 4)),
                }
            )
    if not profiles:
        raise ValueError("No valid threshold profiles generated from provided ranges.")
    return profiles


def _read_sweep_rows_csv(path_value: str | Path) -> list[dict[str, Any]]:
    path = Path(path_value)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append(
                {
                    "run_label": str(raw.get("run_label") or ""),
                    "profile_name": str(raw.get("profile_name") or ""),
                    "safe_threshold": _safe_float(raw.get("safe_threshold")),
                    "warning_threshold": _safe_float(raw.get("warning_threshold")),
                    "speedup_warning_area_nm2_delta": _safe_float(raw.get("speedup_warning_area_nm2_delta")),
                    "speedup_caution_area_nm2_delta": _safe_float(raw.get("speedup_caution_area_nm2_delta")),
                    "speedup_mean_risk_delta": _safe_float(raw.get("speedup_mean_risk_delta")),
                    "current_warning_area_nm2": _safe_float(raw.get("current_warning_area_nm2")),
                    "current_caution_area_nm2": _safe_float(raw.get("current_caution_area_nm2")),
                }
            )
    return rows


def _compute_profile_metrics_from_rows(
    sweep_rows: list[dict[str, Any]],
    run_labels: list[str],
    epsilon: float,
) -> list[dict[str, Any]]:
    if not run_labels:
        return []
    run_count = len(run_labels)
    by_profile_run: dict[tuple[str, str], list[dict[str, Any]]] = {}
    profile_thresholds: dict[str, tuple[float | None, float | None]] = {}
    for row in sweep_rows:
        profile_name = str(row.get("profile_name", ""))
        run_label = str(row.get("run_label", ""))
        if not profile_name or not run_label:
            continue
        by_profile_run.setdefault((profile_name, run_label), []).append(row)
        if profile_name not in profile_thresholds:
            profile_thresholds[profile_name] = (
                _safe_float(row.get("safe_threshold")),
                _safe_float(row.get("warning_threshold")),
            )

    results: list[dict[str, Any]] = []
    for profile_name in sorted(profile_thresholds.keys()):
        warning_values_abs: list[float] = []
        caution_values_abs: list[float] = []
        mean_risk_values: list[float] = []
        current_warning_values: list[float] = []
        current_caution_values: list[float] = []
        nonzero_warning_runs = 0

        for run_label in run_labels:
            rows = by_profile_run.get((profile_name, run_label), [])
            warning_samples = [float(item["speedup_warning_area_nm2_delta"]) for item in rows if item.get("speedup_warning_area_nm2_delta") is not None]
            caution_samples = [float(item["speedup_caution_area_nm2_delta"]) for item in rows if item.get("speedup_caution_area_nm2_delta") is not None]
            mean_risk_samples = [float(item["speedup_mean_risk_delta"]) for item in rows if item.get("speedup_mean_risk_delta") is not None]
            current_warning_samples = [float(item["current_warning_area_nm2"]) for item in rows if item.get("current_warning_area_nm2") is not None]
            current_caution_samples = [float(item["current_caution_area_nm2"]) for item in rows if item.get("current_caution_area_nm2") is not None]

            run_warning_mean = _mean(warning_samples)
            run_caution_mean = _mean(caution_samples)
            run_mean_risk_mean = _mean(mean_risk_samples)
            run_current_warning_mean = _mean(current_warning_samples)
            run_current_caution_mean = _mean(current_caution_samples)

            if run_warning_mean is not None:
                warning_abs = abs(float(run_warning_mean))
                warning_values_abs.append(warning_abs)
                if warning_abs > float(epsilon):
                    nonzero_warning_runs += 1
            if run_caution_mean is not None:
                caution_values_abs.append(abs(float(run_caution_mean)))
            if run_mean_risk_mean is not None:
                mean_risk_values.append(float(run_mean_risk_mean))
            if run_current_warning_mean is not None:
                current_warning_values.append(float(run_current_warning_mean))
            if run_current_caution_mean is not None:
                current_caution_values.append(float(run_current_caution_mean))

        safe_threshold, warning_threshold = profile_thresholds.get(profile_name, (None, None))
        results.append(
            {
                "profile_name": profile_name,
                "safe_threshold": safe_threshold,
                "warning_threshold": warning_threshold,
                "run_count": run_count,
                "warning_nonzero_ratio": float(nonzero_warning_runs) / float(run_count),
                "speedup_warning_delta_abs_mean": _mean(warning_values_abs) or 0.0,
                "speedup_caution_delta_abs_mean": _mean(caution_values_abs) or 0.0,
                "speedup_mean_risk_delta_mean": _mean(mean_risk_values) or 0.0,
                "current_warning_area_nm2_mean": _mean(current_warning_values) or 0.0,
                "current_caution_area_nm2_mean": _mean(current_caution_values) or 0.0,
            }
        )
    return results


def _extract_profile_metrics(sweep_summary: dict[str, Any], epsilon: float) -> list[dict[str, Any]]:
    run_count = len(sweep_summary.get("runs", []))
    by_profile: dict[str, dict[str, Any]] = {}
    for run in sweep_summary.get("runs", []):
        run_label = str(run.get("label") or "")
        for profile in run.get("profiles", []):
            profile_name = str(profile.get("name") or "")
            if not profile_name:
                continue
            bucket = by_profile.get(profile_name)
            if bucket is None:
                bucket = {
                    "profile_name": profile_name,
                    "safe_threshold": _safe_float(profile.get("safe")),
                    "warning_threshold": _safe_float(profile.get("warning")),
                    "run_metrics": [],
                }
                by_profile[profile_name] = bucket
            delta_stats = profile.get("delta_stats", {})
            bucket["run_metrics"].append(
                {
                    "run_label": run_label,
                    "speedup_warning_area_nm2_delta_mean": _safe_float((delta_stats.get("speedup_warning_area_nm2_delta") or {}).get("mean")),
                    "speedup_caution_area_nm2_delta_mean": _safe_float((delta_stats.get("speedup_caution_area_nm2_delta") or {}).get("mean")),
                    "speedup_mean_risk_delta_mean": _safe_float((delta_stats.get("speedup_mean_risk_delta") or {}).get("mean")),
                    "current_warning_area_nm2_mean": _safe_float((delta_stats.get("current_warning_area_nm2") or {}).get("mean")),
                    "current_caution_area_nm2_mean": _safe_float((delta_stats.get("current_caution_area_nm2") or {}).get("mean")),
                }
            )

    rows: list[dict[str, Any]] = []
    for profile_name, bucket in by_profile.items():
        run_metrics = list(bucket.get("run_metrics", []))
        warning_values = [
            abs(float(item["speedup_warning_area_nm2_delta_mean"]))
            for item in run_metrics
            if item.get("speedup_warning_area_nm2_delta_mean") is not None
        ]
        caution_values = [
            abs(float(item["speedup_caution_area_nm2_delta_mean"]))
            for item in run_metrics
            if item.get("speedup_caution_area_nm2_delta_mean") is not None
        ]
        mean_risk_values = [
            float(item["speedup_mean_risk_delta_mean"])
            for item in run_metrics
            if item.get("speedup_mean_risk_delta_mean") is not None
        ]
        current_warning_values = [
            float(item["current_warning_area_nm2_mean"])
            for item in run_metrics
            if item.get("current_warning_area_nm2_mean") is not None
        ]
        current_caution_values = [
            float(item["current_caution_area_nm2_mean"])
            for item in run_metrics
            if item.get("current_caution_area_nm2_mean") is not None
        ]

        nonzero_warning_runs = sum(1 for value in warning_values if value > float(epsilon))
        warning_nonzero_ratio = (float(nonzero_warning_runs) / float(run_count)) if run_count > 0 else 0.0
        rows.append(
            {
                "profile_name": profile_name,
                "safe_threshold": bucket.get("safe_threshold"),
                "warning_threshold": bucket.get("warning_threshold"),
                "run_count": run_count,
                "warning_nonzero_ratio": warning_nonzero_ratio,
                "speedup_warning_delta_abs_mean": _mean(warning_values) or 0.0,
                "speedup_caution_delta_abs_mean": _mean(caution_values) or 0.0,
                "speedup_mean_risk_delta_mean": _mean(mean_risk_values) or 0.0,
                "current_warning_area_nm2_mean": _mean(current_warning_values) or 0.0,
                "current_caution_area_nm2_mean": _mean(current_caution_values) or 0.0,
            }
        )
    return rows


def _score_profiles(
    rows: list[dict[str, Any]],
    target_warning_nonzero_ratio: float,
    min_warning_delta_abs_mean: float,
    min_caution_delta_abs_mean: float,
    warning_area_min_nm2: float,
    warning_area_max_nm2: float,
    caution_area_min_nm2: float,
    caution_area_max_nm2: float,
    weight_warning_ratio: float,
    weight_warning_delta: float,
    weight_caution_delta: float,
    weight_warning_area_range: float,
    weight_caution_area_range: float,
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for row in rows:
        warning_ratio = float(row.get("warning_nonzero_ratio") or 0.0)
        warning_abs = float(row.get("speedup_warning_delta_abs_mean") or 0.0)
        caution_abs = float(row.get("speedup_caution_delta_abs_mean") or 0.0)
        current_warning_mean = float(row.get("current_warning_area_nm2_mean") or 0.0)
        current_caution_mean = float(row.get("current_caution_area_nm2_mean") or 0.0)

        term_warning_ratio = abs(warning_ratio - float(target_warning_nonzero_ratio))
        term_warning_delta = max(0.0, float(min_warning_delta_abs_mean) - warning_abs)
        term_caution_delta = max(0.0, float(min_caution_delta_abs_mean) - caution_abs)
        term_warning_area = _range_penalty(
            current_warning_mean,
            min_value=float(warning_area_min_nm2),
            max_value=float(warning_area_max_nm2),
        )
        term_caution_area = _range_penalty(
            current_caution_mean,
            min_value=float(caution_area_min_nm2),
            max_value=float(caution_area_max_nm2),
        )
        objective = (
            float(weight_warning_ratio) * term_warning_ratio
            + float(weight_warning_delta) * term_warning_delta
            + float(weight_caution_delta) * term_caution_delta
            + float(weight_warning_area_range) * term_warning_area
            + float(weight_caution_area_range) * term_caution_area
        )

        payload = dict(row)
        payload.update(
            {
                "objective_score": objective,
                "term_warning_ratio": term_warning_ratio,
                "term_warning_delta": term_warning_delta,
                "term_caution_delta": term_caution_delta,
                "term_warning_area_range": term_warning_area,
                "term_caution_area_range": term_caution_area,
            }
        )
        scored.append(payload)

    scored.sort(
        key=lambda item: (
            float(item.get("objective_score") or 0.0),
            -float(item.get("speedup_caution_delta_abs_mean") or 0.0),
            -float(item.get("speedup_warning_delta_abs_mean") or 0.0),
            str(item.get("profile_name", "")),
        )
    )
    for index, row in enumerate(scored, start=1):
        row["rank"] = index
    return scored


def _bootstrap_profile_stats(
    sweep_rows: list[dict[str, Any]],
    profile_names: list[str],
    run_labels: list[str],
    epsilon: float,
    objective_kwargs: dict[str, float],
    bootstrap_iterations: int,
    bootstrap_random_seed: int,
) -> dict[str, Any]:
    if bootstrap_iterations <= 0 or not profile_names or not run_labels:
        return {"enabled": False, "requested_iterations": int(bootstrap_iterations), "iterations": 0, "profile_stats": {}}

    by_run_profile: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in sweep_rows:
        run_label = str(row.get("run_label", ""))
        profile_name = str(row.get("profile_name", ""))
        if not run_label or not profile_name:
            continue
        by_run_profile.setdefault((run_label, profile_name), []).append(row)

    rng = random.Random(int(bootstrap_random_seed))
    top1_count: dict[str, int] = {profile: 0 for profile in profile_names}
    objective_samples: dict[str, list[float]] = {profile: [] for profile in profile_names}
    effective_iterations = 0

    for _ in range(int(bootstrap_iterations)):
        sampled_runs = [rng.choice(run_labels) for _ in run_labels]
        synthetic_labels = [f"boot_run_{index:02d}" for index in range(len(sampled_runs))]
        resampled_rows: list[dict[str, Any]] = []
        for synthetic_label, sampled_run in zip(synthetic_labels, sampled_runs, strict=True):
            for profile_name in profile_names:
                source_rows = by_run_profile.get((sampled_run, profile_name), [])
                if not source_rows:
                    continue
                for _ in range(len(source_rows)):
                    picked = dict(rng.choice(source_rows))
                    picked["run_label"] = synthetic_label
                    resampled_rows.append(picked)

        metrics = _compute_profile_metrics_from_rows(
            sweep_rows=resampled_rows,
            run_labels=synthetic_labels,
            epsilon=float(epsilon),
        )
        scored = _score_profiles(
            rows=metrics,
            target_warning_nonzero_ratio=float(objective_kwargs["target_warning_nonzero_ratio"]),
            min_warning_delta_abs_mean=float(objective_kwargs["min_warning_delta_abs_mean"]),
            min_caution_delta_abs_mean=float(objective_kwargs["min_caution_delta_abs_mean"]),
            warning_area_min_nm2=float(objective_kwargs["warning_area_min_nm2"]),
            warning_area_max_nm2=float(objective_kwargs["warning_area_max_nm2"]),
            caution_area_min_nm2=float(objective_kwargs["caution_area_min_nm2"]),
            caution_area_max_nm2=float(objective_kwargs["caution_area_max_nm2"]),
            weight_warning_ratio=float(objective_kwargs["weight_warning_ratio"]),
            weight_warning_delta=float(objective_kwargs["weight_warning_delta"]),
            weight_caution_delta=float(objective_kwargs["weight_caution_delta"]),
            weight_warning_area_range=float(objective_kwargs["weight_warning_area_range"]),
            weight_caution_area_range=float(objective_kwargs["weight_caution_area_range"]),
        )
        if not scored:
            continue

        effective_iterations += 1
        top_name = str(scored[0].get("profile_name", ""))
        if top_name in top1_count:
            top1_count[top_name] += 1
        for row in scored:
            profile_name = str(row.get("profile_name", ""))
            value = _safe_float(row.get("objective_score"))
            if profile_name in objective_samples and value is not None:
                objective_samples[profile_name].append(float(value))

    profile_stats: dict[str, dict[str, Any]] = {}
    for profile_name in profile_names:
        values = sorted(objective_samples.get(profile_name, []))
        objective_mean = _mean(values)
        variance = _mean([(item - objective_mean) ** 2 for item in values]) if values and objective_mean is not None else None
        objective_std = (variance ** 0.5) if variance is not None else None
        top1_frequency = (
            float(top1_count.get(profile_name, 0)) / float(effective_iterations)
            if effective_iterations > 0
            else None
        )
        profile_stats[profile_name] = {
            "bootstrap_top1_frequency": top1_frequency,
            "bootstrap_objective_mean": objective_mean,
            "bootstrap_objective_std": objective_std,
            "bootstrap_objective_q05": _quantile(values, 0.05),
            "bootstrap_objective_q95": _quantile(values, 0.95),
            "bootstrap_sample_count": len(values),
        }

    return {
        "enabled": True,
        "requested_iterations": int(bootstrap_iterations),
        "iterations": effective_iterations,
        "profile_stats": profile_stats,
    }


def _write_rows_csv(path_value: str | Path, rows: list[dict[str, Any]]) -> str:
    destination = Path(path_value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "rank",
        "profile_name",
        "safe_threshold",
        "warning_threshold",
        "run_count",
        "objective_score",
        "warning_nonzero_ratio",
        "speedup_warning_delta_abs_mean",
        "speedup_caution_delta_abs_mean",
        "speedup_mean_risk_delta_mean",
        "current_warning_area_nm2_mean",
        "current_caution_area_nm2_mean",
        "term_warning_ratio",
        "term_warning_delta",
        "term_caution_delta",
        "term_warning_area_range",
        "term_caution_area_range",
        "bootstrap_top1_frequency",
        "bootstrap_objective_mean",
        "bootstrap_objective_std",
        "bootstrap_objective_q05",
        "bootstrap_objective_q95",
        "bootstrap_sample_count",
    ]
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})
    return str(destination)


def build_scenario_threshold_tuning_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Scenario Threshold Tuning Summary",
        "",
        f"- scenario_shift_summary: `{summary.get('scenario_shift_summary_path', '')}`",
        f"- sweep_summary: `{summary.get('sweep_summary_path', '')}`",
        f"- candidate_profile_count: `{summary.get('candidate_profile_count', 0)}`",
        "",
        "## Objective",
        "",
        f"- target_warning_nonzero_ratio: `{summary.get('target_warning_nonzero_ratio')}`",
        f"- min_warning_delta_abs_mean: `{summary.get('min_warning_delta_abs_mean')}`",
        f"- min_caution_delta_abs_mean: `{summary.get('min_caution_delta_abs_mean')}`",
        f"- warning_area_range_nm2: `{summary.get('warning_area_range_nm2')}`",
        f"- caution_area_range_nm2: `{summary.get('caution_area_range_nm2')}`",
        "",
        "## Recommended Profile",
        "",
        f"- profile_name: `{summary.get('recommended_profile_name', '')}`",
        f"- safe: `{summary.get('recommended_safe_threshold')}`",
        f"- warning: `{summary.get('recommended_warning_threshold')}`",
        f"- objective_score: `{_fmt(summary.get('recommended_objective_score'))}`",
        f"- bootstrap_top1_frequency: `{_fmt(summary.get('recommended_bootstrap_top1_frequency'))}`",
        f"- bootstrap_iterations: `{summary.get('bootstrap_effective_iterations', 0)}` / `{summary.get('bootstrap_requested_iterations', 0)}`",
        f"- bootstrap_consensus_profile: `{summary.get('bootstrap_consensus_profile_name', '')}` (freq `{_fmt(summary.get('bootstrap_consensus_profile_frequency'))}`)",
        "",
        "| rank | profile | safe | warning | objective | bootstrap_top1 | warning_nonzero_ratio | speedup_warning_abs_mean | speedup_caution_abs_mean | current_warning_area_mean | current_caution_area_mean |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.get("top_rows", []):
        lines.append(
            "| {rank} | {profile} | {safe} | {warning} | {objective} | {boot} | {ratio} | {warning_abs} | {caution_abs} | {current_warning} | {current_caution} |".format(
                rank=row.get("rank", ""),
                profile=row.get("profile_name", ""),
                safe=row.get("safe_threshold", ""),
                warning=row.get("warning_threshold", ""),
                objective=_fmt(row.get("objective_score")),
                boot=_fmt(row.get("bootstrap_top1_frequency")),
                ratio=_fmt(row.get("warning_nonzero_ratio")),
                warning_abs=_fmt(row.get("speedup_warning_delta_abs_mean")),
                caution_abs=_fmt(row.get("speedup_caution_delta_abs_mean")),
                current_warning=_fmt(row.get("current_warning_area_nm2_mean")),
                current_caution=_fmt(row.get("current_caution_area_nm2_mean")),
            )
        )
    lines.append("")
    return "\n".join(lines)


def run_scenario_threshold_tuning(
    scenario_shift_summary_path: str | Path,
    output_prefix: str | Path,
    config_path: str | Path = "configs/base.toml",
    safe_min: float = 0.25,
    safe_max: float = 0.45,
    safe_step: float = 0.05,
    warning_min: float = 0.55,
    warning_max: float = 0.80,
    warning_step: float = 0.05,
    current_scenario_name: str = "current",
    epsilon_nonzero_nm2: float = 1e-9,
    target_warning_nonzero_ratio: float = 0.40,
    min_warning_delta_abs_mean: float = 0.005,
    min_caution_delta_abs_mean: float = 0.05,
    warning_area_min_nm2: float = 0.0,
    warning_area_max_nm2: float = 0.15,
    caution_area_min_nm2: float = 0.05,
    caution_area_max_nm2: float = 1.2,
    weight_warning_ratio: float = 1.0,
    weight_warning_delta: float = 1.0,
    weight_caution_delta: float = 1.0,
    weight_warning_area_range: float = 1.0,
    weight_caution_area_range: float = 1.0,
    top_k: int = 10,
    bootstrap_iterations: int = 0,
    bootstrap_random_seed: int = 42,
) -> dict[str, Any]:
    config = load_config(Path(config_path))
    profiles = _build_profiles(
        safe_min=float(safe_min),
        safe_max=float(safe_max),
        safe_step=float(safe_step),
        warning_min=float(warning_min),
        warning_max=float(warning_max),
        warning_step=float(warning_step),
    )

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    sweep_prefix = prefix.with_name(f"{prefix.name}_sweep")
    sweep_summary = run_scenario_threshold_sweep(
        scenario_shift_summary_path=scenario_shift_summary_path,
        output_prefix=sweep_prefix,
        config_path=config_path,
        threshold_profiles=profiles,
        baseline_profile=profiles[0]["name"],
        current_scenario_name=current_scenario_name,
        save_profile_results=False,
    )

    sweep_rows = _read_sweep_rows_csv(str(sweep_summary.get("rows_csv_path", "")))
    run_labels = sorted({str(row.get("run_label", "")) for row in sweep_rows if str(row.get("run_label", ""))})
    metrics = _compute_profile_metrics_from_rows(
        sweep_rows=sweep_rows,
        run_labels=run_labels,
        epsilon=float(epsilon_nonzero_nm2),
    )
    if not metrics:
        metrics = _extract_profile_metrics(
            sweep_summary=sweep_summary,
            epsilon=float(epsilon_nonzero_nm2),
        )
        if not run_labels:
            run_labels = [str(run.get("label") or "") for run in sweep_summary.get("runs", []) if str(run.get("label") or "")]

    objective_kwargs = {
        "target_warning_nonzero_ratio": float(target_warning_nonzero_ratio),
        "min_warning_delta_abs_mean": float(min_warning_delta_abs_mean),
        "min_caution_delta_abs_mean": float(min_caution_delta_abs_mean),
        "warning_area_min_nm2": float(warning_area_min_nm2),
        "warning_area_max_nm2": float(warning_area_max_nm2),
        "caution_area_min_nm2": float(caution_area_min_nm2),
        "caution_area_max_nm2": float(caution_area_max_nm2),
        "weight_warning_ratio": float(weight_warning_ratio),
        "weight_warning_delta": float(weight_warning_delta),
        "weight_caution_delta": float(weight_caution_delta),
        "weight_warning_area_range": float(weight_warning_area_range),
        "weight_caution_area_range": float(weight_caution_area_range),
    }

    scored_rows = _score_profiles(
        rows=metrics,
        target_warning_nonzero_ratio=float(objective_kwargs["target_warning_nonzero_ratio"]),
        min_warning_delta_abs_mean=float(objective_kwargs["min_warning_delta_abs_mean"]),
        min_caution_delta_abs_mean=float(objective_kwargs["min_caution_delta_abs_mean"]),
        warning_area_min_nm2=float(objective_kwargs["warning_area_min_nm2"]),
        warning_area_max_nm2=float(objective_kwargs["warning_area_max_nm2"]),
        caution_area_min_nm2=float(objective_kwargs["caution_area_min_nm2"]),
        caution_area_max_nm2=float(objective_kwargs["caution_area_max_nm2"]),
        weight_warning_ratio=float(objective_kwargs["weight_warning_ratio"]),
        weight_warning_delta=float(objective_kwargs["weight_warning_delta"]),
        weight_caution_delta=float(objective_kwargs["weight_caution_delta"]),
        weight_warning_area_range=float(objective_kwargs["weight_warning_area_range"]),
        weight_caution_area_range=float(objective_kwargs["weight_caution_area_range"]),
    )

    profile_names = [str(row.get("profile_name", "")) for row in scored_rows if str(row.get("profile_name", ""))]
    bootstrap_payload = _bootstrap_profile_stats(
        sweep_rows=sweep_rows,
        profile_names=profile_names,
        run_labels=run_labels,
        epsilon=float(epsilon_nonzero_nm2),
        objective_kwargs=objective_kwargs,
        bootstrap_iterations=max(0, int(bootstrap_iterations)),
        bootstrap_random_seed=int(bootstrap_random_seed),
    )
    for row in scored_rows:
        profile_name = str(row.get("profile_name", ""))
        stats = (bootstrap_payload.get("profile_stats") or {}).get(profile_name, {})
        row["bootstrap_top1_frequency"] = stats.get("bootstrap_top1_frequency")
        row["bootstrap_objective_mean"] = stats.get("bootstrap_objective_mean")
        row["bootstrap_objective_std"] = stats.get("bootstrap_objective_std")
        row["bootstrap_objective_q05"] = stats.get("bootstrap_objective_q05")
        row["bootstrap_objective_q95"] = stats.get("bootstrap_objective_q95")
        row["bootstrap_sample_count"] = stats.get("bootstrap_sample_count")

    bootstrap_profile_stats = dict(bootstrap_payload.get("profile_stats") or {})
    consensus_profile_name = ""
    consensus_profile_freq = None
    for profile_name, stats in bootstrap_profile_stats.items():
        freq = _safe_float(stats.get("bootstrap_top1_frequency"))
        if freq is None:
            continue
        if consensus_profile_freq is None or freq > consensus_profile_freq:
            consensus_profile_name = profile_name
            consensus_profile_freq = float(freq)

    recommended = scored_rows[0] if scored_rows else {}
    top_rows = scored_rows[: max(1, int(top_k))]
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    rows_csv_path = prefix.with_name(f"{prefix.name}_rows.csv")
    rows_csv_written = _write_rows_csv(rows_csv_path, scored_rows)

    summary: dict[str, Any] = {
        "status": "completed",
        "scenario_shift_summary_path": str(scenario_shift_summary_path),
        "config_path": str(config_path),
        "sweep_summary_path": str(sweep_summary.get("summary_json_path", "")),
        "sweep_summary_md_path": str(sweep_summary.get("summary_md_path", "")),
        "sweep_rows_csv_path": str(sweep_summary.get("rows_csv_path", "")),
        "candidate_profile_count": len(scored_rows),
        "safe_grid": [float(safe_min), float(safe_max), float(safe_step)],
        "warning_grid": [float(warning_min), float(warning_max), float(warning_step)],
        "target_warning_nonzero_ratio": float(target_warning_nonzero_ratio),
        "min_warning_delta_abs_mean": float(min_warning_delta_abs_mean),
        "min_caution_delta_abs_mean": float(min_caution_delta_abs_mean),
        "warning_area_range_nm2": [float(warning_area_min_nm2), float(warning_area_max_nm2)],
        "caution_area_range_nm2": [float(caution_area_min_nm2), float(caution_area_max_nm2)],
        "weights": {
            "warning_ratio": float(weight_warning_ratio),
            "warning_delta": float(weight_warning_delta),
            "caution_delta": float(weight_caution_delta),
            "warning_area_range": float(weight_warning_area_range),
            "caution_area_range": float(weight_caution_area_range),
        },
        "default_config_thresholds": {
            "safe": float(config.thresholds.safe),
            "warning": float(config.thresholds.warning),
        },
        "recommended_profile_name": recommended.get("profile_name"),
        "recommended_safe_threshold": recommended.get("safe_threshold"),
        "recommended_warning_threshold": recommended.get("warning_threshold"),
        "recommended_objective_score": recommended.get("objective_score"),
        "recommended_bootstrap_top1_frequency": recommended.get("bootstrap_top1_frequency"),
        "bootstrap_enabled": bool(bootstrap_payload.get("enabled", False)),
        "bootstrap_requested_iterations": int(bootstrap_payload.get("requested_iterations", 0)),
        "bootstrap_effective_iterations": int(bootstrap_payload.get("iterations", 0)),
        "bootstrap_random_seed": int(bootstrap_random_seed),
        "bootstrap_consensus_profile_name": consensus_profile_name,
        "bootstrap_consensus_profile_frequency": consensus_profile_freq,
        "top_rows": top_rows,
        "rows": scored_rows,
        "rows_csv_path": rows_csv_written,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_scenario_threshold_tuning_markdown(summary), encoding="utf-8")
    return summary
