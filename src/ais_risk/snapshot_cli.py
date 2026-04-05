from __future__ import annotations

import argparse
from pathlib import Path

from .csv_tools import build_snapshot_from_curated_csv
from .io import save_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build own-ship-centric snapshot JSON from curated AIS CSV.")
    parser.add_argument("--input", required=True, help="Path to curated CSV.")
    parser.add_argument("--own-mmsi", required=True, help="Own ship MMSI.")
    parser.add_argument("--timestamp", required=True, help="Target timestamp in ISO format.")
    parser.add_argument("--radius-nm", type=float, default=6.0, help="Nearby target radius in nautical miles.")
    parser.add_argument("--max-age-min", type=float, default=5.0, help="Max allowed time delta per vessel.")
    parser.add_argument("--output", required=True, help="Path to output snapshot JSON.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    snapshot = build_snapshot_from_curated_csv(
        input_path=Path(args.input),
        own_mmsi=str(args.own_mmsi),
        timestamp=str(args.timestamp),
        radius_nm=float(args.radius_nm),
        max_age_minutes=float(args.max_age_min),
    )
    save_snapshot(Path(args.output), snapshot)
    print(f"saved={args.output}")
    print(f"timestamp={snapshot.timestamp}")
    print(f"own_ship={snapshot.own_ship.mmsi}")
    print(f"targets={len(snapshot.targets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
