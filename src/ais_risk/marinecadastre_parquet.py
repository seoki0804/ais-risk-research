from __future__ import annotations

import csv
import json
import struct
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

import pyarrow.parquet as pq

from .csv_tools import parse_timestamp
from .vessel_types import normalize_vessel_type

RAW_FIELDNAMES = (
    "MMSI",
    "BaseDateTime",
    "LAT",
    "LON",
    "SOG",
    "COG",
    "Heading",
    "VesselType",
)

PARQUET_COLUMNS = (
    "mmsi",
    "base_date_time",
    "sog",
    "cog",
    "heading",
    "vessel_type",
    "geometry",
)


def _is_http_source(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _open_source(path_or_url: str) -> tuple[BinaryIO, BinaryIO | None]:
    if _is_http_source(path_or_url):
        import fsspec

        handle = fsspec.filesystem("http").open(path_or_url, "rb")
        return handle, handle
    handle = Path(path_or_url).open("rb")
    return handle, handle


def decode_wkb_point(value: bytes | bytearray | memoryview | None) -> tuple[float, float] | None:
    if value is None:
        return None
    blob = bytes(value)
    if len(blob) < 21:
        return None
    byte_order = blob[0]
    if byte_order == 1:
        fmt = "<"
    elif byte_order == 0:
        fmt = ">"
    else:
        return None
    raw_type = struct.unpack(f"{fmt}I", blob[1:5])[0]
    has_srid = bool(raw_type & 0x20000000)
    geometry_type = raw_type & 0x0FFFFFFF
    if geometry_type not in {1, 1001, 2001, 3001}:
        return None
    offset = 5
    if has_srid:
        if len(blob) < 25:
            return None
        offset += 4
    if len(blob) < offset + 16:
        return None
    lon, lat = struct.unpack(f"{fmt}dd", blob[offset : offset + 16])
    return float(lat), float(lon)


def _format_timestamp(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _normalize_heading(value: object) -> str:
    if value is None:
        return ""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""
    if 0.0 <= numeric < 360.0:
        return f"{numeric:.6f}"
    return ""


def _normalize_float(value: object) -> str | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return f"{numeric:.6f}"


def convert_marinecadastre_parquet_to_raw_csv(
    input_path_or_url: str,
    output_path: str | Path,
    *,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    allowed_vessel_types: set[str] | None = None,
    max_row_groups: int | None = None,
    limit_rows: int | None = None,
    stats_output_path: str | Path | None = None,
) -> dict[str, object]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    start_dt = parse_timestamp(start_time) if start_time else None
    end_dt = parse_timestamp(end_time) if end_time else None
    normalized_types = {normalize_vessel_type(item) for item in allowed_vessel_types} if allowed_vessel_types else None

    stats = {
        "input_path_or_url": input_path_or_url,
        "output_path": str(output),
        "row_groups_total": 0,
        "row_groups_scanned": 0,
        "rows_scanned": 0,
        "rows_written": 0,
        "invalid_geometry_rows": 0,
        "invalid_timestamp_rows": 0,
        "filtered_by_bounds": 0,
        "filtered_by_time": 0,
        "filtered_by_type": 0,
        "limit_rows": limit_rows or 0,
        "max_row_groups": max_row_groups or 0,
        "unique_vessels_written": 0,
    }
    seen_vessels: set[str] = set()

    source_handle, closable = _open_source(input_path_or_url)
    try:
        parquet_file = pq.ParquetFile(source_handle)
        stats["row_groups_total"] = parquet_file.num_row_groups
        max_groups = parquet_file.num_row_groups if max_row_groups is None else min(max_row_groups, parquet_file.num_row_groups)
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=RAW_FIELDNAMES)
            writer.writeheader()
            for row_group_index in range(max_groups):
                table = parquet_file.read_row_group(row_group_index, columns=list(PARQUET_COLUMNS))
                payload = table.to_pydict()
                row_count = len(payload["mmsi"])
                stats["row_groups_scanned"] = row_group_index + 1
                for index in range(row_count):
                    stats["rows_scanned"] += 1
                    point = decode_wkb_point(payload["geometry"][index])
                    if point is None:
                        stats["invalid_geometry_rows"] += 1
                        continue
                    lat_value, lon_value = point
                    if min_lat is not None and lat_value < min_lat:
                        stats["filtered_by_bounds"] += 1
                        continue
                    if max_lat is not None and lat_value > max_lat:
                        stats["filtered_by_bounds"] += 1
                        continue
                    if min_lon is not None and lon_value < min_lon:
                        stats["filtered_by_bounds"] += 1
                        continue
                    if max_lon is not None and lon_value > max_lon:
                        stats["filtered_by_bounds"] += 1
                        continue

                    timestamp_text = _format_timestamp(payload["base_date_time"][index])
                    if timestamp_text is None:
                        stats["invalid_timestamp_rows"] += 1
                        continue
                    timestamp_value = parse_timestamp(timestamp_text)
                    if start_dt is not None and timestamp_value < start_dt:
                        stats["filtered_by_time"] += 1
                        continue
                    if end_dt is not None and timestamp_value > end_dt:
                        stats["filtered_by_time"] += 1
                        continue

                    vessel_type = normalize_vessel_type(str(payload["vessel_type"][index] or ""))
                    if normalized_types is not None and vessel_type not in normalized_types:
                        stats["filtered_by_type"] += 1
                        continue

                    sog_text = _normalize_float(payload["sog"][index])
                    cog_text = _normalize_float(payload["cog"][index])
                    if sog_text is None or cog_text is None:
                        continue

                    mmsi_value = str(payload["mmsi"][index]).strip()
                    writer.writerow(
                        {
                            "MMSI": mmsi_value,
                            "BaseDateTime": timestamp_text,
                            "LAT": f"{lat_value:.6f}",
                            "LON": f"{lon_value:.6f}",
                            "SOG": sog_text,
                            "COG": cog_text,
                            "Heading": _normalize_heading(payload["heading"][index]),
                            "VesselType": vessel_type,
                        }
                    )
                    seen_vessels.add(mmsi_value)
                    stats["rows_written"] += 1
                    if limit_rows is not None and stats["rows_written"] >= limit_rows:
                        break
                if limit_rows is not None and stats["rows_written"] >= limit_rows:
                    break
        stats["unique_vessels_written"] = len(seen_vessels)
        if stats_output_path is not None:
            stats_path = Path(stats_output_path)
            stats_path.parent.mkdir(parents=True, exist_ok=True)
            stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    finally:
        if closable is not None:
            closable.close()
    return stats
