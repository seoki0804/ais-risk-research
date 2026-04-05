from __future__ import annotations

import argparse
from pathlib import Path

from .case_mining import mine_cases_from_curated_csv, save_case_candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mine high-risk timestamp candidates from curated AIS CSV.")
    parser.add_argument("--input", required=True, help="Path to curated AIS CSV.")
    parser.add_argument("--own-mmsi", required=True, help="Own ship MMSI.")
    parser.add_argument("--config", default="configs/base.toml", help="Path to config TOML.")
    parser.add_argument("--radius-nm", type=float, default=6.0, help="Nearby target radius in nautical miles.")
    parser.add_argument("--top-n", type=int, default=10, help="Number of ranked candidates to save.")
    parser.add_argument("--max-age-min", type=float, default=5.0, help="Max allowed time delta per vessel.")
    parser.add_argument("--min-targets", type=int, default=1, help="Minimum nearby targets required.")
    parser.add_argument("--output", required=True, help="Path to output CSV.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = mine_cases_from_curated_csv(
        input_path=Path(args.input),
        own_mmsi=str(args.own_mmsi),
        config_path=Path(args.config),
        radius_nm=float(args.radius_nm),
        top_n=int(args.top_n),
        max_age_minutes=float(args.max_age_min),
        min_targets=int(args.min_targets),
    )
    save_case_candidates(Path(args.output), rows)
    print(f"saved={args.output}")
    print(f"cases={len(rows)}")
    if rows:
        print(f"top_timestamp={rows[0]['timestamp']}")
        print(f"top_max_risk={rows[0]['max_risk']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
