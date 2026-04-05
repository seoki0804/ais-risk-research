from __future__ import annotations

import argparse
from pathlib import Path

from .trajectory import reconstruct_trajectory_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reconstruct AIS trajectories into segmented, resampled CSV.")
    parser.add_argument("--input", required=True, help="Path to curated AIS CSV.")
    parser.add_argument("--output", required=True, help="Path to reconstructed trajectory CSV.")
    parser.add_argument("--split-gap-min", type=float, default=10.0, help="Gap threshold to start a new segment.")
    parser.add_argument("--max-interp-gap-min", type=float, default=2.0, help="Maximum gap length allowed for interpolation.")
    parser.add_argument("--step-sec", type=int, default=30, help="Interpolation time step in seconds.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    stats = reconstruct_trajectory_csv(
        input_path=Path(args.input),
        output_path=Path(args.output),
        split_gap_minutes=float(args.split_gap_min),
        max_interp_gap_minutes=float(args.max_interp_gap_min),
        step_seconds=int(args.step_sec),
    )
    print(f"saved={args.output}")
    for key, value in stats.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
