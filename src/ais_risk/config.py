from __future__ import annotations

import tomllib
from pathlib import Path

from .models import GridConfig, HorizonConfig, ProjectConfig, RiskWeights, ThresholdConfig


def load_config(path: str | Path) -> ProjectConfig:
    with Path(path).open("rb") as handle:
        raw = tomllib.load(handle)

    scenario_order = raw["scenarios"]["order"]
    scenario_values = raw["scenarios"]["values"]
    scenarios = tuple((name, float(scenario_values[name])) for name in scenario_order)

    return ProjectConfig(
        project_name=raw["project"]["name"],
        grid=GridConfig(
            radius_nm=float(raw["grid"]["radius_nm"]),
            cell_size_m=float(raw["grid"]["cell_size_m"]),
            kernel_sigma_m=float(raw["grid"]["kernel_sigma_m"]),
        ),
        horizon=HorizonConfig(
            minutes=int(raw["horizon"]["minutes"]),
            time_step_seconds=int(raw["horizon"]["time_step_seconds"]),
        ),
        thresholds=ThresholdConfig(
            safe=float(raw["thresholds"]["safe"]),
            warning=float(raw["thresholds"]["warning"]),
            density_radius_nm=float(raw["thresholds"]["density_radius_nm"]),
            density_reference_count=float(raw["thresholds"]["density_reference_count"]),
        ),
        weights=RiskWeights(
            distance=float(raw["weights"]["distance"]),
            dcpa=float(raw["weights"]["dcpa"]),
            tcpa=float(raw["weights"]["tcpa"]),
            bearing=float(raw["weights"]["bearing"]),
            relspeed=float(raw["weights"]["relspeed"]),
            encounter=float(raw["weights"]["encounter"]),
            density=float(raw["weights"]["density"]),
        ),
        scenarios=scenarios,
    )
