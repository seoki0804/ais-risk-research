from __future__ import annotations

import csv
import re
from datetime import UTC, datetime
from pathlib import Path

from .geo import latlon_to_local_xy_m, nm_to_m
from .models import SnapshotInput, VesselState
from .vessel_types import normalize_vessel_type

HEADER_ALIASES = {
    "mmsi": ("mmsi", "MMSI", "ship_mmsi", "shipmmsi"),
    "timestamp": (
        "timestamp",
        "Timestamp",
        "BaseDateTime",
        "base_datetime",
        "base date time",
        "time",
        "datetime",
        "date_time_utc",
        "msgtime",
        "record_time",
    ),
    "lat": ("lat", "LAT", "latitude", "Latitude", "LATITUDE", "lat_dd"),
    "lon": ("lon", "LON", "longitude", "Longitude", "LONGITUDE", "lon_dd", "lng"),
    "sog": ("sog", "SOG", "speed_over_ground", "speed over ground", "speedoverground"),
    "cog": ("cog", "COG", "course_over_ground", "course over ground", "courseoverground"),
    "heading": ("heading", "Heading", "HEADING", "true_heading", "true heading", "trueheading"),
    "vessel_type": ("vessel_type", "VesselType", "vesseltype", "ship_type", "ship type", "shiptype"),
}

CANONICAL_COLUMNS = ("mmsi", "timestamp", "lat", "lon", "sog", "cog", "heading", "vessel_type")
REQUIRED_COLUMNS = ("mmsi", "timestamp", "lat", "lon", "sog", "cog")
OPTIONAL_COLUMNS = ("heading", "vessel_type")


def normalize_header_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def _resolve_actual_header(fieldnames: list[str], requested_header: str) -> str | None:
    normalized_requested = normalize_header_name(requested_header)
    for field in fieldnames:
        if field == requested_header or normalize_header_name(field) == normalized_requested:
            return field
    return None


def parse_column_overrides(raw: str | None) -> dict[str, str]:
    if raw is None or raw.strip() == "":
        return {}

    overrides: dict[str, str] = {}
    tokens = [token.strip() for token in re.split(r"[\n,]+", raw) if token.strip()]
    for token in tokens:
        if "=" not in token:
            raise ValueError(f"Invalid column override token: {token}")
        canonical_key, actual_header = token.split("=", 1)
        canonical_key = canonical_key.strip()
        actual_header = actual_header.strip()
        if canonical_key not in CANONICAL_COLUMNS:
            raise ValueError(f"Unsupported canonical column in override: {canonical_key}")
        if actual_header == "":
            raise ValueError(f"Missing source header for override: {canonical_key}")
        overrides[canonical_key] = actual_header
    return overrides


def build_header_lookup(
    fieldnames: list[str] | tuple[str, ...] | None,
    column_overrides: dict[str, str] | None = None,
) -> dict[str, str | None]:
    lookup: dict[str, str | None] = {}
    available_fields = list(fieldnames or [])
    for canonical_key in CANONICAL_COLUMNS:
        matched = None
        if column_overrides and canonical_key in column_overrides:
            matched = _resolve_actual_header(available_fields, column_overrides[canonical_key])
        normalized_aliases = {normalize_header_name(alias) for alias in HEADER_ALIASES[canonical_key]}
        if matched is None:
            for field in available_fields:
                if normalize_header_name(field) in normalized_aliases:
                    matched = field
                    break
        lookup[canonical_key] = matched
    return lookup


def parse_timestamp(value: str) -> datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    candidates = (
        lambda text: datetime.fromisoformat(text),
        lambda text: datetime.strptime(text, "%Y-%m-%d %H:%M:%S"),
        lambda text: datetime.strptime(text, "%Y/%m/%d %H:%M:%S"),
    )
    for parser in candidates:
        try:
            parsed = parser(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except ValueError:
            continue
    raise ValueError(f"Unsupported timestamp format: {value}")


def format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _get_value(row: dict[str, str], canonical_key: str, header_lookup: dict[str, str | None]) -> str | None:
    actual_header = header_lookup.get(canonical_key)
    if actual_header is not None and actual_header in row and row[actual_header] != "":
        return row[actual_header]
    for field, value in row.items():
        if normalize_header_name(field) in {normalize_header_name(alias) for alias in HEADER_ALIASES[canonical_key]} and value != "":
            return value
    return None


def _normalize_row(row: dict[str, str], header_lookup: dict[str, str | None] | None = None) -> dict[str, str] | None:
    try:
        effective_lookup = header_lookup or build_header_lookup(list(row.keys()))
        mmsi = _get_value(row, "mmsi", effective_lookup)
        timestamp = _get_value(row, "timestamp", effective_lookup)
        lat = _get_value(row, "lat", effective_lookup)
        lon = _get_value(row, "lon", effective_lookup)
        sog = _get_value(row, "sog", effective_lookup)
        cog = _get_value(row, "cog", effective_lookup)
        if not all((mmsi, timestamp, lat, lon, sog, cog)):
            return None

        lat_value = float(lat)
        lon_value = float(lon)
        sog_value = float(sog)
        cog_raw_value = float(cog)
        heading_raw = _get_value(row, "heading", effective_lookup)
        vessel_type = _get_value(row, "vessel_type", effective_lookup)

        if not (-90.0 <= lat_value <= 90.0 and -180.0 <= lon_value <= 180.0):
            return None
        if sog_value < 0.0 or sog_value > 60.0:
            return None
        # AIS COG unavailable values should not be wrapped into a valid angle.
        if not (0.0 <= cog_raw_value < 360.0):
            return None
        cog_value = cog_raw_value

        heading_value = ""
        if heading_raw is not None:
            heading_raw_value = float(heading_raw)
            # AIS heading 511 means "not available"; preserve it as missing.
            if 0.0 <= heading_raw_value < 360.0:
                heading_value = f"{heading_raw_value:.6f}"

        return {
            "mmsi": str(mmsi).strip(),
            "timestamp": format_timestamp(parse_timestamp(str(timestamp))),
            "lat": f"{lat_value:.6f}",
            "lon": f"{lon_value:.6f}",
            "sog": f"{sog_value:.6f}",
            "cog": f"{cog_value:.6f}",
            "heading": heading_value,
            "vessel_type": normalize_vessel_type("" if vessel_type is None else str(vessel_type).strip()),
        }
    except (TypeError, ValueError):
        return None


def preprocess_ais_csv(
    input_path: str | Path,
    output_path: str | Path,
    min_lat: float | None = None,
    max_lat: float | None = None,
    min_lon: float | None = None,
    max_lon: float | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    allowed_vessel_types: set[str] | None = None,
    column_overrides: dict[str, str] | None = None,
) -> dict[str, int | str]:
    source = Path(input_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    valid_rows = 0
    rejected_rows = 0
    filtered_by_bounds = 0
    filtered_by_time = 0
    filtered_by_type = 0
    deduped: dict[tuple[str, str], dict[str, str]] = {}
    start_dt = parse_timestamp(start_time) if start_time else None
    end_dt = parse_timestamp(end_time) if end_time else None
    normalized_types = {normalize_vessel_type(item) for item in allowed_vessel_types} if allowed_vessel_types else None

    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        header_lookup = build_header_lookup(reader.fieldnames, column_overrides=column_overrides)
        for row in reader:
            normalized = _normalize_row(row, header_lookup=header_lookup)
            if normalized is None:
                rejected_rows += 1
                continue
            lat_value = float(normalized["lat"])
            lon_value = float(normalized["lon"])
            if min_lat is not None and lat_value < min_lat:
                filtered_by_bounds += 1
                continue
            if max_lat is not None and lat_value > max_lat:
                filtered_by_bounds += 1
                continue
            if min_lon is not None and lon_value < min_lon:
                filtered_by_bounds += 1
                continue
            if max_lon is not None and lon_value > max_lon:
                filtered_by_bounds += 1
                continue
            row_time = parse_timestamp(normalized["timestamp"])
            if start_dt is not None and row_time < start_dt:
                filtered_by_time += 1
                continue
            if end_dt is not None and row_time > end_dt:
                filtered_by_time += 1
                continue
            if normalized_types is not None:
                vessel_type = normalized["vessel_type"].strip().lower()
                if vessel_type not in normalized_types:
                    filtered_by_type += 1
                    continue
            valid_rows += 1
            deduped[(normalized["mmsi"], normalized["timestamp"])] = normalized

    rows = sorted(deduped.values(), key=lambda item: (item["mmsi"], item["timestamp"]))
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "valid_rows": valid_rows,
        "rejected_rows": rejected_rows,
        "filtered_by_bounds": filtered_by_bounds,
        "filtered_by_time": filtered_by_time,
        "filtered_by_type": filtered_by_type,
        "duplicate_rows": valid_rows - len(rows),
        "output_rows": len(rows),
        "unique_vessels": len({row["mmsi"] for row in rows}),
        "resolved_columns": ",".join(
            f"{key}:{value}" for key, value in header_lookup.items() if value is not None
        ),
    }


def load_curated_csv_rows(input_path: str | Path) -> list[dict[str, str]]:
    with Path(input_path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
    return sorted(rows, key=lambda item: (item["mmsi"], item["timestamp"]))


def _row_to_vessel(row: dict[str, str]) -> VesselState:
    return VesselState(
        mmsi=row["mmsi"],
        lat=float(row["lat"]),
        lon=float(row["lon"]),
        sog=float(row["sog"]),
        cog=float(row["cog"]),
        heading=float(row["heading"]) if row["heading"] else None,
        vessel_type=row["vessel_type"] or None,
    )


def build_snapshot_from_curated_rows(
    rows: list[dict[str, str]],
    own_mmsi: str,
    timestamp: str,
    radius_nm: float,
    max_age_minutes: float = 5.0,
) -> SnapshotInput:
    target_time = parse_timestamp(timestamp)
    best_by_vessel: dict[str, tuple[float, dict[str, str]]] = {}
    for row in rows:
        row_time = parse_timestamp(row["timestamp"])
        delta_seconds = abs((row_time - target_time).total_seconds())
        if delta_seconds > max_age_minutes * 60.0:
            continue
        existing = best_by_vessel.get(row["mmsi"])
        if existing is None or delta_seconds < existing[0]:
            best_by_vessel[row["mmsi"]] = (delta_seconds, row)

    if own_mmsi not in best_by_vessel:
        raise ValueError(f"Own ship MMSI {own_mmsi} not found within {max_age_minutes} minutes of {timestamp}")

    own_ship = _row_to_vessel(best_by_vessel[own_mmsi][1])
    radius_m = nm_to_m(radius_nm)
    targets: list[VesselState] = []
    for mmsi, (_, row) in best_by_vessel.items():
        if mmsi == own_mmsi:
            continue
        vessel = _row_to_vessel(row)
        dx_m, dy_m = latlon_to_local_xy_m(own_ship.lat, own_ship.lon, vessel.lat, vessel.lon)
        if dx_m * dx_m + dy_m * dy_m <= radius_m * radius_m:
            targets.append(vessel)

    targets.sort(key=lambda vessel: vessel.mmsi)
    return SnapshotInput(timestamp=format_timestamp(target_time), own_ship=own_ship, targets=tuple(targets))


def build_snapshot_from_curated_csv(
    input_path: str | Path,
    own_mmsi: str,
    timestamp: str,
    radius_nm: float,
    max_age_minutes: float = 5.0,
) -> SnapshotInput:
    rows = load_curated_csv_rows(input_path)
    return build_snapshot_from_curated_rows(
        rows=rows,
        own_mmsi=own_mmsi,
        timestamp=timestamp,
        radius_nm=radius_nm,
        max_age_minutes=max_age_minutes,
    )
