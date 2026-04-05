from __future__ import annotations

import argparse
from pathlib import Path

from .workflow import run_ingestion_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the full AIS ingestion workflow from raw CSV to demo package outputs."
    )
    parser.add_argument("--input", required=True, help="Path to raw AIS CSV.")
    parser.add_argument("--output-dir", required=True, help="Directory to save workflow outputs.")
    parser.add_argument("--config", default="configs/base.toml", help="Path to project config TOML.")
    parser.add_argument("--ingestion-bundle", help="Optional named ingestion bundle.")
    parser.add_argument("--ingestion-config", help="Optional ingestion TOML file path.")
    parser.add_argument("--source-preset", default="auto", help="Header mapping preset. Use auto for alias detection.")
    parser.add_argument("--column-map", help="Optional column overrides.")
    parser.add_argument("--vessel-types", help="Optional standardized vessel type filter.")
    parser.add_argument("--min-lat", type=float, help="Minimum latitude filter.")
    parser.add_argument("--max-lat", type=float, help="Maximum latitude filter.")
    parser.add_argument("--min-lon", type=float, help="Minimum longitude filter.")
    parser.add_argument("--max-lon", type=float, help="Maximum longitude filter.")
    parser.add_argument("--start-time", help="Inclusive UTC/ISO start time filter.")
    parser.add_argument("--end-time", help="Inclusive UTC/ISO end time filter.")
    parser.add_argument("--split-gap-min", type=float, default=10.0, help="Gap threshold to split trajectory segments.")
    parser.add_argument("--max-interp-gap-min", type=float, default=2.0, help="Maximum interpolation gap in minutes.")
    parser.add_argument("--step-sec", type=int, default=30, help="Interpolation step in seconds.")
    parser.add_argument("--schema-sample-size", type=int, default=50, help="Schema probe sample size.")
    parser.add_argument("--radius-nm", type=float, help="Target search radius. Defaults to project config radius.")
    parser.add_argument("--top-n", type=int, default=3, help="Number of recommendation/demo cases to keep.")
    parser.add_argument("--min-targets", type=int, default=1, help="Minimum nearby targets used for candidate scoring.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    summary = run_ingestion_workflow(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
        project_config_path=Path(args.config),
        ingestion_bundle_name=args.ingestion_bundle,
        ingestion_config_path=args.ingestion_config,
        source_preset_name=args.source_preset,
        manual_column_map_text=args.column_map,
        vessel_types_text=args.vessel_types,
        min_lat=args.min_lat,
        max_lat=args.max_lat,
        min_lon=args.min_lon,
        max_lon=args.max_lon,
        start_time=args.start_time,
        end_time=args.end_time,
        split_gap_minutes=float(args.split_gap_min),
        max_interp_gap_minutes=float(args.max_interp_gap_min),
        step_seconds=int(args.step_sec),
        schema_sample_size=int(args.schema_sample_size),
        radius_nm=args.radius_nm,
        top_n=int(args.top_n),
        min_targets=int(args.min_targets),
    )
    print(f"saved={summary['output_dir']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"tracks={summary['tracks_csv_path']}")
    print(f"recommendations={summary['own_ship_candidates_path']}")
    print(f"demo_manifest={summary['demo_package_manifest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
