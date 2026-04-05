from __future__ import annotations

import csv
from collections import defaultdict
from itertools import groupby
from pathlib import Path

from .case_mining import mine_cases_from_curated_rows
from .config import load_config
from .csv_tools import build_snapshot_from_curated_rows
from .csv_tools import load_curated_csv_rows, parse_timestamp
from .geo import latlon_to_local_xy_m, nm_to_m
from .models import ProjectConfig
from .pipeline import run_snapshot


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0.0:
        return 0.0
    return numerator / denominator


def _normalize(value: float, max_value: float) -> float:
    if max_value <= 0.0:
        return 0.0
    return min(1.0, max(0.0, value / max_value))


def _segment_break_count(vessel_rows: list[dict[str, str]], segment_gap_minutes: float) -> int:
    segment_ids = {row.get("segment_id", "").strip() for row in vessel_rows if row.get("segment_id", "").strip()}
    if segment_ids:
        return max(0, len(segment_ids) - 1)

    segment_gap_seconds = segment_gap_minutes * 60.0
    breaks = 0
    for previous, current in zip(vessel_rows, vessel_rows[1:], strict=False):
        gap_seconds = (parse_timestamp(current["timestamp"]) - parse_timestamp(previous["timestamp"])).total_seconds()
        if gap_seconds > segment_gap_seconds:
            breaks += 1
    return breaks


def _interaction_stats(
    vessel_rows: list[dict[str, str]],
    rows_by_timestamp: dict[str, list[dict[str, str]]],
    radius_m: float,
    min_targets: int,
) -> tuple[int, float, int, float]:
    active_window_count = 0
    total_nearby_targets = 0
    max_nearby_targets = 0
    total_neighbor_proximity = 0.0

    radius_squared = radius_m * radius_m
    for row in vessel_rows:
        nearby_targets = 0
        neighbor_proximity = 0.0
        for other in rows_by_timestamp.get(row["timestamp"], []):
            if other["mmsi"] == row["mmsi"]:
                continue
            dx_m, dy_m = latlon_to_local_xy_m(
                float(row["lat"]),
                float(row["lon"]),
                float(other["lat"]),
                float(other["lon"]),
            )
            distance_squared = (dx_m * dx_m) + (dy_m * dy_m)
            if distance_squared > radius_squared:
                continue
            nearby_targets += 1
            distance_ratio = min(1.0, (distance_squared**0.5) / radius_m) if radius_m > 0.0 else 1.0
            neighbor_proximity += 1.0 - distance_ratio

        if nearby_targets >= min_targets:
            active_window_count += 1
        total_nearby_targets += nearby_targets
        max_nearby_targets = max(max_nearby_targets, nearby_targets)
        total_neighbor_proximity += neighbor_proximity

    row_count = len(vessel_rows)
    average_nearby_targets = _safe_ratio(total_nearby_targets, row_count)
    average_neighbor_proximity = _safe_ratio(total_neighbor_proximity, row_count)
    return active_window_count, average_nearby_targets, max_nearby_targets, average_neighbor_proximity


def _candidate_reason(
    timestamp_count: int,
    active_window_count: int,
    min_targets: int,
    average_nearby_targets: float,
    segment_break_count: int,
) -> str:
    return (
        f"{timestamp_count} windows, "
        f"{active_window_count} windows with >={min_targets} nearby targets, "
        f"avg nearby {average_nearby_targets:.2f}, "
        f"segment breaks {segment_break_count}"
    )


def rank_own_ship_candidates_rows(
    rows: list[dict[str, str]],
    radius_nm: float,
    top_n: int = 10,
    min_targets: int = 1,
    moving_sog_threshold: float = 1.0,
    segment_gap_minutes: float = 10.0,
) -> list[dict[str, object]]:
    if not rows:
        return []

    rows = sorted(rows, key=lambda item: (item["mmsi"], item["timestamp"]))
    rows_by_timestamp: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_timestamp[row["timestamp"]].append(row)

    radius_m = nm_to_m(radius_nm)
    raw_candidates: list[dict[str, object]] = []
    for mmsi, vessel_rows_iter in groupby(rows, key=lambda item: item["mmsi"]):
        vessel_rows = list(vessel_rows_iter)
        timestamp_count = len(vessel_rows)
        if timestamp_count == 0:
            continue

        segment_break_count = _segment_break_count(vessel_rows, segment_gap_minutes=segment_gap_minutes)
        heading_coverage_ratio = _safe_ratio(sum(1 for row in vessel_rows if row.get("heading")), timestamp_count)
        movement_ratio = _safe_ratio(sum(1 for row in vessel_rows if float(row["sog"]) >= moving_sog_threshold), timestamp_count)
        average_sog = sum(float(row["sog"]) for row in vessel_rows) / timestamp_count
        observed_row_count = sum(1 for row in vessel_rows if row.get("is_interpolated") != "1")
        active_window_count, average_nearby_targets, max_nearby_targets, average_neighbor_proximity = _interaction_stats(
            vessel_rows=vessel_rows,
            rows_by_timestamp=rows_by_timestamp,
            radius_m=radius_m,
            min_targets=min_targets,
        )

        raw_candidates.append(
            {
                "mmsi": mmsi,
                "vessel_type": vessel_rows[0].get("vessel_type", "") or "unknown",
                "row_count": timestamp_count,
                "observed_row_count": observed_row_count,
                "first_timestamp": vessel_rows[0]["timestamp"],
                "last_timestamp": vessel_rows[-1]["timestamp"],
                "segment_break_count": segment_break_count,
                "heading_coverage_ratio": heading_coverage_ratio,
                "movement_ratio": movement_ratio,
                "average_sog": average_sog,
                "active_window_count": active_window_count,
                "active_window_ratio": _safe_ratio(active_window_count, timestamp_count),
                "average_nearby_targets": average_nearby_targets,
                "max_nearby_targets": max_nearby_targets,
                "average_neighbor_proximity": average_neighbor_proximity,
            }
        )

    max_row_count = max(candidate["row_count"] for candidate in raw_candidates)
    max_active_window_count = max(candidate["active_window_count"] for candidate in raw_candidates)
    max_average_sog = max(candidate["average_sog"] for candidate in raw_candidates)
    max_average_nearby_targets = max(candidate["average_nearby_targets"] for candidate in raw_candidates)
    max_average_neighbor_proximity = max(candidate["average_neighbor_proximity"] for candidate in raw_candidates)

    ranked: list[dict[str, object]] = []
    for candidate in raw_candidates:
        continuity_score = (
            0.55 * _normalize(float(candidate["row_count"]), float(max_row_count))
            + 0.25 * (1.0 / (1.0 + float(candidate["segment_break_count"])))
            + 0.20 * float(candidate["heading_coverage_ratio"])
        )
        interaction_score = (
            0.45 * float(candidate["active_window_ratio"])
            + 0.25 * _normalize(float(candidate["active_window_count"]), float(max_active_window_count))
            + 0.15 * _normalize(float(candidate["average_nearby_targets"]), float(max_average_nearby_targets))
            + 0.15 * _normalize(float(candidate["average_neighbor_proximity"]), float(max_average_neighbor_proximity))
        )
        mobility_score = (
            0.70 * float(candidate["movement_ratio"])
            + 0.30 * _normalize(float(candidate["average_sog"]), float(max_average_sog))
        )
        candidate_score = (0.40 * continuity_score) + (0.45 * interaction_score) + (0.15 * mobility_score)

        ranked.append(
            {
                **candidate,
                "continuity_score": continuity_score,
                "interaction_score": interaction_score,
                "mobility_score": mobility_score,
                "candidate_score": candidate_score,
                "reason_summary": _candidate_reason(
                    timestamp_count=int(candidate["row_count"]),
                    active_window_count=int(candidate["active_window_count"]),
                    min_targets=min_targets,
                    average_nearby_targets=float(candidate["average_nearby_targets"]),
                    segment_break_count=int(candidate["segment_break_count"]),
                ),
            }
        )

    ranked.sort(
        key=lambda item: (
            float(item["candidate_score"]),
            float(item["interaction_score"]),
            float(item["average_neighbor_proximity"]),
            int(item["active_window_count"]),
            int(item["row_count"]),
        ),
        reverse=True,
    )
    for index, candidate in enumerate(ranked[:top_n], start=1):
        candidate["rank"] = index
    return ranked[:top_n]


def rank_own_ship_candidates_csv(
    input_path: str | Path,
    radius_nm: float,
    top_n: int = 10,
    min_targets: int = 1,
    moving_sog_threshold: float = 1.0,
    segment_gap_minutes: float = 10.0,
) -> list[dict[str, object]]:
    rows = load_curated_csv_rows(input_path)
    return rank_own_ship_candidates_rows(
        rows=rows,
        radius_nm=radius_nm,
        top_n=top_n,
        min_targets=min_targets,
        moving_sog_threshold=moving_sog_threshold,
        segment_gap_minutes=segment_gap_minutes,
    )


def _attach_representative_case(
    rows: list[dict[str, str]],
    config: ProjectConfig,
    radius_nm: float,
    candidate: dict[str, object],
    min_targets: int,
) -> dict[str, object]:
    case_rows = mine_cases_from_curated_rows(
        rows=rows,
        own_mmsi=str(candidate["mmsi"]),
        config=config,
        radius_nm=radius_nm,
        top_n=1,
        min_targets=min_targets,
    )
    if case_rows:
        case = case_rows[0]
        return {
            **candidate,
            "recommended_timestamp": case["timestamp"],
            "recommended_max_risk": float(case["max_risk"]),
            "recommended_target_count": int(case["target_count"]),
            "recommended_warning_area_nm2": float(case["warning_area_nm2"]),
            "recommended_dominant_sector": case["dominant_sector"],
            "recommendation_source": "risk_peak",
        }

    fallback_timestamp = str(candidate["first_timestamp"])
    snapshot = build_snapshot_from_curated_rows(
        rows=rows,
        own_mmsi=str(candidate["mmsi"]),
        timestamp=fallback_timestamp,
        radius_nm=radius_nm,
    )
    result = run_snapshot(snapshot, config)
    current = next(
        (scenario for scenario in result.scenarios if scenario.summary.scenario_name == "current"),
        result.scenarios[0],
    )
    return {
        **candidate,
        "recommended_timestamp": fallback_timestamp,
        "recommended_max_risk": float(current.summary.max_risk),
        "recommended_target_count": int(current.summary.target_count),
        "recommended_warning_area_nm2": float(current.summary.warning_area_nm2),
        "recommended_dominant_sector": current.summary.dominant_sector,
        "recommendation_source": "first_observation_fallback",
    }


def recommend_own_ship_candidates_rows(
    rows: list[dict[str, str]],
    config: ProjectConfig,
    radius_nm: float,
    top_n: int = 10,
    min_targets: int = 1,
    moving_sog_threshold: float = 1.0,
    segment_gap_minutes: float = 10.0,
) -> list[dict[str, object]]:
    ranked = rank_own_ship_candidates_rows(
        rows=rows,
        radius_nm=radius_nm,
        top_n=top_n,
        min_targets=min_targets,
        moving_sog_threshold=moving_sog_threshold,
        segment_gap_minutes=segment_gap_minutes,
    )
    return [
        _attach_representative_case(
            rows=rows,
            config=config,
            radius_nm=radius_nm,
            candidate=candidate,
            min_targets=min_targets,
        )
        for candidate in ranked
    ]


def recommend_own_ship_candidates_csv(
    input_path: str | Path,
    config_path: str | Path,
    radius_nm: float,
    top_n: int = 10,
    min_targets: int = 1,
    moving_sog_threshold: float = 1.0,
    segment_gap_minutes: float = 10.0,
) -> list[dict[str, object]]:
    rows = load_curated_csv_rows(input_path)
    config = load_config(config_path)
    return recommend_own_ship_candidates_rows(
        rows=rows,
        config=config,
        radius_nm=radius_nm,
        top_n=top_n,
        min_targets=min_targets,
        moving_sog_threshold=moving_sog_threshold,
        segment_gap_minutes=segment_gap_minutes,
    )


def save_own_ship_candidates(path: str | Path, rows: list[dict[str, object]]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "mmsi",
        "vessel_type",
        "candidate_score",
        "continuity_score",
        "interaction_score",
        "mobility_score",
        "row_count",
        "observed_row_count",
        "segment_break_count",
        "heading_coverage_ratio",
        "movement_ratio",
        "average_sog",
        "active_window_count",
        "active_window_ratio",
        "average_nearby_targets",
        "max_nearby_targets",
        "average_neighbor_proximity",
        "first_timestamp",
        "last_timestamp",
        "recommended_timestamp",
        "recommended_max_risk",
        "recommended_target_count",
        "recommended_warning_area_nm2",
        "recommended_dominant_sector",
        "recommendation_source",
        "reason_summary",
    ]
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
