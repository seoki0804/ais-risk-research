from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VesselState:
    mmsi: str
    lat: float
    lon: float
    sog: float
    cog: float
    heading: float | None = None
    vessel_type: str | None = None

    @property
    def heading_or_cog(self) -> float:
        return self.cog if self.heading is None else self.heading


@dataclass(frozen=True)
class SnapshotInput:
    timestamp: str
    own_ship: VesselState
    targets: tuple[VesselState, ...]


@dataclass(frozen=True)
class RiskWeights:
    distance: float
    dcpa: float
    tcpa: float
    bearing: float
    relspeed: float
    encounter: float
    density: float


@dataclass(frozen=True)
class GridConfig:
    radius_nm: float
    cell_size_m: float
    kernel_sigma_m: float


@dataclass(frozen=True)
class HorizonConfig:
    minutes: int
    time_step_seconds: int


@dataclass(frozen=True)
class ThresholdConfig:
    safe: float
    warning: float
    density_radius_nm: float
    density_reference_count: float


@dataclass(frozen=True)
class ProjectConfig:
    project_name: str
    grid: GridConfig
    horizon: HorizonConfig
    thresholds: ThresholdConfig
    weights: RiskWeights
    scenarios: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class AblationSettings:
    label: str = "baseline"
    disabled_factors: tuple[str, ...] = ()
    use_time_decay: bool = True
    use_spatial_kernel: bool = True


@dataclass(frozen=True)
class RelativeKinematics:
    dx_m: float
    dy_m: float
    distance_nm: float
    relative_bearing_deg: float
    relative_speed_knots: float
    tcpa_min: float
    dcpa_nm: float
    course_difference_deg: float
    encounter_type: str


@dataclass(frozen=True)
class PairwiseRisk:
    mmsi: str
    score: float
    components: dict[str, float]
    encounter_type: str
    tcpa_min: float
    dcpa_nm: float
    distance_nm: float
    relative_bearing_deg: float
    top_factors: tuple[str, ...]


@dataclass(frozen=True)
class GridCellRisk:
    x_m: float
    y_m: float
    risk: float
    label: str


@dataclass(frozen=True)
class ScenarioSummary:
    scenario_name: str
    speed_multiplier: float
    max_risk: float
    mean_risk: float
    warning_area_nm2: float
    caution_area_nm2: float
    dominant_sector: str
    target_count: int


@dataclass(frozen=True)
class ScenarioResult:
    summary: ScenarioSummary
    top_vessels: tuple[PairwiseRisk, ...]
    cells: tuple[GridCellRisk, ...]


@dataclass(frozen=True)
class SnapshotResult:
    project_name: str
    timestamp: str
    disclaimer: str
    scenarios: tuple[ScenarioResult, ...]
    metadata: dict[str, str] = field(default_factory=dict)
