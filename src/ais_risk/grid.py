from __future__ import annotations

import math

from .geo import bearing_from_vector_deg, m2_to_nm2, nm_to_m, signed_angle_diff_deg, velocity_vector_ms
from .models import AblationSettings, GridCellRisk, PairwiseRisk, ProjectConfig, ScenarioResult, ScenarioSummary, SnapshotInput, VesselState
from .relative_motion import compute_relative_kinematics
from .risk_scoring import compute_pairwise_risk
from .scenario import apply_speed_multiplier


def build_grid(config: ProjectConfig) -> list[tuple[float, float]]:
    radius_m = nm_to_m(config.grid.radius_nm)
    step = config.grid.cell_size_m
    half_step = step / 2.0
    start = -radius_m + half_step
    grid: list[tuple[float, float]] = []
    y = start
    while y <= radius_m:
        x = start
        while x <= radius_m:
            if math.hypot(x, y) <= radius_m:
                grid.append((x, y))
            x += step
        y += step
    return grid


def risk_label(value: float, config: ProjectConfig) -> str:
    if value >= config.thresholds.warning:
        return "danger"
    if value >= config.thresholds.safe:
        return "caution"
    return "safe"


def local_density_count(own_ship: VesselState, targets: tuple[VesselState, ...], radius_nm: float) -> int:
    radius_m = nm_to_m(radius_nm)
    count = 0
    for target in targets:
        kin = compute_relative_kinematics(own_ship, target)
        if math.hypot(kin.dx_m, kin.dy_m) <= radius_m:
            count += 1
    return count


def scenario_sector_name(own_heading_deg: float, x_m: float, y_m: float) -> str:
    bearing = bearing_from_vector_deg(x_m, y_m)
    relative = signed_angle_diff_deg(bearing, own_heading_deg)
    if -22.5 <= relative < 22.5:
        return "ahead"
    if 22.5 <= relative < 67.5:
        return "forward_starboard"
    if 67.5 <= relative < 112.5:
        return "starboard"
    if 112.5 <= relative < 157.5:
        return "aft_starboard"
    if relative >= 157.5 or relative < -157.5:
        return "astern"
    if -157.5 <= relative < -112.5:
        return "aft_port"
    if -112.5 <= relative < -67.5:
        return "port"
    return "forward_port"


def _predicted_relative_positions(
    own_ship: VesselState,
    target: VesselState,
    config: ProjectConfig,
    use_time_decay: bool = True,
) -> list[tuple[float, float, float]]:
    kin = compute_relative_kinematics(own_ship, target)
    own_vx, own_vy = velocity_vector_ms(own_ship.sog, own_ship.cog)
    target_vx, target_vy = velocity_vector_ms(target.sog, target.cog)
    rel_vx = target_vx - own_vx
    rel_vy = target_vy - own_vy
    horizon_seconds = config.horizon.minutes * 60
    positions: list[tuple[float, float, float]] = []
    for elapsed in range(0, horizon_seconds + config.horizon.time_step_seconds, config.horizon.time_step_seconds):
        time_weight = 1.0 if not use_time_decay else max(0.0, 1.0 - (elapsed / horizon_seconds))
        positions.append((kin.dx_m + (rel_vx * elapsed), kin.dy_m + (rel_vy * elapsed), time_weight))
    return positions


def compute_scenario_grid(
    snapshot: SnapshotInput,
    scenario_name: str,
    speed_multiplier: float,
    config: ProjectConfig,
    ablation: AblationSettings | None = None,
) -> ScenarioResult:
    ablation_settings = AblationSettings() if ablation is None else ablation
    own_ship = apply_speed_multiplier(snapshot.own_ship, speed_multiplier)
    density_count = local_density_count(own_ship, snapshot.targets, config.thresholds.density_radius_nm)
    pairwise_risks: list[PairwiseRisk] = []
    for target in snapshot.targets:
        kinematics = compute_relative_kinematics(own_ship, target)
        pairwise_risks.append(
            compute_pairwise_risk(
                target.mmsi,
                kinematics,
                density_count,
                config,
                disabled_factors=set(ablation_settings.disabled_factors),
            )
        )

    cells = build_grid(config)
    risk_values = [0.0] * len(cells)
    sigma_sq = config.grid.kernel_sigma_m * config.grid.kernel_sigma_m
    support_radius_sq = (config.grid.kernel_sigma_m * 3.0) ** 2
    nearest_radius_sq = (config.grid.cell_size_m * 0.55) ** 2

    for target, pairwise in zip(snapshot.targets, pairwise_risks, strict=True):
        for px_m, py_m, time_weight in _predicted_relative_positions(
            own_ship,
            target,
            config,
            use_time_decay=ablation_settings.use_time_decay,
        ):
            base_risk = pairwise.score * time_weight
            if base_risk <= 0.0:
                continue
            for index, (cx_m, cy_m) in enumerate(cells):
                dx = cx_m - px_m
                dy = cy_m - py_m
                dist_sq = dx * dx + dy * dy
                if ablation_settings.use_spatial_kernel:
                    if dist_sq > support_radius_sq:
                        continue
                    candidate = base_risk * math.exp(-(dist_sq / (2.0 * sigma_sq)))
                else:
                    if dist_sq > nearest_radius_sq:
                        continue
                    candidate = base_risk
                if candidate > risk_values[index]:
                    risk_values[index] = candidate

    cell_area_nm2 = m2_to_nm2(config.grid.cell_size_m * config.grid.cell_size_m)
    warning_cells = 0
    caution_cells = 0
    sector_totals: dict[str, list[float]] = {}
    grid_cells: list[GridCellRisk] = []
    for (x_m, y_m), risk_value in zip(cells, risk_values, strict=True):
        label = risk_label(risk_value, config)
        if risk_value >= config.thresholds.warning:
            warning_cells += 1
        if risk_value >= config.thresholds.safe:
            caution_cells += 1
        sector = scenario_sector_name(own_ship.heading_or_cog, x_m, y_m)
        sector_totals.setdefault(sector, []).append(risk_value)
        grid_cells.append(GridCellRisk(x_m=x_m, y_m=y_m, risk=risk_value, label=label))

    dominant_sector = max(
        sector_totals.items(),
        key=lambda item: (sum(item[1]) / len(item[1])) if item[1] else -1.0,
    )[0]
    top_vessels = tuple(sorted(pairwise_risks, key=lambda item: item.score, reverse=True)[:5])
    summary = ScenarioSummary(
        scenario_name=scenario_name,
        speed_multiplier=speed_multiplier,
        max_risk=max(risk_values) if risk_values else 0.0,
        mean_risk=(sum(risk_values) / len(risk_values)) if risk_values else 0.0,
        warning_area_nm2=warning_cells * cell_area_nm2,
        caution_area_nm2=caution_cells * cell_area_nm2,
        dominant_sector=dominant_sector,
        target_count=len(snapshot.targets),
    )
    return ScenarioResult(summary=summary, top_vessels=top_vessels, cells=tuple(grid_cells))
