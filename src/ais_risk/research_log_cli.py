from __future__ import annotations

import argparse

from .research_log import build_benchmark_research_log


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a research log markdown file from pairwise benchmark outputs."
    )
    parser.add_argument("--benchmark-summary", required=True, help="Benchmark summary JSON path.")
    parser.add_argument("--output", required=True, help="Output markdown path.")
    parser.add_argument("--pairwise-stats", help="Optional pairwise dataset stats JSON path.")
    parser.add_argument("--dataset-manifest", help="Optional dataset manifest markdown path.")
    parser.add_argument("--date", help="Optional YYYY-MM-DD override.")
    parser.add_argument("--author", default="Codex", help="Author name for the log.")
    parser.add_argument("--topic", default="pairwise_benchmark", help="Topic slug for the log title.")
    parser.add_argument("--area", help="Optional area text override.")
    parser.add_argument("--config", default="configs/base.toml", help="Config path text to embed in the log.")
    args = parser.parse_args()

    output = build_benchmark_research_log(
        benchmark_summary_path=args.benchmark_summary,
        output_path=args.output,
        pairwise_stats_path=args.pairwise_stats,
        dataset_manifest_path=args.dataset_manifest,
        date_text=args.date,
        author=args.author,
        topic=args.topic,
        area_text=args.area,
        config_text=args.config,
    )
    print(f"log={output}")


if __name__ == "__main__":
    main()
