from __future__ import annotations

import argparse

from .noaa_focus_pairwise_bundle import run_noaa_focus_pairwise_bundle


def _parse_region_specs(entries: list[str] | None) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    for entry in entries or []:
        raw = str(entry).strip()
        if not raw:
            continue
        chunks = [part.strip() for part in raw.split("|")]
        if len(chunks) != 6:
            raise ValueError(
                "Invalid --region format. Use "
                "'label|min_lat|max_lat|min_lon|max_lon|own_mmsi1,own_mmsi2'. "
                f"Received: {raw}"
            )
        label, min_lat, max_lat, min_lon, max_lon, own_mmsis_text = chunks
        own_mmsis = [item.strip() for item in own_mmsis_text.split(",") if item.strip()]
        specs.append(
            {
                "label": label,
                "min_lat": float(min_lat),
                "max_lat": float(max_lat),
                "min_lon": float(min_lon),
                "max_lon": float(max_lon),
                "own_mmsis": own_mmsis,
            }
        )
    return specs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build focus subsets, reconstructed tracks, and pairwise datasets for multiple NOAA regions."
    )
    parser.add_argument("--raw-input", required=True, help="Raw NOAA CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for bundle summary JSON/MD.")
    parser.add_argument(
        "--region",
        action="append",
        help="Region spec: label|min_lat|max_lat|min_lon|max_lon|own_mmsi1,own_mmsi2.",
    )
    parser.add_argument("--config", default="configs/base.toml", help="Project TOML config path.")
    parser.add_argument("--focus-output-dir", help="Optional directory to save raw_focus_{label}_{time_label}.csv.")
    parser.add_argument("--source-preset", default="noaa_accessais", help="Header mapping preset.")
    parser.add_argument(
        "--vessel-types",
        default="cargo,tanker,passenger,tug,service",
        help="Comma-separated vessel types kept in preprocess stage.",
    )
    parser.add_argument("--start-time", help="Optional start time filter, e.g. 2023-08-01T00:00:00Z.")
    parser.add_argument("--end-time", help="Optional end time filter, e.g. 2023-08-01T23:59:59Z.")
    parser.add_argument("--time-label", default="0000_2359", help="Suffix used in focus CSV file names.")
    parser.add_argument("--split-gap-min", type=float, default=10.0, help="Trajectory split gap (minutes).")
    parser.add_argument("--max-interp-gap-min", type=float, default=2.0, help="Trajectory max interpolation gap (minutes).")
    parser.add_argument("--step-sec", type=int, default=30, help="Trajectory interpolation step (seconds).")
    parser.add_argument("--pairwise-label-distance-nm", type=float, default=1.6, help="Pairwise positive label threshold (nm).")
    parser.add_argument("--pairwise-sample-every", type=int, default=5, help="Use every Nth timestamp for pairwise rows.")
    parser.add_argument("--pairwise-min-future-points", type=int, default=2, help="Minimum future points for label generation.")
    parser.add_argument("--pairwise-min-targets", type=int, default=1, help="Minimum nearby targets per own-ship timestamp.")
    parser.add_argument("--pairwise-max-timestamps-per-ship", type=int, default=120, help="Optional cap for own-ship sampled timestamps.")
    args = parser.parse_args()

    region_specs = _parse_region_specs(args.region)
    if not region_specs:
        raise ValueError("At least one --region must be provided.")

    vessel_types = [item.strip().lower() for item in str(args.vessel_types).split(",") if item.strip()]
    max_timestamps = int(args.pairwise_max_timestamps_per_ship)
    pairwise_max_timestamps_per_ship = max_timestamps if max_timestamps > 0 else None

    summary = run_noaa_focus_pairwise_bundle(
        raw_input_path=args.raw_input,
        output_prefix=args.output_prefix,
        region_specs=region_specs,
        config_path=args.config,
        focus_output_dir=args.focus_output_dir,
        source_preset=args.source_preset,
        vessel_types=vessel_types,
        start_time=args.start_time,
        end_time=args.end_time,
        time_label=args.time_label,
        split_gap_minutes=float(args.split_gap_min),
        max_interp_gap_minutes=float(args.max_interp_gap_min),
        step_seconds=int(args.step_sec),
        pairwise_label_distance_nm=float(args.pairwise_label_distance_nm),
        pairwise_sample_every=max(1, int(args.pairwise_sample_every)),
        pairwise_min_future_points=max(1, int(args.pairwise_min_future_points)),
        pairwise_min_targets=max(1, int(args.pairwise_min_targets)),
        pairwise_max_timestamps_per_ship=pairwise_max_timestamps_per_ship,
    )
    print(f"status={summary['status']}")
    print(f"run_count={summary['run_count']}")
    print(f"bundle_dir={summary['bundle_dir']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")


if __name__ == "__main__":
    main()

