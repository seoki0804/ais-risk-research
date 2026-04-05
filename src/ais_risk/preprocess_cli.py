from __future__ import annotations

import argparse
from pathlib import Path

from .csv_tools import preprocess_ais_csv
from .ingestion_bundles import resolve_ingestion_bundle
from .source_presets import resolve_source_preset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize and filter raw AIS CSV into canonical curated CSV.")
    parser.add_argument("--input", required=True, help="Path to raw AIS CSV.")
    parser.add_argument("--output", required=True, help="Path to curated CSV.")
    parser.add_argument("--min-lat", type=float, help="Minimum latitude filter.")
    parser.add_argument("--max-lat", type=float, help="Maximum latitude filter.")
    parser.add_argument("--min-lon", type=float, help="Minimum longitude filter.")
    parser.add_argument("--max-lon", type=float, help="Maximum longitude filter.")
    parser.add_argument("--start-time", help="Inclusive UTC/ISO start time filter.")
    parser.add_argument("--end-time", help="Inclusive UTC/ISO end time filter.")
    parser.add_argument("--vessel-types", help="Comma-separated standardized vessel types to keep, e.g. cargo,tanker,passenger.")
    parser.add_argument("--ingestion-bundle", help="Optional ingestion bundle name from configs/ingestion presets.")
    parser.add_argument("--ingestion-config", help="Optional TOML config path from configs/ingestion or a custom ingestion template.")
    parser.add_argument("--source-preset", default="auto", help="Header mapping preset. Use `auto` for alias detection only.")
    parser.add_argument("--column-map", help="Optional overrides like mmsi=ShipId,timestamp=Event Time.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    resolved_bundle = resolve_ingestion_bundle(
        bundle_name=args.ingestion_bundle,
        config_path=args.ingestion_config,
        source_preset_name=args.source_preset,
        manual_column_map_text=args.column_map,
        vessel_types_text=args.vessel_types,
    )
    vessel_types = set(resolved_bundle["vessel_types"]) or None
    stats = preprocess_ais_csv(
        Path(args.input),
        Path(args.output),
        min_lat=args.min_lat,
        max_lat=args.max_lat,
        min_lon=args.min_lon,
        max_lon=args.max_lon,
        start_time=args.start_time,
        end_time=args.end_time,
        allowed_vessel_types=vessel_types,
        column_overrides=resolve_source_preset(
            str(resolved_bundle["source_preset"]),
            str(resolved_bundle["column_map_text"]),
        ),
    )
    print(f"saved={args.output}")
    for key, value in stats.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
