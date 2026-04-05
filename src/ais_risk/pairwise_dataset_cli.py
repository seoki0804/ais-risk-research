from __future__ import annotations

import argparse

from .config import load_config
from .pairwise_dataset import build_pairwise_learning_dataset_from_csv


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a pairwise learning dataset from reconstructed AIS tracks using realized future separation labels."
    )
    parser.add_argument("--input", required=True, help="Reconstructed tracks CSV path.")
    parser.add_argument("--config", required=True, help="Project TOML config path.")
    parser.add_argument("--output", required=True, help="Output CSV path for the pairwise learning dataset.")
    parser.add_argument("--stats-output", help="Optional JSON path to save dataset stats.")
    parser.add_argument("--own-mmsi", action="append", default=[], help="Own ship MMSI to include. Can be passed multiple times.")
    parser.add_argument("--own-candidates", help="Optional own-ship candidate CSV path.")
    parser.add_argument("--top-n-candidates", type=int, help="Optional top-N own-ship candidates to import from the candidate CSV.")
    parser.add_argument("--radius-nm", type=float, help="Radius around the own ship used to collect current targets.")
    parser.add_argument("--label-distance-nm", type=float, default=0.5, help="Positive label threshold on realized future minimum distance.")
    parser.add_argument("--sample-every", type=int, default=1, help="Use every Nth timestamp to reduce dataset size.")
    parser.add_argument("--min-future-points", type=int, default=2, help="Minimum shared future timestamps required to create a label.")
    parser.add_argument("--min-targets", type=int, default=1, help="Minimum nearby targets required to keep an own-ship timestamp.")
    parser.add_argument("--max-timestamps-per-ship", type=int, help="Optional cap on sampled timestamps per own ship.")
    args = parser.parse_args()

    config = load_config(args.config)
    payload = build_pairwise_learning_dataset_from_csv(
        input_path=args.input,
        output_path=args.output,
        config=config,
        own_mmsis=set(args.own_mmsi),
        own_candidates_path=args.own_candidates,
        top_n_candidates=args.top_n_candidates,
        radius_nm=args.radius_nm,
        label_distance_nm=float(args.label_distance_nm),
        sample_every_nth_timestamp=max(1, int(args.sample_every)),
        min_future_points=max(1, int(args.min_future_points)),
        min_targets=max(1, int(args.min_targets)),
        max_timestamps_per_ship=args.max_timestamps_per_ship,
        stats_output_path=args.stats_output,
    )
    print(f"dataset={payload['dataset_path']}")
    if payload.get("stats_path"):
        print(f"stats={payload['stats_path']}")
    print(f"rows={payload['row_count']}")
    print(f"positive_rate={float(payload['positive_rate']):.6f}")


if __name__ == "__main__":
    main()
