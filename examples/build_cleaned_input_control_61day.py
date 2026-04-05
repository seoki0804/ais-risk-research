#!/usr/bin/env python3
"""Build a cleaned-input control CSV from pairwise rows."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter pairwise rows into a cleaned-input control CSV.")
    parser.add_argument("--input", required=True, help="Input pairwise CSV.")
    parser.add_argument("--output", required=True, help="Output filtered CSV.")
    parser.add_argument(
        "--mode",
        default="observed_pair",
        choices=[
            "observed_pair",
            "observed_pair_fp5",
            "own_observed_allow_target_interp",
            "own_observed_allow_target_interp_fp5",
        ],
        help="Filtering mode.",
    )
    parser.add_argument("--summary-json", required=True, help="Summary JSON output path.")
    return parser.parse_args()


def row_kept(row: dict[str, str], mode: str) -> bool:
    future_points_used = int(row["future_points_used"])
    own_observed = row["own_is_interpolated"] == "0"
    target_observed = row["target_is_interpolated"] == "0"

    if mode == "observed_pair":
        return own_observed and target_observed
    if mode == "observed_pair_fp5":
        return own_observed and target_observed and future_points_used >= 5
    if mode == "own_observed_allow_target_interp":
        return own_observed
    if mode == "own_observed_allow_target_interp_fp5":
        return own_observed and future_points_used >= 5
    raise ValueError(f"Unsupported mode: {mode}")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    summary_path = Path(args.summary_json)

    rows = list(csv.DictReader(input_path.open()))
    filtered = [row for row in rows if row_kept(row, args.mode)]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(filtered)

    summary = {
        "input_path": str(input_path),
        "output_path": str(output_path),
        "mode": args.mode,
        "input_row_count": len(rows),
        "output_row_count": len(filtered),
        "input_positive_rate": (sum(int(r["label_future_conflict"]) for r in rows) / len(rows)) if rows else 0.0,
        "output_positive_rate": (sum(int(r["label_future_conflict"]) for r in filtered) / len(filtered)) if filtered else 0.0,
        "input_own_ship_count": len({r["own_mmsi"] for r in rows}),
        "output_own_ship_count": len({r["own_mmsi"] for r in filtered}),
        "output_rows_by_own_ship": Counter(r["own_mmsi"] for r in filtered),
        "output_positive_by_own_ship": Counter(r["own_mmsi"] for r in filtered if int(r["label_future_conflict"]) == 1),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary_path)


if __name__ == "__main__":
    main()
