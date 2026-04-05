from __future__ import annotations

import csv
import json
from pathlib import Path

from .csv_tools import OPTIONAL_COLUMNS, REQUIRED_COLUMNS, build_header_lookup, parse_timestamp
from .vessel_types import normalize_vessel_type


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _can_parse_float(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _is_valid_cog(value: str) -> float:
    parsed = float(value)
    if not (0.0 <= parsed < 360.0):
        raise ValueError("invalid cog range")
    return parsed


def _is_valid_heading(value: str) -> float:
    parsed = float(value)
    if not (0.0 <= parsed < 360.0):
        raise ValueError("invalid heading range")
    return parsed


def _field_quality(sample_rows: list[dict[str, str]], actual_header: str | None, parser) -> dict[str, object]:
    if actual_header is None:
        return {"detected": False, "non_empty_ratio": 0.0, "valid_ratio": 0.0, "sample_values": []}

    non_empty_count = 0
    valid_count = 0
    sample_values: list[str] = []
    for row in sample_rows:
        raw = row.get(actual_header, "")
        if raw == "":
            continue
        non_empty_count += 1
        if len(sample_values) < 3:
            sample_values.append(raw)
        try:
            parser(raw)
            valid_count += 1
        except (TypeError, ValueError):
            continue
    return {
        "detected": True,
        "non_empty_ratio": _safe_ratio(non_empty_count, len(sample_rows)),
        "valid_ratio": _safe_ratio(valid_count, max(non_empty_count, 1)),
        "sample_values": sample_values,
    }


def inspect_csv_schema(
    input_path: str | Path,
    sample_size: int = 50,
    column_overrides: dict[str, str] | None = None,
) -> dict[str, object]:
    source = Path(input_path)
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        header_lookup = build_header_lookup(fieldnames, column_overrides=column_overrides)
        sample_rows: list[dict[str, str]] = []
        for index, row in enumerate(reader):
            if index >= sample_size:
                break
            sample_rows.append(dict(row))

    missing_required = [key for key in REQUIRED_COLUMNS if header_lookup.get(key) is None]
    optional_detected = [key for key in OPTIONAL_COLUMNS if header_lookup.get(key) is not None]
    unknown_headers = [
        field
        for field in fieldnames
        if field not in {value for value in header_lookup.values() if value is not None}
    ]

    field_quality = {
        "timestamp": _field_quality(sample_rows, header_lookup.get("timestamp"), parse_timestamp),
        "lat": _field_quality(sample_rows, header_lookup.get("lat"), float),
        "lon": _field_quality(sample_rows, header_lookup.get("lon"), float),
        "sog": _field_quality(sample_rows, header_lookup.get("sog"), float),
        "cog": _field_quality(sample_rows, header_lookup.get("cog"), _is_valid_cog),
        "heading": _field_quality(sample_rows, header_lookup.get("heading"), _is_valid_heading),
    }
    if header_lookup.get("vessel_type") is not None:
        vessel_type_header = header_lookup["vessel_type"]
        non_empty_vessel_type = sum(1 for row in sample_rows if row.get(vessel_type_header, "") != "")
        standardized_samples = [
            normalize_vessel_type(row[vessel_type_header])
            for row in sample_rows
            if row.get(vessel_type_header, "") != ""
        ][:3]
        field_quality["vessel_type"] = {
            "detected": True,
            "non_empty_ratio": _safe_ratio(non_empty_vessel_type, len(sample_rows)),
            "valid_ratio": 1.0,
            "sample_values": [row[vessel_type_header] for row in sample_rows if row.get(vessel_type_header, "") != ""][:3],
            "standardized_values": standardized_samples,
        }
    else:
        field_quality["vessel_type"] = {
            "detected": False,
            "non_empty_ratio": 0.0,
            "valid_ratio": 0.0,
            "sample_values": [],
            "standardized_values": [],
        }

    notes: list[str] = []
    if missing_required:
        notes.append(f"Missing required columns: {', '.join(missing_required)}")
    for key in ("timestamp", "lat", "lon", "sog", "cog"):
        quality = field_quality[key]
        if quality["detected"] and quality["valid_ratio"] < 0.8:
            notes.append(f"Low parse ratio for {key}: {quality['valid_ratio']:.2f}")

    return {
        "input_path": str(source),
        "fieldnames": fieldnames,
        "detected_mapping": header_lookup,
        "applied_overrides": dict(column_overrides or {}),
        "missing_required": missing_required,
        "optional_detected": optional_detected,
        "unknown_headers": unknown_headers,
        "sample_row_count": len(sample_rows),
        "field_quality": field_quality,
        "ready_for_preprocess": len(missing_required) == 0,
        "notes": notes,
    }


def save_schema_probe(path: str | Path, payload: dict[str, object]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination
