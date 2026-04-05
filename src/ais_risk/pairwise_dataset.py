from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from .csv_tools import format_timestamp, load_curated_csv_rows, parse_timestamp
from .geo import latlon_to_local_xy_m, m_to_nm, vector_norm
from .models import ProjectConfig, VesselState
from .relative_motion import compute_relative_kinematics
from .risk_scoring import compute_pairwise_risk

PAIRWISE_DATASET_COLUMNS = [
    "timestamp",
    "own_mmsi",
    "target_mmsi",
    "own_segment_id",
    "target_segment_id",
    "own_vessel_type",
    "target_vessel_type",
    "own_is_interpolated",
    "target_is_interpolated",
    "local_target_count",
    "distance_nm",
    "dcpa_nm",
    "tcpa_min",
    "relative_speed_knots",
    "relative_bearing_deg",
    "bearing_abs_deg",
    "course_difference_deg",
    "encounter_type",
    "rule_score",
    "rule_component_distance",
    "rule_component_dcpa",
    "rule_component_tcpa",
    "rule_component_bearing",
    "rule_component_relspeed",
    "rule_component_encounter",
    "rule_component_density",
    "future_min_distance_nm",
    "future_time_to_min_min",
    "future_points_used",
    "label_future_conflict",
]


def _track_row_to_vessel(row: dict[str, str]) -> VesselState:
    return VesselState(
        mmsi=row["mmsi"],
        lat=float(row["lat"]),
        lon=float(row["lon"]),
        sog=float(row["sog"]),
        cog=float(row["cog"]),
        heading=float(row["heading"]) if row.get("heading") else None,
        vessel_type=row.get("vessel_type") or None,
    )


def _load_candidate_mmsis(path: str | Path, top_n: int | None = None) -> list[str]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
    if top_n is not None:
        rows = rows[:top_n]
    return [str(row["mmsi"]) for row in rows if row.get("mmsi")]


def _compute_future_min_distance(
    series_index: dict[tuple[str, str], dict[object, dict[str, str]]],
    own_row: dict[str, str],
    target_row: dict[str, str],
    current_time,
    horizon_minutes: int,
    min_future_points: int,
) -> tuple[float, float, int] | None:
    horizon_end = current_time + timedelta(minutes=horizon_minutes)
    own_series = series_index.get((own_row["mmsi"], own_row["segment_id"]), {})
    target_series = series_index.get((target_row["mmsi"], target_row["segment_id"]), {})
    shared_times = sorted(set(own_series.keys()) & set(target_series.keys()))
    future_times = [timestamp for timestamp in shared_times if current_time < timestamp <= horizon_end]
    if len(future_times) < min_future_points:
        return None

    min_distance_nm = float("inf")
    time_to_min_min = 0.0
    for timestamp in future_times:
        own_future = own_series[timestamp]
        target_future = target_series[timestamp]
        dx_m, dy_m = latlon_to_local_xy_m(
            float(own_future["lat"]),
            float(own_future["lon"]),
            float(target_future["lat"]),
            float(target_future["lon"]),
        )
        distance_nm = m_to_nm(vector_norm(dx_m, dy_m))
        if distance_nm < min_distance_nm:
            min_distance_nm = distance_nm
            time_to_min_min = (timestamp - current_time).total_seconds() / 60.0

    return min_distance_nm, time_to_min_min, len(future_times)


def extract_pairwise_learning_rows(
    rows: list[dict[str, str]],
    config: ProjectConfig,
    own_mmsis: set[str] | None = None,
    radius_nm: float | None = None,
    label_distance_nm: float = 0.5,
    sample_every_nth_timestamp: int = 1,
    min_future_points: int = 2,
    min_targets: int = 1,
    max_timestamps_per_ship: int | None = None,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    effective_radius_nm = float(config.grid.radius_nm) if radius_nm is None else float(radius_nm)
    radius_sq_nm = effective_radius_nm * effective_radius_nm
    horizon_minutes = int(config.horizon.minutes)

    normalized_rows: list[dict[str, object]] = []
    rows_by_timestamp: dict[str, list[dict[str, object]]] = defaultdict(list)
    series_index: dict[tuple[str, str], dict[object, dict[str, str]]] = defaultdict(dict)
    own_timestamp_count: dict[str, int] = defaultdict(int)

    for row in rows:
        parsed_time = parse_timestamp(row["timestamp"])
        enriched = dict(row)
        enriched["_parsed_time"] = parsed_time
        normalized_rows.append(enriched)
        rows_by_timestamp[row["timestamp"]].append(enriched)
        segment_id = str(row.get("segment_id") or "")
        if segment_id:
            series_index[(row["mmsi"], segment_id)][parsed_time] = row

    ordered_timestamps = sorted(rows_by_timestamp.keys())
    learning_rows: list[dict[str, str]] = []
    skipped_for_future = 0
    skipped_for_target_count = 0

    for timestamp_index, timestamp in enumerate(ordered_timestamps):
        if sample_every_nth_timestamp > 1 and timestamp_index % sample_every_nth_timestamp != 0:
            continue
        current_rows = sorted(rows_by_timestamp[timestamp], key=lambda item: (str(item["mmsi"]), str(item.get("segment_id", ""))))
        for own_row in current_rows:
            own_mmsi = str(own_row["mmsi"])
            if own_mmsis is not None and own_mmsi not in own_mmsis:
                continue
            if max_timestamps_per_ship is not None and own_timestamp_count[own_mmsi] >= max_timestamps_per_ship:
                continue

            own_vessel = _track_row_to_vessel(own_row)
            nearby_targets: list[dict[str, object]] = []
            for target_row in current_rows:
                if str(target_row["mmsi"]) == own_mmsi:
                    continue
                target_vessel = _track_row_to_vessel(target_row)
                dx_m, dy_m = latlon_to_local_xy_m(own_vessel.lat, own_vessel.lon, target_vessel.lat, target_vessel.lon)
                distance_nm = m_to_nm(vector_norm(dx_m, dy_m))
                if distance_nm * distance_nm <= radius_sq_nm:
                    nearby_targets.append(target_row)

            if len(nearby_targets) < min_targets:
                skipped_for_target_count += 1
                continue

            own_timestamp_count[own_mmsi] += 1
            local_target_count = len(nearby_targets)
            for target_row in nearby_targets:
                target_vessel = _track_row_to_vessel(target_row)
                future = _compute_future_min_distance(
                    series_index=series_index,
                    own_row=own_row,
                    target_row=target_row,
                    current_time=own_row["_parsed_time"],
                    horizon_minutes=horizon_minutes,
                    min_future_points=min_future_points,
                )
                if future is None:
                    skipped_for_future += 1
                    continue

                future_min_distance_nm, future_time_to_min_min, future_points_used = future
                kinematics = compute_relative_kinematics(own_vessel, target_vessel)
                pairwise_risk = compute_pairwise_risk(
                    mmsi=target_vessel.mmsi,
                    kinematics=kinematics,
                    local_target_count=local_target_count,
                    config=config,
                )
                learning_rows.append(
                    {
                        "timestamp": format_timestamp(own_row["_parsed_time"]),
                        "own_mmsi": own_mmsi,
                        "target_mmsi": str(target_row["mmsi"]),
                        "own_segment_id": str(own_row.get("segment_id") or ""),
                        "target_segment_id": str(target_row.get("segment_id") or ""),
                        "own_vessel_type": str(own_row.get("vessel_type") or ""),
                        "target_vessel_type": str(target_row.get("vessel_type") or ""),
                        "own_is_interpolated": str(own_row.get("is_interpolated") or "0"),
                        "target_is_interpolated": str(target_row.get("is_interpolated") or "0"),
                        "local_target_count": str(local_target_count),
                        "distance_nm": f"{kinematics.distance_nm:.6f}",
                        "dcpa_nm": f"{kinematics.dcpa_nm:.6f}",
                        "tcpa_min": f"{kinematics.tcpa_min:.6f}",
                        "relative_speed_knots": f"{kinematics.relative_speed_knots:.6f}",
                        "relative_bearing_deg": f"{kinematics.relative_bearing_deg:.6f}",
                        "bearing_abs_deg": f"{abs(kinematics.relative_bearing_deg):.6f}",
                        "course_difference_deg": f"{kinematics.course_difference_deg:.6f}",
                        "encounter_type": kinematics.encounter_type,
                        "rule_score": f"{pairwise_risk.score:.6f}",
                        "rule_component_distance": f"{pairwise_risk.components['distance']:.6f}",
                        "rule_component_dcpa": f"{pairwise_risk.components['dcpa']:.6f}",
                        "rule_component_tcpa": f"{pairwise_risk.components['tcpa']:.6f}",
                        "rule_component_bearing": f"{pairwise_risk.components['bearing']:.6f}",
                        "rule_component_relspeed": f"{pairwise_risk.components['relspeed']:.6f}",
                        "rule_component_encounter": f"{pairwise_risk.components['encounter']:.6f}",
                        "rule_component_density": f"{pairwise_risk.components['density']:.6f}",
                        "future_min_distance_nm": f"{future_min_distance_nm:.6f}",
                        "future_time_to_min_min": f"{future_time_to_min_min:.6f}",
                        "future_points_used": str(future_points_used),
                        "label_future_conflict": "1" if future_min_distance_nm <= label_distance_nm else "0",
                    }
                )

    positive_rows = sum(1 for row in learning_rows if row["label_future_conflict"] == "1")
    future_min_distances = [float(row["future_min_distance_nm"]) for row in learning_rows]
    future_distance_summary = {}
    if future_min_distances:
        ordered = sorted(future_min_distances)
        middle = len(ordered) // 2
        median = ordered[middle] if len(ordered) % 2 == 1 else (ordered[middle - 1] + ordered[middle]) / 2.0
        future_distance_summary = {
            "min_nm": min(ordered),
            "median_nm": median,
            "max_nm": max(ordered),
        }
    stats = {
        "row_count": len(learning_rows),
        "positive_rows": positive_rows,
        "negative_rows": len(learning_rows) - positive_rows,
        "positive_rate": (positive_rows / len(learning_rows)) if learning_rows else 0.0,
        "own_ship_count": len({row["own_mmsi"] for row in learning_rows}),
        "target_ship_count": len({row["target_mmsi"] for row in learning_rows}),
        "timestamp_count": len({row["timestamp"] for row in learning_rows}),
        "label_distance_nm": float(label_distance_nm),
        "radius_nm": effective_radius_nm,
        "horizon_minutes": horizon_minutes,
        "skipped_for_future": skipped_for_future,
        "skipped_for_target_count": skipped_for_target_count,
        "selected_own_mmsis": sorted(own_mmsis) if own_mmsis is not None else "all",
        "future_min_distance_summary": future_distance_summary,
    }
    return learning_rows, stats


def save_pairwise_learning_dataset(
    output_path: str | Path,
    rows: list[dict[str, str]],
) -> str:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAIRWISE_DATASET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return str(destination)


def save_pairwise_learning_stats(
    output_path: str | Path,
    stats: dict[str, object],
) -> str:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return str(destination)


def build_pairwise_learning_dataset_from_csv(
    input_path: str | Path,
    output_path: str | Path,
    config: ProjectConfig,
    own_mmsis: set[str] | None = None,
    own_candidates_path: str | Path | None = None,
    top_n_candidates: int | None = None,
    radius_nm: float | None = None,
    label_distance_nm: float = 0.5,
    sample_every_nth_timestamp: int = 1,
    min_future_points: int = 2,
    min_targets: int = 1,
    max_timestamps_per_ship: int | None = None,
    stats_output_path: str | Path | None = None,
) -> dict[str, object]:
    rows = load_curated_csv_rows(input_path)
    selected_own_mmsis = set(own_mmsis or set())
    if own_candidates_path:
        selected_own_mmsis.update(_load_candidate_mmsis(own_candidates_path, top_n=top_n_candidates))
    learning_rows, stats = extract_pairwise_learning_rows(
        rows=rows,
        config=config,
        own_mmsis=selected_own_mmsis or None,
        radius_nm=radius_nm,
        label_distance_nm=label_distance_nm,
        sample_every_nth_timestamp=sample_every_nth_timestamp,
        min_future_points=min_future_points,
        min_targets=min_targets,
        max_timestamps_per_ship=max_timestamps_per_ship,
    )
    dataset_path = save_pairwise_learning_dataset(output_path, learning_rows)
    payload = {
        "dataset_path": dataset_path,
        **stats,
    }
    if stats_output_path is not None:
        payload["stats_path"] = save_pairwise_learning_stats(stats_output_path, payload)
    return payload
