from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .io import load_snapshot
from .report import build_html_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a self-contained HTML report from snapshot and result JSON.")
    parser.add_argument("--snapshot", required=True, help="Path to snapshot JSON.")
    parser.add_argument("--result", required=True, help="Path to result JSON.")
    parser.add_argument("--config", default="configs/base.toml", help="Path to config TOML.")
    parser.add_argument("--output", required=True, help="Path to output HTML file.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    snapshot = load_snapshot(Path(args.snapshot))
    build_html_report(
        snapshot=snapshot,
        result_path=Path(args.result),
        output_path=Path(args.output),
        radius_nm=config.grid.radius_nm,
        cell_size_m=config.grid.cell_size_m,
        safe_threshold=config.thresholds.safe,
        warning_threshold=config.thresholds.warning,
    )
    print(f"saved={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
