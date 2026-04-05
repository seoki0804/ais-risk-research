from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .demo_package import build_recommended_demo_package_from_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a report package from top recommended own-ship bundles.")
    parser.add_argument("--input", required=True, help="Path to curated or reconstructed AIS CSV.")
    parser.add_argument("--config", default="configs/base.toml", help="Path to config TOML.")
    parser.add_argument("--output-dir", required=True, help="Directory to save the demo package.")
    parser.add_argument("--radius-nm", type=float, default=6.0, help="Nearby target radius in nautical miles.")
    parser.add_argument("--top-n", type=int, default=3, help="Number of recommended bundles to package.")
    parser.add_argument("--min-targets", type=int, default=1, help="Minimum nearby targets used in recommendations.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(Path(args.config))
    manifest = build_recommended_demo_package_from_csv(
        input_path=Path(args.input),
        config=config,
        output_dir=Path(args.output_dir),
        radius_nm=float(args.radius_nm),
        top_n=int(args.top_n),
        min_targets=int(args.min_targets),
    )
    print(f"saved={manifest['output_dir']}")
    print(f"case_count={manifest['case_count']}")
    print(f"index={manifest['index_path']}")
    print(f"manifest={manifest['manifest_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
