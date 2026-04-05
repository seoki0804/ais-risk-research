from __future__ import annotations

import math

from .models import PairwiseRisk, ProjectConfig, RelativeKinematics


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def distance_factor(distance_nm: float, scale_nm: float = 1.0) -> float:
    return clamp01(math.exp(-distance_nm / scale_nm))


def dcpa_factor(dcpa_nm: float, scale_nm: float = 1.0) -> float:
    return clamp01(1.0 - (dcpa_nm / scale_nm))


def tcpa_factor(tcpa_min: float, horizon_min: float) -> float:
    if tcpa_min <= 0.0 or tcpa_min > horizon_min:
        return 0.0
    return clamp01(1.0 - (tcpa_min / horizon_min))


def bearing_factor(relative_bearing_deg_value: float) -> float:
    beta = abs(relative_bearing_deg_value)
    if beta <= 22.5:
        return 1.0
    if beta <= 90.0:
        return 0.8
    if beta <= 135.0:
        return 0.5
    return 0.3


def relspeed_factor(relative_speed_knots: float, reference_knots: float = 20.0) -> float:
    return clamp01(relative_speed_knots / reference_knots)


def encounter_factor(encounter_type: str) -> float:
    mapping = {
        "head_on": 1.0,
        "crossing": 0.85,
        "overtaking": 0.70,
        "diverging": 0.20,
    }
    return mapping.get(encounter_type, 0.20)


def density_factor(local_target_count: int, reference_count: float) -> float:
    if reference_count <= 0:
        return 0.0
    return clamp01(local_target_count / reference_count)


def effective_component_weights(config: ProjectConfig, disabled_factors: set[str] | None = None) -> dict[str, float]:
    disabled = disabled_factors or set()
    weights = {
        "distance": 0.0 if "distance" in disabled else config.weights.distance,
        "dcpa": 0.0 if "dcpa" in disabled else config.weights.dcpa,
        "tcpa": 0.0 if "tcpa" in disabled else config.weights.tcpa,
        "bearing": 0.0 if "bearing" in disabled else config.weights.bearing,
        "relspeed": 0.0 if "relspeed" in disabled else config.weights.relspeed,
        "encounter": 0.0 if "encounter" in disabled else config.weights.encounter,
        "density": 0.0 if "density" in disabled else config.weights.density,
    }
    total = sum(weights.values())
    if total <= 0.0:
        return {name: 0.0 for name in weights}
    return {name: (value / total) for name, value in weights.items()}


def compute_pairwise_risk(
    mmsi: str,
    kinematics: RelativeKinematics,
    local_target_count: int,
    config: ProjectConfig,
    disabled_factors: set[str] | None = None,
) -> PairwiseRisk:
    weights = effective_component_weights(config, disabled_factors=disabled_factors)
    raw_components = {
        "distance": distance_factor(kinematics.distance_nm),
        "dcpa": dcpa_factor(kinematics.dcpa_nm),
        "tcpa": tcpa_factor(kinematics.tcpa_min, config.horizon.minutes),
        "bearing": bearing_factor(kinematics.relative_bearing_deg),
        "relspeed": relspeed_factor(kinematics.relative_speed_knots),
        "encounter": encounter_factor(kinematics.encounter_type),
        "density": density_factor(local_target_count, config.thresholds.density_reference_count),
    }
    components = {
        "distance": raw_components["distance"] * weights["distance"],
        "dcpa": raw_components["dcpa"] * weights["dcpa"],
        "tcpa": raw_components["tcpa"] * weights["tcpa"],
        "bearing": raw_components["bearing"] * weights["bearing"],
        "relspeed": raw_components["relspeed"] * weights["relspeed"],
        "encounter": raw_components["encounter"] * weights["encounter"],
        "density": raw_components["density"] * weights["density"],
    }
    score = clamp01(sum(components.values()))
    top_factors = tuple(
        name
        for name, _ in sorted(components.items(), key=lambda item: item[1], reverse=True)[:3]
    )
    return PairwiseRisk(
        mmsi=mmsi,
        score=score,
        components=components,
        encounter_type=kinematics.encounter_type,
        tcpa_min=kinematics.tcpa_min,
        dcpa_nm=kinematics.dcpa_nm,
        distance_nm=kinematics.distance_nm,
        relative_bearing_deg=kinematics.relative_bearing_deg,
        top_factors=top_factors,
    )
