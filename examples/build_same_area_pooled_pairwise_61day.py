#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REPO_ROOT = Path("/Users/seoki/Desktop/research")
DEFAULT_RUN_DATE = "2026-03-17"
DEFAULT_DATES = [
    "2023-08-08",
    "2023-08-09",
    "2023-09-01",
    "2023-09-05",
    "2023-10-08",
    "2023-10-09",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a same-area pooled pairwise CSV from daily main-label NOAA focus bundles."
    )
    parser.add_argument("--region", required=True, help="Region label: houston, nola, or seattle.")
    parser.add_argument("--run-date", default=DEFAULT_RUN_DATE, help="Main benchmark run date.")
    parser.add_argument(
        "--dates",
        nargs="*",
        default=DEFAULT_DATES,
        help="Target dates to pool. Defaults to the six-date validation expansion set.",
    )
    parser.add_argument("--output", required=True, help="Output pooled CSV path.")
    parser.add_argument("--summary-json", help="Optional summary JSON path.")
    return parser.parse_args()


def dataset_path(run_date: str, date: str, region: str) -> Path:
    return (
        REPO_ROOT
        / "outputs"
        / f"noaa_focus_pairwise_bundle_mainlabel_61day_{run_date}"
        / f"noaa_focus_pairwise_bundle_mainlabel_{date}"
        / f"{region}_pairwise_dataset.csv"
    )


def main() -> None:
    args = parse_args()
    paths = [dataset_path(args.run_date, date, args.region) for date in args.dates]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing pooled inputs: {missing}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    merged_rows = 0
    header: list[str] | None = None
    file_counts: list[dict[str, object]] = []

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer: csv.DictWriter[str] | None = None
        for date, path in zip(args.dates, paths, strict=True):
            with path.open("r", encoding="utf-8", newline="") as source_handle:
                reader = csv.DictReader(source_handle)
                current_header = list(reader.fieldnames or [])
                if not current_header:
                    file_counts.append({"date": date, "path": str(path), "row_count": 0, "status": "empty_header"})
                    continue
                if header is None:
                    header = current_header + ["source_date"]
                    writer = csv.DictWriter(handle, fieldnames=header)
                    writer.writeheader()
                elif current_header != header[:-1]:
                    raise ValueError(f"Header mismatch in {path}")

                count = 0
                assert writer is not None
                for row in reader:
                    payload = {key: row.get(key, "") for key in current_header}
                    payload["source_date"] = date
                    writer.writerow(payload)
                    count += 1
                    merged_rows += 1
                file_counts.append({"date": date, "path": str(path), "row_count": count, "status": "merged"})

    summary = {
        "region": args.region,
        "run_date": args.run_date,
        "dates": list(args.dates),
        "output_path": str(output_path),
        "output_rows": merged_rows,
        "header": header or [],
        "file_counts": file_counts,
    }

    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"summary_json={summary_path}")

    print(f"output={output_path}")
    print(f"region={args.region}")
    print(f"dates={','.join(args.dates)}")
    print(f"output_rows={merged_rows}")


if __name__ == "__main__":
    main()
