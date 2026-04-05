from __future__ import annotations

import argparse
from pathlib import Path

from .own_ship_candidates import rank_own_ship_candidates_csv, recommend_own_ship_candidates_csv, save_own_ship_candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rank MMSI candidates that are suitable as own ship for AIS-only spatial risk analysis."
    )
    parser.add_argument("--input", required=True, help="Path to curated or reconstructed AIS CSV.")
    parser.add_argument("--output", required=True, help="Path to output CSV.")
    parser.add_argument("--radius-nm", type=float, default=6.0, help="Nearby target radius in nautical miles.")
    parser.add_argument("--top-n", type=int, default=10, help="Number of ranked candidates to save.")
    parser.add_argument("--min-targets", type=int, default=1, help="Minimum nearby targets to count as an active window.")
    parser.add_argument("--moving-sog-threshold", type=float, default=1.0, help="SOG threshold used to treat a row as moving.")
    parser.add_argument("--segment-gap-min", type=float, default=10.0, help="Gap threshold used when estimating segment breaks.")
    parser.add_argument("--config", help="Optional config TOML. If provided, representative timestamps are attached.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.config:
        rows = recommend_own_ship_candidates_csv(
            input_path=Path(args.input),
            config_path=Path(args.config),
            radius_nm=float(args.radius_nm),
            top_n=int(args.top_n),
            min_targets=int(args.min_targets),
            moving_sog_threshold=float(args.moving_sog_threshold),
            segment_gap_minutes=float(args.segment_gap_min),
        )
    else:
        rows = rank_own_ship_candidates_csv(
            input_path=Path(args.input),
            radius_nm=float(args.radius_nm),
            top_n=int(args.top_n),
            min_targets=int(args.min_targets),
            moving_sog_threshold=float(args.moving_sog_threshold),
            segment_gap_minutes=float(args.segment_gap_min),
        )
    save_own_ship_candidates(Path(args.output), rows)
    print(f"saved={args.output}")
    print(f"candidates={len(rows)}")
    if rows:
        print(f"top_mmsi={rows[0]['mmsi']}")
        print(f"top_score={float(rows[0]['candidate_score']):.6f}")
        if "recommended_timestamp" in rows[0]:
            print(f"top_timestamp={rows[0]['recommended_timestamp']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
