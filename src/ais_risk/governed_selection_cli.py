from __future__ import annotations

import argparse
from pathlib import Path

from .governed_selection import build_governed_selection_matrix


def _parse_models(text: str) -> list[str]:
    values: list[str] = []
    for chunk in str(text).split(","):
        item = chunk.strip()
        if not item:
            continue
        values.append(item)
    return values


def _collect_summary_paths(paths: list[str] | None, path_glob: str | None) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()
    for item in paths or []:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        collected.append(normalized)
        seen.add(normalized)
    if path_glob:
        for matched in sorted(Path(".").glob(path_glob)):
            normalized = str(matched)
            if normalized in seen:
                continue
            collected.append(normalized)
            seen.add(normalized)
    return collected


def main() -> None:
    parser = argparse.ArgumentParser(description="Build governed model recommendation matrix from seed-batch summaries.")
    parser.add_argument(
        "--summary-json",
        action="append",
        help="Path to seed batch summary JSON. Repeat this argument for multiple sources.",
    )
    parser.add_argument(
        "--summary-json-glob",
        help="Optional glob pattern for summary JSON paths, e.g. 'outputs/noaa_*_24h_seed_batch*/**/*summary.json'.",
    )
    parser.add_argument("--output-prefix", required=True, help="Output prefix for governed matrix summary.")
    parser.add_argument("--candidate-models", default="logreg,hgbt,torch_mlp", help="Comma-separated candidate models.")
    parser.add_argument("--ece-threshold", type=float, default=0.25, help="Calibration ECE upper bound for gate pass.")
    parser.add_argument("--loo-threshold", type=float, default=0.60, help="Own-ship LOO F1 lower bound for gate pass.")
    parser.add_argument("--score-key", default="selection_score", help="Aggregate metric key used for ranking within gate.")
    args = parser.parse_args()

    summary_paths = _collect_summary_paths(args.summary_json, args.summary_json_glob)
    if not summary_paths:
        raise ValueError("No summary JSON paths resolved. Provide --summary-json and/or --summary-json-glob.")

    summary = build_governed_selection_matrix(
        summary_json_paths=summary_paths,
        output_prefix=args.output_prefix,
        candidate_models=_parse_models(args.candidate_models),
        ece_threshold=float(args.ece_threshold),
        loo_threshold=float(args.loo_threshold),
        score_key=str(args.score_key),
    )
    print(f"status={summary['status']}")
    print(f"source_count={summary['source_count']}")
    print(f"changed_count={summary['changed_count']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"rows_csv={summary['summary_csv_path']}")


if __name__ == "__main__":
    main()
