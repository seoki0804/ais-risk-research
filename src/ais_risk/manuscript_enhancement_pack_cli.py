from __future__ import annotations

import argparse
from pathlib import Path

from .manuscript_enhancement_pack import run_manuscript_enhancement_pack


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build manuscript enhancement pack (draft + figures + summary tables)."
    )
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("docs/results/2026-04-04-expanded-10seed"),
        help="Path containing the 10-seed curated result bundle.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("docs/manuscript/v0.2_2026-04-09"),
        help="Path to write manuscript draft assets.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = run_manuscript_enhancement_pack(
        results_root=args.results_root,
        output_root=args.output_root,
    )
    for key, value in summary.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
