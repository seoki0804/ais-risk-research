from __future__ import annotations

import argparse
from pathlib import Path

from .ingestion_bundles import resolve_ingestion_bundle
from .schema_probe import inspect_csv_schema, save_schema_probe
from .source_presets import resolve_source_preset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect a raw AIS CSV schema before preprocessing.")
    parser.add_argument("--input", required=True, help="Path to raw AIS CSV.")
    parser.add_argument("--sample-size", type=int, default=50, help="Number of rows to sample for field quality checks.")
    parser.add_argument("--ingestion-bundle", help="Optional ingestion bundle name from configs/ingestion presets.")
    parser.add_argument("--ingestion-config", help="Optional TOML config path from configs/ingestion or a custom ingestion template.")
    parser.add_argument("--source-preset", default="auto", help="Header mapping preset. Use `auto` for alias detection only.")
    parser.add_argument("--column-map", help="Optional overrides like mmsi=ShipId,timestamp=Event Time.")
    parser.add_argument("--output", help="Optional path to save JSON schema probe output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    resolved_bundle = resolve_ingestion_bundle(
        bundle_name=args.ingestion_bundle,
        config_path=args.ingestion_config,
        source_preset_name=args.source_preset,
        manual_column_map_text=args.column_map,
        vessel_types_text=None,
    )
    payload = inspect_csv_schema(
        Path(args.input),
        sample_size=int(args.sample_size),
        column_overrides=resolve_source_preset(
            str(resolved_bundle["source_preset"]),
            str(resolved_bundle["column_map_text"]),
        ),
    )
    print(f"ready_for_preprocess={payload['ready_for_preprocess']}")
    print(f"missing_required={','.join(payload['missing_required'])}")
    print(f"optional_detected={','.join(payload['optional_detected'])}")
    print(f"sample_row_count={payload['sample_row_count']}")
    if args.output:
        path = save_schema_probe(Path(args.output), payload)
        print(f"saved={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
