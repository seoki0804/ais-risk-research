from __future__ import annotations

import argparse
from pathlib import Path

from ais_risk.marinecadastre_parquet import convert_marinecadastre_parquet_to_raw_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert local or remote MarineCadastre daily parquet into NOAA-style raw AIS CSV."
    )
    parser.add_argument("--input", required=True, help="Local parquet path or remote parquet URL.")
    parser.add_argument("--output", required=True, help="Output raw-style CSV path.")
    parser.add_argument("--stats-json", help="Optional JSON path for conversion stats.")
    parser.add_argument("--min-lat", type=float, help="Minimum latitude filter.")
    parser.add_argument("--max-lat", type=float, help="Maximum latitude filter.")
    parser.add_argument("--min-lon", type=float, help="Minimum longitude filter.")
    parser.add_argument("--max-lon", type=float, help="Maximum longitude filter.")
    parser.add_argument("--start-time", help="Inclusive UTC/ISO start time filter.")
    parser.add_argument("--end-time", help="Inclusive UTC/ISO end time filter.")
    parser.add_argument("--vessel-types", help="Comma-separated normalized vessel types to keep.")
    parser.add_argument("--max-row-groups", type=int, help="Optional row-group cap for smoke runs.")
    parser.add_argument("--limit-rows", type=int, help="Optional row limit after filtering.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    allowed_types = None
    if args.vessel_types:
        allowed_types = {item.strip() for item in args.vessel_types.split(",") if item.strip()}
    stats = convert_marinecadastre_parquet_to_raw_csv(
        input_path_or_url=args.input,
        output_path=Path(args.output),
        min_lat=args.min_lat,
        max_lat=args.max_lat,
        min_lon=args.min_lon,
        max_lon=args.max_lon,
        start_time=args.start_time,
        end_time=args.end_time,
        allowed_vessel_types=allowed_types,
        max_row_groups=args.max_row_groups,
        limit_rows=args.limit_rows,
        stats_output_path=args.stats_json,
    )
    print(f"saved={args.output}")
    if args.stats_json:
        print(f"stats_json={args.stats_json}")
    for key, value in stats.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
