#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


ROOT = Path("/Users/seoki/Desktop/research")
DEFAULT_INPUTS = [
    ROOT / "outputs/2026-03-17_r7_true_new_area_la_long_beach_20230901/la_long_beach_true_extension_2023-09-01/la_long_beach_pairwise_dataset.csv",
    ROOT / "outputs/2026-03-17_r12_true_new_area_la_long_beach_20230902/la_long_beach_true_extension_2023-09-02/la_long_beach_pairwise_dataset.csv",
    ROOT / "outputs/2026-03-17_r6_true_new_area_la_long_beach_20230905/la_long_beach_true_extension_2023-09-05/la_long_beach_pairwise_dataset.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build pooled LA/Long Beach true-new-area pairwise CSV.")
    parser.add_argument("--input", action="append", help="Input pairwise CSV. Can be passed multiple times.")
    parser.add_argument("--output", required=True, help="Output pooled CSV.")
    parser.add_argument("--summary-json", help="Optional summary JSON.")
    return parser.parse_args()


def infer_source_date(path: Path) -> str:
    name = path.as_posix()
    extension_match = re.search(r"true_extension_(\d{4}-\d{2}-\d{2})", name)
    if extension_match:
        return extension_match.group(1)
    generic_match = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    if generic_match:
        return generic_match.group(1)
    raise ValueError(f"Could not infer source date from {path}")


def main() -> None:
    args = parse_args()
    inputs = [Path(p) for p in args.input] if args.input else list(DEFAULT_INPUTS)
    missing = [str(p) for p in inputs if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing inputs: {missing}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    header = None
    total_rows = 0
    file_counts: list[dict[str, object]] = []

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = None
        for path in inputs:
            source_date = infer_source_date(path)
            with path.open("r", encoding="utf-8", newline="") as source_handle:
                reader = csv.DictReader(source_handle)
                current = list(reader.fieldnames or [])
                if not current:
                    file_counts.append({"path": str(path), "source_date": source_date, "row_count": 0, "status": "empty_header"})
                    continue
                if header is None:
                    header = current + ["source_date"]
                    writer = csv.DictWriter(handle, fieldnames=header)
                    writer.writeheader()
                elif current != header[:-1]:
                    raise ValueError(f"Header mismatch in {path}")
                assert writer is not None
                count = 0
                for row in reader:
                    payload = dict(row)
                    payload["source_date"] = source_date
                    writer.writerow(payload)
                    count += 1
                    total_rows += 1
                file_counts.append({"path": str(path), "source_date": source_date, "row_count": count, "status": "merged"})

    summary = {
        "inputs": [str(p) for p in inputs],
        "output": str(output),
        "output_rows": total_rows,
        "file_counts": file_counts,
    }
    if args.summary_json:
        summary_json = Path(args.summary_json)
        summary_json.parent.mkdir(parents=True, exist_ok=True)
        summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"summary_json={summary_json}")
    print(f"output={output}")
    print(f"output_rows={total_rows}")


if __name__ == "__main__":
    main()
