from __future__ import annotations

import argparse
from pathlib import Path

from .experiments import run_ablation_experiment_from_csv, save_ablation_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ablation experiments over mined own-ship cases.")
    parser.add_argument("--input", required=True, help="Path to reconstructed or curated AIS CSV.")
    parser.add_argument("--own-mmsi", required=True, help="Own ship MMSI.")
    parser.add_argument("--config", default="configs/base.toml", help="Path to config TOML.")
    parser.add_argument("--radius-nm", type=float, default=6.0, help="Nearby target radius in nautical miles.")
    parser.add_argument("--top-n", type=int, default=5, help="Number of top case timestamps to evaluate.")
    parser.add_argument("--min-targets", type=int, default=1, help="Minimum nearby targets required.")
    parser.add_argument(
        "--ablations",
        required=True,
        help="Comma-separated ablations. Supported: distance,dcpa,tcpa,bearing,relspeed,encounter,density,time_decay,spatial_kernel",
    )
    parser.add_argument("--output-prefix", required=True, help="Prefix for ablation outputs.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    ablation_names = [item.strip() for item in str(args.ablations).split(",") if item.strip()]
    rows, aggregate = run_ablation_experiment_from_csv(
        input_path=Path(args.input),
        own_mmsi=str(args.own_mmsi),
        config_path=Path(args.config),
        radius_nm=float(args.radius_nm),
        ablation_names=ablation_names,
        top_n=int(args.top_n),
        min_targets=int(args.min_targets),
    )
    csv_path, json_path = save_ablation_outputs(Path(args.output_prefix), rows, aggregate)
    print(f"saved_cases={csv_path}")
    print(f"saved_aggregate={json_path}")
    print(f"case_count={aggregate['case_count']}")
    print(f"ablations={','.join(ablation_names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
