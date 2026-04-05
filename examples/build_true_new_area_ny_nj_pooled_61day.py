#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import re


ROOT = Path("/Users/seoki/Desktop/research")
DEFAULT_INPUTS = [
    ROOT / "outputs/2026-03-17_r4_true_new_area_ny_nj_20230901/ny_nj_true_extension_2023-09-01/ny_nj_pairwise_dataset.csv",
    ROOT / "outputs/2026-03-17_r2_true_new_area_ny_nj_20230905/ny_nj_true_extension_2023-09-05/ny_nj_pairwise_dataset.csv",
    ROOT / "outputs/2026-03-17_r3_true_new_area_ny_nj_20231008/ny_nj_true_extension_2023-10-08/ny_nj_pairwise_dataset.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build pooled NY/NJ true-new-area pairwise CSV.")
    parser.add_argument("--input", action="append", help="Input pairwise CSV. Can be passed multiple times.")
    parser.add_argument("--output", required=True, help="Output pooled CSV.")
    parser.add_argument("--summary-json", help="Optional summary JSON.")
    return parser.parse_args()


def infer_source_date(path: Path) -> str:
    name = path.as_posix()
    candidates: list[tuple[int, str]] = []
    for match in re.finditer(r"(20\d{2}-\d{2}-\d{2})", name):
        candidates.append((match.start(), match.group(1)))
    for match in re.finditer(r"(20\d{2})(\d{2})(\d{2})", name):
        candidates.append((match.start(), f"{match.group(1)}-{match.group(2)}-{match.group(3)}"))
    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[-1][1]
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
