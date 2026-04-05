from __future__ import annotations

import csv
import json
import struct
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from ais_risk.marinecadastre_parquet import convert_marinecadastre_parquet_to_raw_csv, decode_wkb_point


def _encode_point_wkb(lon: float, lat: float) -> bytes:
    return b"".join(
        [
            struct.pack("<B", 1),
            struct.pack("<I", 1),
            struct.pack("<d", lon),
            struct.pack("<d", lat),
        ]
    )


def test_decode_wkb_point_roundtrip() -> None:
    payload = _encode_point_wkb(-74.0, 40.7)
    assert decode_wkb_point(payload) == (40.7, -74.0)


def test_convert_marinecadastre_parquet_to_raw_csv_filters_and_writes(tmp_path: Path) -> None:
    parquet_path = tmp_path / "sample.parquet"
    output_csv = tmp_path / "raw.csv"
    stats_json = tmp_path / "stats.json"

    table = pa.table(
        {
            "mmsi": pa.array([111111111, 222222222], type=pa.int32()),
            "base_date_time": pa.array(
                [
                    datetime(2024, 9, 5, 1, 0, tzinfo=UTC),
                    datetime(2024, 9, 5, 2, 0, tzinfo=UTC),
                ],
                type=pa.timestamp("ms", tz="UTC"),
            ),
            "sog": pa.array([10.0, 12.0], type=pa.float32()),
            "cog": pa.array([180.0, 90.0], type=pa.float32()),
            "heading": pa.array([181, 511], type=pa.int32()),
            "vessel_type": pa.array([70, 52], type=pa.int32()),
            "geometry": pa.array(
                [
                    _encode_point_wkb(-74.0, 40.7),
                    _encode_point_wkb(-80.0, 35.0),
                ],
                type=pa.binary(),
            ),
        }
    )
    pq.write_table(table, parquet_path)

    stats = convert_marinecadastre_parquet_to_raw_csv(
        str(parquet_path),
        output_csv,
        min_lat=40.0,
        max_lat=41.0,
        min_lon=-75.0,
        max_lon=-73.0,
        allowed_vessel_types={"cargo", "tanker"},
        stats_output_path=stats_json,
    )

    with output_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["MMSI"] == "111111111"
    assert rows[0]["LAT"] == "40.700000"
    assert rows[0]["LON"] == "-74.000000"
    assert rows[0]["VesselType"] == "cargo"
    assert rows[0]["Heading"] == "181.000000"
    assert stats["rows_written"] == 1
    assert stats["filtered_by_bounds"] == 1

    saved_stats = json.loads(stats_json.read_text(encoding="utf-8"))
    assert saved_stats["rows_written"] == 1
