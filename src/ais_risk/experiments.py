from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from .case_mining import mine_cases_from_curated_rows
from .config import load_config
from .csv_tools import build_snapshot_from_curated_rows, load_curated_csv_rows
from .models import AblationSettings, ProjectConfig
from .pipeline import run_snapshot


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def _scenario_row(
    timestamp: str,
    scenario,
    current_summary,
) -> dict[str, str]:
    top = scenario.top_vessels[0] if scenario.top_vessels else None
    return {
        "timestamp": timestamp,
        "scenario_name": scenario.summary.scenario_name,
        "speed_multiplier": f"{scenario.summary.speed_multiplier:.2f}",
        "max_risk": f"{scenario.summary.max_risk:.6f}",
        "mean_risk": f"{scenario.summary.mean_risk:.6f}",
        "warning_area_nm2": f"{scenario.summary.warning_area_nm2:.6f}",
        "caution_area_nm2": f"{scenario.summary.caution_area_nm2:.6f}",
        "dominant_sector": scenario.summary.dominant_sector,
        "target_count": str(scenario.summary.target_count),
        "delta_max_risk_vs_current": f"{scenario.summary.max_risk - current_summary.max_risk:.6f}",
        "delta_warning_area_vs_current": f"{scenario.summary.warning_area_nm2 - current_summary.warning_area_nm2:.6f}",
        "warning_area_ratio_vs_current": f"{_safe_div(scenario.summary.warning_area_nm2, current_summary.warning_area_nm2):.6f}",
        "top_vessel_mmsi": "" if top is None else top.mmsi,
        "top_vessel_score": "" if top is None else f"{top.score:.6f}",
        "top_vessel_encounter": "" if top is None else top.encounter_type,
        "top_vessel_factors": "" if top is None else ",".join(top.top_factors),
    }


def run_baseline_experiment(
    rows: list[dict[str, str]],
    own_mmsi: str,
    config: ProjectConfig,
    radius_nm: float,
    top_n: int = 5,
    min_targets: int = 1,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    candidates = mine_cases_from_curated_rows(
        rows=rows,
        own_mmsi=own_mmsi,
        config=config,
        radius_nm=radius_nm,
        top_n=top_n,
        min_targets=min_targets,
    )
    experiment_rows: list[dict[str, str]] = []
    sector_counter: Counter[str] = Counter()
    scenario_buckets: dict[str, list[dict[str, float]]] = {}

    for candidate in candidates:
        snapshot = build_snapshot_from_curated_rows(
            rows=rows,
            own_mmsi=own_mmsi,
            timestamp=candidate["timestamp"],
            radius_nm=radius_nm,
        )
        result = run_snapshot(snapshot, config)
        current_scenario = next(
            (scenario for scenario in result.scenarios if scenario.summary.scenario_name == "current"),
            result.scenarios[0],
        )
        sector_counter[current_scenario.summary.dominant_sector] += 1
        for scenario in result.scenarios:
            experiment_rows.append(_scenario_row(result.timestamp, scenario, current_scenario.summary))
            scenario_buckets.setdefault(scenario.summary.scenario_name, []).append(
                {
                    "max_risk": scenario.summary.max_risk,
                    "mean_risk": scenario.summary.mean_risk,
                    "warning_area_nm2": scenario.summary.warning_area_nm2,
                    "delta_max_risk_vs_current": scenario.summary.max_risk - current_scenario.summary.max_risk,
                    "delta_warning_area_vs_current": scenario.summary.warning_area_nm2 - current_scenario.summary.warning_area_nm2,
                }
            )

    aggregate = {
        "case_count": len(candidates),
        "own_mmsi": own_mmsi,
        "radius_nm": radius_nm,
        "dominant_sector_counts_current": dict(sector_counter),
        "scenario_averages": {},
    }
    for scenario_name, values in scenario_buckets.items():
        count = len(values)
        aggregate["scenario_averages"][scenario_name] = {
            "avg_max_risk": sum(item["max_risk"] for item in values) / count if count else 0.0,
            "avg_mean_risk": sum(item["mean_risk"] for item in values) / count if count else 0.0,
            "avg_warning_area_nm2": sum(item["warning_area_nm2"] for item in values) / count if count else 0.0,
            "avg_delta_max_risk_vs_current": sum(item["delta_max_risk_vs_current"] for item in values) / count if count else 0.0,
            "avg_delta_warning_area_vs_current": sum(item["delta_warning_area_vs_current"] for item in values) / count if count else 0.0,
        }
    return experiment_rows, aggregate


def run_baseline_experiment_from_csv(
    input_path: str | Path,
    own_mmsi: str,
    config_path: str | Path,
    radius_nm: float,
    top_n: int = 5,
    min_targets: int = 1,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    rows = load_curated_csv_rows(input_path)
    config = load_config(config_path)
    return run_baseline_experiment(
        rows=rows,
        own_mmsi=own_mmsi,
        config=config,
        radius_nm=radius_nm,
        top_n=top_n,
        min_targets=min_targets,
    )


def save_experiment_outputs(prefix: str | Path, rows: list[dict[str, str]], aggregate: dict[str, object]) -> tuple[Path, Path]:
    prefix_path = Path(prefix)
    prefix_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = prefix_path.with_name(prefix_path.name + "_cases.csv")
    json_path = prefix_path.with_name(prefix_path.name + "_aggregate.json")

    fieldnames = [
        "timestamp",
        "scenario_name",
        "speed_multiplier",
        "max_risk",
        "mean_risk",
        "warning_area_nm2",
        "caution_area_nm2",
        "dominant_sector",
        "target_count",
        "delta_max_risk_vs_current",
        "delta_warning_area_vs_current",
        "warning_area_ratio_vs_current",
        "top_vessel_mmsi",
        "top_vessel_score",
        "top_vessel_encounter",
        "top_vessel_factors",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    return csv_path, json_path


def build_ablation_settings(name: str) -> AblationSettings:
    if name in {"distance", "dcpa", "tcpa", "bearing", "relspeed", "encounter", "density"}:
        return AblationSettings(label=f"drop_{name}", disabled_factors=(name,))
    if name == "time_decay":
        return AblationSettings(label="drop_time_decay", use_time_decay=False)
    if name == "spatial_kernel":
        return AblationSettings(label="drop_spatial_kernel", use_spatial_kernel=False)
    raise ValueError(f"Unsupported ablation: {name}")


def _ablation_scenario_row(
    timestamp: str,
    ablation_label: str,
    scenario,
    baseline_summary,
) -> dict[str, str]:
    top = scenario.top_vessels[0] if scenario.top_vessels else None
    return {
        "timestamp": timestamp,
        "ablation_label": ablation_label,
        "scenario_name": scenario.summary.scenario_name,
        "speed_multiplier": f"{scenario.summary.speed_multiplier:.2f}",
        "max_risk": f"{scenario.summary.max_risk:.6f}",
        "mean_risk": f"{scenario.summary.mean_risk:.6f}",
        "warning_area_nm2": f"{scenario.summary.warning_area_nm2:.6f}",
        "caution_area_nm2": f"{scenario.summary.caution_area_nm2:.6f}",
        "dominant_sector": scenario.summary.dominant_sector,
        "target_count": str(scenario.summary.target_count),
        "delta_max_risk_vs_baseline": f"{scenario.summary.max_risk - baseline_summary.max_risk:.6f}",
        "delta_warning_area_vs_baseline": f"{scenario.summary.warning_area_nm2 - baseline_summary.warning_area_nm2:.6f}",
        "warning_area_ratio_vs_baseline": f"{_safe_div(scenario.summary.warning_area_nm2, baseline_summary.warning_area_nm2):.6f}",
        "top_vessel_mmsi": "" if top is None else top.mmsi,
        "top_vessel_score": "" if top is None else f"{top.score:.6f}",
        "top_vessel_encounter": "" if top is None else top.encounter_type,
        "top_vessel_factors": "" if top is None else ",".join(top.top_factors),
    }


def run_ablation_experiment(
    rows: list[dict[str, str]],
    own_mmsi: str,
    config: ProjectConfig,
    radius_nm: float,
    ablation_names: list[str],
    top_n: int = 5,
    min_targets: int = 1,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    candidates = mine_cases_from_curated_rows(
        rows=rows,
        own_mmsi=own_mmsi,
        config=config,
        radius_nm=radius_nm,
        top_n=top_n,
        min_targets=min_targets,
    )
    settings_list = [AblationSettings(label="baseline")] + [build_ablation_settings(name) for name in ablation_names]
    experiment_rows: list[dict[str, str]] = []
    aggregates: dict[str, dict[str, list[dict[str, float]]]] = {}

    for candidate in candidates:
        snapshot = build_snapshot_from_curated_rows(
            rows=rows,
            own_mmsi=own_mmsi,
            timestamp=candidate["timestamp"],
            radius_nm=radius_nm,
        )
        baseline_result = run_snapshot(snapshot, config, ablation=settings_list[0])
        baseline_by_scenario = {
            scenario.summary.scenario_name: scenario.summary
            for scenario in baseline_result.scenarios
        }
        for settings in settings_list:
            result = baseline_result if settings.label == "baseline" else run_snapshot(snapshot, config, ablation=settings)
            for scenario in result.scenarios:
                baseline_summary = baseline_by_scenario[scenario.summary.scenario_name]
                experiment_rows.append(
                    _ablation_scenario_row(
                        timestamp=result.timestamp,
                        ablation_label=settings.label,
                        scenario=scenario,
                        baseline_summary=baseline_summary,
                    )
                )
                aggregates.setdefault(settings.label, {}).setdefault(scenario.summary.scenario_name, []).append(
                    {
                        "max_risk": scenario.summary.max_risk,
                        "mean_risk": scenario.summary.mean_risk,
                        "warning_area_nm2": scenario.summary.warning_area_nm2,
                        "delta_max_risk_vs_baseline": scenario.summary.max_risk - baseline_summary.max_risk,
                        "delta_warning_area_vs_baseline": scenario.summary.warning_area_nm2 - baseline_summary.warning_area_nm2,
                    }
                )

    aggregate_payload: dict[str, object] = {
        "case_count": len(candidates),
        "own_mmsi": own_mmsi,
        "radius_nm": radius_nm,
        "ablations": {},
    }
    for label, scenario_map in aggregates.items():
        aggregate_payload["ablations"][label] = {}
        for scenario_name, values in scenario_map.items():
            count = len(values)
            aggregate_payload["ablations"][label][scenario_name] = {
                "avg_max_risk": sum(item["max_risk"] for item in values) / count if count else 0.0,
                "avg_mean_risk": sum(item["mean_risk"] for item in values) / count if count else 0.0,
                "avg_warning_area_nm2": sum(item["warning_area_nm2"] for item in values) / count if count else 0.0,
                "avg_delta_max_risk_vs_baseline": sum(item["delta_max_risk_vs_baseline"] for item in values) / count if count else 0.0,
                "avg_delta_warning_area_vs_baseline": sum(item["delta_warning_area_vs_baseline"] for item in values) / count if count else 0.0,
            }
    return experiment_rows, aggregate_payload


def run_ablation_experiment_from_csv(
    input_path: str | Path,
    own_mmsi: str,
    config_path: str | Path,
    radius_nm: float,
    ablation_names: list[str],
    top_n: int = 5,
    min_targets: int = 1,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    rows = load_curated_csv_rows(input_path)
    config = load_config(config_path)
    return run_ablation_experiment(
        rows=rows,
        own_mmsi=own_mmsi,
        config=config,
        radius_nm=radius_nm,
        ablation_names=ablation_names,
        top_n=top_n,
        min_targets=min_targets,
    )


def save_ablation_outputs(prefix: str | Path, rows: list[dict[str, str]], aggregate: dict[str, object]) -> tuple[Path, Path]:
    prefix_path = Path(prefix)
    prefix_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = prefix_path.with_name(prefix_path.name + "_cases.csv")
    json_path = prefix_path.with_name(prefix_path.name + "_aggregate.json")
    fieldnames = [
        "timestamp",
        "ablation_label",
        "scenario_name",
        "speed_multiplier",
        "max_risk",
        "mean_risk",
        "warning_area_nm2",
        "caution_area_nm2",
        "dominant_sector",
        "target_count",
        "delta_max_risk_vs_baseline",
        "delta_warning_area_vs_baseline",
        "warning_area_ratio_vs_baseline",
        "top_vessel_mmsi",
        "top_vessel_score",
        "top_vessel_encounter",
        "top_vessel_factors",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    return csv_path, json_path
