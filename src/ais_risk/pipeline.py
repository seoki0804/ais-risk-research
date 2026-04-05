from __future__ import annotations

from .grid import compute_scenario_grid
from .models import AblationSettings, ProjectConfig, SnapshotInput, SnapshotResult

DISCLAIMER = (
    "This output is an AIS-only, constant-velocity proxy for navigational risk awareness "
    "and decision support. It is not an autonomous control command or a safety guarantee."
)


def run_snapshot(
    snapshot: SnapshotInput,
    config: ProjectConfig,
    ablation: AblationSettings | None = None,
) -> SnapshotResult:
    ablation_settings = AblationSettings() if ablation is None else ablation
    scenarios = tuple(
        compute_scenario_grid(
            snapshot,
            scenario_name=name,
            speed_multiplier=multiplier,
            config=config,
            ablation=ablation_settings,
        )
        for name, multiplier in config.scenarios
    )
    metadata = {
        "grid_radius_nm": f"{config.grid.radius_nm}",
        "cell_size_m": f"{config.grid.cell_size_m}",
        "horizon_minutes": f"{config.horizon.minutes}",
        "ablation_label": ablation_settings.label,
    }
    return SnapshotResult(
        project_name=config.project_name,
        timestamp=snapshot.timestamp,
        disclaimer=DISCLAIMER,
        scenarios=scenarios,
        metadata=metadata,
    )
