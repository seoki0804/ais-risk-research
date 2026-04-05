from __future__ import annotations

import argparse
from pathlib import Path

from .summary import build_markdown_summary, save_markdown_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate markdown findings summary from experiment and ablation aggregates.")
    parser.add_argument("--experiment", required=True, help="Path to experiment aggregate JSON.")
    parser.add_argument("--ablation", required=True, help="Path to ablation aggregate JSON.")
    parser.add_argument("--output", required=True, help="Path to output markdown file.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    markdown_text = build_markdown_summary(
        experiment_json_path=Path(args.experiment),
        ablation_json_path=Path(args.ablation),
    )
    save_markdown_summary(Path(args.output), markdown_text)
    print(f"saved={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
