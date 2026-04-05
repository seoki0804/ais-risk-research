from __future__ import annotations

import csv
from datetime import UTC, datetime
from itertools import groupby
from pathlib import Path

from .csv_tools import format_timestamp, load_curated_csv_rows, parse_timestamp

TRACK_COLUMNS = [
    "mmsi",
    "timestamp",
    "lat",
    "lon",
    "sog",
    "cog",
    "heading",
    "vessel_type",
    "segment_id",
    "is_interpolated",
]


def _interpolate_linear(a: float, b: float, alpha: float) -> float:
    return a + ((b - a) * alpha)


def _interpolate_angle_deg(a: float, b: float, alpha: float) -> float:
    diff = (b - a + 180.0) % 360.0 - 180.0
    return (a + (diff * alpha)) % 360.0


def _copy_row(row: dict[str, str], segment_id: str, is_interpolated: bool) -> dict[str, str]:
    return {
        "mmsi": row["mmsi"],
        "timestamp": row["timestamp"],
        "lat": row["lat"],
        "lon": row["lon"],
        "sog": row["sog"],
        "cog": row["cog"],
        "heading": row.get("heading", ""),
        "vessel_type": row.get("vessel_type", ""),
        "segment_id": segment_id,
        "is_interpolated": "1" if is_interpolated else "0",
    }


def _interpolate_row(prev_row: dict[str, str], next_row: dict[str, str], timestamp_offset_seconds: int, segment_id: str) -> dict[str, str]:
    prev_time = parse_timestamp(prev_row["timestamp"])
    next_time = parse_timestamp(next_row["timestamp"])
    total_seconds = int((next_time - prev_time).total_seconds())
    alpha = timestamp_offset_seconds / total_seconds
    interpolated_time = datetime.fromtimestamp(prev_time.timestamp() + timestamp_offset_seconds, tz=UTC)

    heading_value = ""
    if prev_row.get("heading") and next_row.get("heading"):
        heading_value = f"{_interpolate_angle_deg(float(prev_row['heading']), float(next_row['heading']), alpha):.6f}"
    elif prev_row.get("heading"):
        heading_value = prev_row["heading"]
    elif next_row.get("heading"):
        heading_value = next_row["heading"]

    return {
        "mmsi": prev_row["mmsi"],
        "timestamp": format_timestamp(interpolated_time),
        "lat": f"{_interpolate_linear(float(prev_row['lat']), float(next_row['lat']), alpha):.6f}",
        "lon": f"{_interpolate_linear(float(prev_row['lon']), float(next_row['lon']), alpha):.6f}",
        "sog": f"{_interpolate_linear(float(prev_row['sog']), float(next_row['sog']), alpha):.6f}",
        "cog": f"{_interpolate_angle_deg(float(prev_row['cog']), float(next_row['cog']), alpha):.6f}",
        "heading": heading_value,
        "vessel_type": prev_row.get("vessel_type") or next_row.get("vessel_type", ""),
        "segment_id": segment_id,
        "is_interpolated": "1",
    }


def reconstruct_trajectory_rows(
    rows: list[dict[str, str]],
    split_gap_minutes: float = 10.0,
    max_interp_gap_minutes: float = 2.0,
    step_seconds: int = 30,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    split_gap_seconds = split_gap_minutes * 60.0
    max_interp_gap_seconds = max_interp_gap_minutes * 60.0
    output_rows: list[dict[str, str]] = []
    segment_count = 0
    interpolated_rows = 0

    rows = sorted(rows, key=lambda item: (item["mmsi"], item["timestamp"]))
    for mmsi, group_iter in groupby(rows, key=lambda item: item["mmsi"]):
        vessel_rows = list(group_iter)
        if not vessel_rows:
            continue

        segment_index = 1
        segment_id = f"{mmsi}-{segment_index:04d}"
        segment_count += 1
        output_rows.append(_copy_row(vessel_rows[0], segment_id, is_interpolated=False))

        for prev_row, next_row in zip(vessel_rows, vessel_rows[1:], strict=False):
            prev_time = parse_timestamp(prev_row["timestamp"])
            next_time = parse_timestamp(next_row["timestamp"])
            gap_seconds = (next_time - prev_time).total_seconds()
            if gap_seconds <= 0:
                continue
            if gap_seconds > split_gap_seconds:
                segment_index += 1
                segment_id = f"{mmsi}-{segment_index:04d}"
                segment_count += 1
                output_rows.append(_copy_row(next_row, segment_id, is_interpolated=False))
                continue

            if gap_seconds <= max_interp_gap_seconds and gap_seconds > step_seconds:
                for offset in range(step_seconds, int(gap_seconds), step_seconds):
                    output_rows.append(_interpolate_row(prev_row, next_row, offset, segment_id))
                    interpolated_rows += 1

            output_rows.append(_copy_row(next_row, segment_id, is_interpolated=False))

    stats = {
        "input_rows": len(rows),
        "output_rows": len(output_rows),
        "interpolated_rows": interpolated_rows,
        "segment_count": segment_count,
        "unique_vessels": len({row["mmsi"] for row in rows}),
    }
    return output_rows, stats


def reconstruct_trajectory_csv(
    input_path: str | Path,
    output_path: str | Path,
    split_gap_minutes: float = 10.0,
    max_interp_gap_minutes: float = 2.0,
    step_seconds: int = 30,
) -> dict[str, int]:
    rows = load_curated_csv_rows(input_path)
    reconstructed, stats = reconstruct_trajectory_rows(
        rows=rows,
        split_gap_minutes=split_gap_minutes,
        max_interp_gap_minutes=max_interp_gap_minutes,
        step_seconds=step_seconds,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRACK_COLUMNS)
        writer.writeheader()
        writer.writerows(reconstructed)
    return stats
