from __future__ import annotations

import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import load_config
from .csv_tools import build_snapshot_from_curated_rows, load_curated_csv_rows, parse_timestamp
from .io import save_result, save_snapshot
from .pipeline import run_snapshot


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _slugify(text: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in str(text))


def _read_pairwise_rows(path_value: str | Path) -> list[dict[str, str]]:
    path = Path(path_value)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _aggregate_candidates(
    pairwise_rows: list[dict[str, str]],
    score_weight_rule: float,
    score_weight_density: float,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in pairwise_rows:
        own_mmsi = str(row.get("own_mmsi") or "").strip()
        timestamp = str(row.get("timestamp") or "").strip()
        if not own_mmsi or not timestamp:
            continue
        key = (own_mmsi, timestamp)
        item = grouped.get(key)
        if item is None:
            item = {
                "own_mmsi": own_mmsi,
                "timestamp": timestamp,
                "pair_rows": 0,
                "rule_score_sum": 0.0,
                "local_target_sum": 0.0,
            }
            grouped[key] = item
        item["pair_rows"] += 1
        item["rule_score_sum"] += _safe_float(row.get("rule_score")) or 0.0
        item["local_target_sum"] += _safe_float(row.get("local_target_count")) or 0.0

    candidates: list[dict[str, Any]] = []
    for item in grouped.values():
        pair_rows = int(item.get("pair_rows") or 0)
        if pair_rows <= 0:
            continue
        mean_rule = float(item["rule_score_sum"]) / float(pair_rows)
        mean_local = float(item["local_target_sum"]) / float(pair_rows)
        candidates.append(
            {
                "own_mmsi": item["own_mmsi"],
                "timestamp": item["timestamp"],
                "pair_rows": pair_rows,
                "mean_rule_score": mean_rule,
                "mean_local_target_count": mean_local,
            }
        )

    max_rule = max((item["mean_rule_score"] for item in candidates), default=0.0)
    max_local = max((item["mean_local_target_count"] for item in candidates), default=0.0)
    for item in candidates:
        normalized_rule = item["mean_rule_score"] / max_rule if max_rule > 0.0 else 0.0
        normalized_local = item["mean_local_target_count"] / max_local if max_local > 0.0 else 0.0
        item["selection_score"] = (score_weight_rule * normalized_rule) + (score_weight_density * normalized_local)
    candidates.sort(
        key=lambda item: (
            -float(item.get("selection_score", 0.0)),
            -float(item.get("mean_local_target_count", 0.0)),
            -float(item.get("mean_rule_score", 0.0)),
            -int(item.get("pair_rows", 0)),
            str(item.get("own_mmsi", "")),
            str(item.get("timestamp", "")),
        )
    )
    for index, item in enumerate(candidates, start=1):
        item["candidate_rank"] = index
    return candidates


def _select_candidates(
    candidates: list[dict[str, Any]],
    sample_count: int,
    min_pair_rows: int,
    min_local_target_count: float,
    min_time_gap_minutes: float,
) -> list[dict[str, Any]]:
    target_count = max(1, int(sample_count))
    min_gap_seconds = max(0.0, float(min_time_gap_minutes) * 60.0)
    selected: list[dict[str, Any]] = []
    selected_times_by_ship: dict[str, list[Any]] = defaultdict(list)

    def _passes_gap(candidate: dict[str, Any]) -> bool:
        if min_gap_seconds <= 0.0:
            return True
        ship = str(candidate.get("own_mmsi", ""))
        try:
            timestamp_dt = parse_timestamp(str(candidate.get("timestamp", "")))
        except Exception:
            return False
        for existing in selected_times_by_ship.get(ship, []):
            if abs((timestamp_dt - existing).total_seconds()) < min_gap_seconds:
                return False
        return True

    def _register(candidate: dict[str, Any], relaxed_gap: bool) -> None:
        ship = str(candidate.get("own_mmsi", ""))
        timestamp_dt = parse_timestamp(str(candidate.get("timestamp", "")))
        selected_times_by_ship[ship].append(timestamp_dt)
        payload = dict(candidate)
        payload["selection_gap_relaxed"] = relaxed_gap
        selected.append(payload)

    for candidate in candidates:
        if len(selected) >= target_count:
            break
        if int(candidate.get("pair_rows", 0)) < int(min_pair_rows):
            continue
        if float(candidate.get("mean_local_target_count", 0.0)) < float(min_local_target_count):
            continue
        if not _passes_gap(candidate):
            continue
        _register(candidate, relaxed_gap=False)

    if len(selected) < target_count and min_gap_seconds > 0.0:
        used = {(row.get("own_mmsi"), row.get("timestamp")) for row in selected}
        for candidate in candidates:
            if len(selected) >= target_count:
                break
            key = (candidate.get("own_mmsi"), candidate.get("timestamp"))
            if key in used:
                continue
            if int(candidate.get("pair_rows", 0)) < int(min_pair_rows):
                continue
            if float(candidate.get("mean_local_target_count", 0.0)) < float(min_local_target_count):
                continue
            _register(candidate, relaxed_gap=True)
            used.add(key)

    for index, item in enumerate(selected, start=1):
        item["selected_rank"] = index
    return selected


def _extract_scenarios(sample_result: Any) -> dict[str, dict[str, Any]]:
    scenarios: dict[str, dict[str, Any]] = {}
    for scenario in sample_result.scenarios:
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


def _build_delta_stats(completed_samples: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    values_by_metric: dict[str, list[float]] = defaultdict(list)
    for sample in completed_samples:
        for metric, value in (sample.get("deltas_vs_current") or {}).items():
            numeric = _safe_float(value)
            if numeric is None:
                continue
            values_by_metric[str(metric)].append(float(numeric))

    stats: dict[str, dict[str, Any]] = {}
    for metric, values in sorted(values_by_metric.items()):
        stats[metric] = _build_metric_stats(values)
    return stats


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def build_scenario_shift_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Scenario Shift Multi-Snapshot Summary",
        "",
        f"- run_count: `{summary.get('run_count', 0)}`",
        f"- completed_sample_count: `{summary.get('completed_sample_count', 0)}`",
        f"- requested_sample_count: `{summary.get('requested_sample_count', 0)}`",
        "",
    ]
    for run in summary.get("runs", []):
        lines.extend(
            [
                f"## {run.get('label', 'unknown')}",
                "",
                f"- pairwise_path: `{run.get('pairwise_path', '')}`",
                f"- curated_path: `{run.get('curated_path', '')}`",
                f"- selected_samples: `{run.get('completed_sample_count', 0)}` / `{run.get('requested_sample_count', 0)}`",
                "",
                "| idx | own_mmsi | timestamp | pair_rows | mean_local_targets | mean_rule_score | target_count | current_mean_risk | slowdown_mean_risk_delta | speedup_mean_risk_delta |",
                "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for sample in run.get("samples", []):
            if sample.get("status") != "completed":
                continue
            current = (sample.get("scenarios") or {}).get(run.get("current_scenario_name", "current"), {})
            lines.append(
                "| {idx} | {own} | {ts} | {pair_rows} | {local} | {rule} | {targets} | {current_mean} | {slowdown_delta} | {speedup_delta} |".format(
                    idx=sample.get("selected_rank", ""),
                    own=sample.get("own_mmsi", ""),
                    ts=sample.get("timestamp", ""),
                    pair_rows=sample.get("pair_rows", 0),
                    local=_fmt(sample.get("mean_local_target_count"), 2),
                    rule=_fmt(sample.get("mean_rule_score"), 4),
                    targets=sample.get("target_count", 0),
                    current_mean=_fmt(current.get("mean_risk"), 4),
                    slowdown_delta=_fmt((sample.get("deltas_vs_current") or {}).get("slowdown_mean_risk_delta"), 4),
                    speedup_delta=_fmt((sample.get("deltas_vs_current") or {}).get("speedup_mean_risk_delta"), 4),
                )
            )
        lines.extend(
            [
                "",
                "| delta_metric | count | mean | std | min | max | pos | neg | zero |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for metric, stats in (run.get("delta_stats_vs_current") or {}).items():
            lines.append(
                "| {metric} | {count} | {mean} | {std} | {min_v} | {max_v} | {pos} | {neg} | {zero} |".format(
                    metric=metric,
                    count=stats.get("count", 0),
                    mean=_fmt(stats.get("mean"), 4),
                    std=_fmt(stats.get("std"), 4),
                    min_v=_fmt(stats.get("min"), 4),
                    max_v=_fmt(stats.get("max"), 4),
                    pos=stats.get("positive_count", 0),
                    neg=stats.get("negative_count", 0),
                    zero=stats.get("zero_count", 0),
                )
            )
        lines.append("")
    return "\n".join(lines)


def run_scenario_shift_multi_snapshot(
    run_specs: list[dict[str, str]],
    output_prefix: str | Path,
    config_path: str | Path = "configs/base.toml",
    sample_count: int = 3,
    radius_nm: float = 6.0,
    max_age_minutes: float = 5.0,
    min_pair_rows: int = 2,
    min_local_target_count: float = 1.0,
    min_snapshot_targets: int = 1,
    min_time_gap_minutes: float = 120.0,
    current_scenario_name: str = "current",
    score_weight_rule: float = 0.4,
    score_weight_density: float = 0.6,
) -> dict[str, Any]:
    if not run_specs:
        raise ValueError("run_specs is empty. Provide at least one run spec with label/pairwise_path/curated_path.")

    weights_total = float(score_weight_rule) + float(score_weight_density)
    if weights_total <= 0.0:
        raise ValueError("score weights must have positive sum.")
    normalized_rule_weight = float(score_weight_rule) / weights_total
    normalized_density_weight = float(score_weight_density) / weights_total

    prefix = Path(output_prefix)
    output_dir = prefix.parent if prefix.parent != Path("") else Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")

    config = load_config(Path(config_path))
    runs: list[dict[str, Any]] = []
    requested_total = 0
    completed_total = 0

    for spec in run_specs:
        label = str(spec.get("label") or "").strip()
        pairwise_path = str(spec.get("pairwise_path") or "").strip()
        curated_path = str(spec.get("curated_path") or "").strip()
        if not label or not pairwise_path or not curated_path:
            raise ValueError("Each run spec must include label, pairwise_path, and curated_path.")

        pairwise_rows = _read_pairwise_rows(pairwise_path)
        curated_rows = load_curated_csv_rows(curated_path)
        candidates = _aggregate_candidates(
            pairwise_rows=pairwise_rows,
            score_weight_rule=normalized_rule_weight,
            score_weight_density=normalized_density_weight,
        )
        selected_candidates = _select_candidates(
            candidates=candidates,
            sample_count=max(1, int(sample_count)),
            min_pair_rows=max(1, int(min_pair_rows)),
            min_local_target_count=float(min_local_target_count),
            min_time_gap_minutes=max(0.0, float(min_time_gap_minutes)),
        )
        requested_total += max(1, int(sample_count))

        samples: list[dict[str, Any]] = []
        for candidate in selected_candidates:
            sample_payload: dict[str, Any] = {
                "status": "pending",
                "selected_rank": candidate.get("selected_rank"),
                "candidate_rank": candidate.get("candidate_rank"),
                "selection_gap_relaxed": bool(candidate.get("selection_gap_relaxed", False)),
                "own_mmsi": candidate.get("own_mmsi"),
                "timestamp": candidate.get("timestamp"),
                "pair_rows": candidate.get("pair_rows"),
                "mean_rule_score": candidate.get("mean_rule_score"),
                "mean_local_target_count": candidate.get("mean_local_target_count"),
                "selection_score": candidate.get("selection_score"),
            }
            try:
                snapshot = build_snapshot_from_curated_rows(
                    rows=curated_rows,
                    own_mmsi=str(candidate["own_mmsi"]),
                    timestamp=str(candidate["timestamp"]),
                    radius_nm=float(radius_nm),
                    max_age_minutes=float(max_age_minutes),
                )
                if len(snapshot.targets) < int(min_snapshot_targets):
                    sample_payload["status"] = "skipped"
                    sample_payload["error"] = (
                        f"target_count<{int(min_snapshot_targets)} "
                        f"(observed={len(snapshot.targets)})"
                    )
                    samples.append(sample_payload)
                    continue

                result = run_snapshot(snapshot=snapshot, config=config)
                scenarios = _extract_scenarios(result)
                deltas = _compute_deltas_vs_current(scenarios, current_scenario_name=str(current_scenario_name))
                artifact_stem = (
                    f"{_slugify(label)}_sample_{int(candidate.get('selected_rank', 0)):02d}_"
                    f"{_slugify(str(candidate['own_mmsi']))}_{_slugify(str(candidate['timestamp']))}"
                )
                snapshot_path = output_dir / f"{artifact_stem}_snapshot.json"
                result_path = output_dir / f"{artifact_stem}_result.json"
                save_snapshot(snapshot_path, snapshot)
                save_result(result_path, result)

                sample_payload.update(
                    {
                        "status": "completed",
                        "target_count": len(snapshot.targets),
                        "selection_basis": {
                            "pair_rows_on_key": candidate.get("pair_rows"),
                            "mean_rule_score": candidate.get("mean_rule_score"),
                            "mean_local_target_count": candidate.get("mean_local_target_count"),
                            "selection_score": candidate.get("selection_score"),
                        },
                        "scenarios": scenarios,
                        "deltas_vs_current": deltas,
                        "snapshot_json": str(snapshot_path),
                        "result_json": str(result_path),
                    }
                )
            except Exception as exc:
                sample_payload["status"] = "skipped"
                sample_payload["error"] = str(exc)
            samples.append(sample_payload)

        completed_samples = [sample for sample in samples if sample.get("status") == "completed"]
        completed_total += len(completed_samples)
        run_summary: dict[str, Any] = {
            "label": label,
            "pairwise_path": pairwise_path,
            "curated_path": curated_path,
            "selection_params": {
                "sample_count": max(1, int(sample_count)),
                "min_pair_rows": max(1, int(min_pair_rows)),
                "min_local_target_count": float(min_local_target_count),
                "min_snapshot_targets": max(1, int(min_snapshot_targets)),
                "min_time_gap_minutes": max(0.0, float(min_time_gap_minutes)),
                "current_scenario_name": str(current_scenario_name),
                "score_weight_rule": normalized_rule_weight,
                "score_weight_density": normalized_density_weight,
                "radius_nm": float(radius_nm),
                "max_age_minutes": float(max_age_minutes),
            },
            "requested_sample_count": max(1, int(sample_count)),
            "selected_candidate_count": len(selected_candidates),
            "completed_sample_count": len(completed_samples),
            "candidate_count_total": len(candidates),
            "current_scenario_name": str(current_scenario_name),
            "samples": samples,
            "delta_stats_vs_current": _build_delta_stats(completed_samples),
        }
        runs.append(run_summary)

    summary: dict[str, Any] = {
        "status": "completed",
        "run_count": len(runs),
        "requested_sample_count": requested_total,
        "completed_sample_count": completed_total,
        "config_path": str(config_path),
        "runs": runs,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_scenario_shift_markdown(summary), encoding="utf-8")
    return summary
