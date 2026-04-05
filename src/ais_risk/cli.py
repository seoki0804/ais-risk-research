from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .io import load_snapshot, save_result
from .pipeline import run_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run baseline AIS risk mapping on a snapshot JSON file.")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot JSON input.")
    parser.add_argument("--config", required=True, help="Path to TOML config.")
    parser.add_argument("--output", required=True, help="Path to JSON result output.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    snapshot = load_snapshot(Path(args.snapshot))
    result = run_snapshot(snapshot, config)
    save_result(Path(args.output), result)

    print(f"project={result.project_name}")
    print(f"timestamp={result.timestamp}")
    for scenario in result.scenarios:
        summary = scenario.summary
        print(
            "scenario="
            f"{summary.scenario_name} "
            f"multiplier={summary.speed_multiplier:.2f} "
            f"max_risk={summary.max_risk:.3f} "
            f"mean_risk={summary.mean_risk:.3f} "
            f"warning_area_nm2={summary.warning_area_nm2:.3f} "
            f"dominant_sector={summary.dominant_sector}"
        )
    print(f"saved={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
