from __future__ import annotations

import json
import statistics
from collections import Counter
from itertools import groupby
from pathlib import Path

from .csv_tools import load_curated_csv_rows, parse_timestamp


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * quantile))))
    return float(ordered[index])


def profile_curated_rows(rows: list[dict[str, str]], top_n: int = 10) -> dict[str, object]:
    if not rows:
        return {
            "row_count": 0,
            "unique_vessels": 0,
            "time_range": {"start": None, "end": None},
            "spatial_extent": None,
            "speed_stats": None,
            "heading_coverage_ratio": 0.0,
            "vessel_type_counts": {},
            "top_vessels_by_rows": [],
            "gap_stats_seconds": None,
            "segment_estimate_count_gap_gt_10min": 0,
        }

    timestamps = [parse_timestamp(row["timestamp"]) for row in rows]
    latitudes = [float(row["lat"]) for row in rows]
    longitudes = [float(row["lon"]) for row in rows]
    sog_values = [float(row["sog"]) for row in rows]
    heading_present = sum(1 for row in rows if row.get("heading"))
    vessel_type_counts = Counter((row.get("vessel_type") or "unknown").strip() or "unknown" for row in rows)
    vessel_row_counts = Counter(row["mmsi"] for row in rows)

    gap_seconds: list[float] = []
    segment_breaks = 0
    ordered_rows = sorted(rows, key=lambda item: (item["mmsi"], item["timestamp"]))
    for _, vessel_rows_iter in groupby(ordered_rows, key=lambda item: item["mmsi"]):
        vessel_rows = list(vessel_rows_iter)
        for previous, current in zip(vessel_rows, vessel_rows[1:], strict=False):
            gap = (parse_timestamp(current["timestamp"]) - parse_timestamp(previous["timestamp"])).total_seconds()
            if gap > 0:
                gap_seconds.append(gap)
            if gap > 600.0:
                segment_breaks += 1

    gap_stats = None
    if gap_seconds:
        gap_stats = {
            "min": min(gap_seconds),
            "median": statistics.median(gap_seconds),
            "p90": _percentile(gap_seconds, 0.90),
            "max": max(gap_seconds),
            "count": len(gap_seconds),
        }

    return {
        "row_count": len(rows),
        "unique_vessels": len(vessel_row_counts),
        "time_range": {
            "start": min(timestamps).isoformat().replace("+00:00", "Z"),
            "end": max(timestamps).isoformat().replace("+00:00", "Z"),
        },
        "spatial_extent": {
            "min_lat": min(latitudes),
            "max_lat": max(latitudes),
            "min_lon": min(longitudes),
            "max_lon": max(longitudes),
        },
        "speed_stats": {
            "min_sog": min(sog_values),
            "median_sog": statistics.median(sog_values),
            "max_sog": max(sog_values),
        },
        "heading_coverage_ratio": heading_present / len(rows),
        "vessel_type_counts": dict(vessel_type_counts.most_common()),
        "top_vessels_by_rows": [
            {"mmsi": mmsi, "row_count": count}
            for mmsi, count in vessel_row_counts.most_common(top_n)
        ],
        "gap_stats_seconds": gap_stats,
        "segment_estimate_count_gap_gt_10min": segment_breaks,
    }


def profile_curated_csv(input_path: str | Path, top_n: int = 10) -> dict[str, object]:
    rows = load_curated_csv_rows(input_path)
    return profile_curated_rows(rows, top_n=top_n)


def build_profile_markdown(profile: dict[str, object]) -> str:
    gap_stats = profile["gap_stats_seconds"]
    gap_lines = "- Gap stats: unavailable"
    if gap_stats is not None:
        gap_lines = (
            f"- Gap stats (sec): min `{gap_stats['min']:.1f}`, median `{gap_stats['median']:.1f}`, "
            f"p90 `{gap_stats['p90']:.1f}`, max `{gap_stats['max']:.1f}`"
        )

    top_vessels_rows = "\n".join(
        f"| {item['mmsi']} | {item['row_count']} |" for item in profile["top_vessels_by_rows"]
    ) or "| - | - |"
    vessel_type_rows = "\n".join(
        f"| {name} | {count} |" for name, count in profile["vessel_type_counts"].items()
    ) or "| - | - |"

    markdown = f"""# AIS Dataset Profile

## Overview

- Row count: `{profile['row_count']}`
- Unique vessels: `{profile['unique_vessels']}`
- Time range: `{profile['time_range']['start']}` to `{profile['time_range']['end']}`
- Heading coverage ratio: `{profile['heading_coverage_ratio']:.3f}`
- Estimated segment breaks (gap > 10 min): `{profile['segment_estimate_count_gap_gt_10min']}`

## Spatial Extent

- Latitude: `{profile['spatial_extent']['min_lat']:.6f}` to `{profile['spatial_extent']['max_lat']:.6f}`
- Longitude: `{profile['spatial_extent']['min_lon']:.6f}` to `{profile['spatial_extent']['max_lon']:.6f}`

## Speed Stats

- SOG min/median/max: `{profile['speed_stats']['min_sog']:.2f}` / `{profile['speed_stats']['median_sog']:.2f}` / `{profile['speed_stats']['max_sog']:.2f}`
{gap_lines}

## Vessel Type Counts

| Vessel Type | Count |
|---|---:|
{vessel_type_rows}

## Top Vessels By Row Count

| MMSI | Row Count |
|---|---:|
{top_vessels_rows}
"""
    return markdown


def save_profile_outputs(output_prefix: str | Path, profile: dict[str, object]) -> tuple[Path, Path]:
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.with_name(prefix.name + "_profile.json")
    md_path = prefix.with_name(prefix.name + "_profile.md")
    json_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    md_path.write_text(build_profile_markdown(profile), encoding="utf-8")
    return json_path, md_path
