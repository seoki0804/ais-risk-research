#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path("/Users/seoki/Desktop/research")
DEFAULT_DATES = ["2024-08-01", "2024-09-05", "2024-10-08"]
BASE_URL = "https://marinecadastre.gov/downloads/ais2024"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build URL manifest for 2024 MarineCadastre AIS daily parquet files.")
    parser.add_argument("--date", action="append", help="Date in YYYY-MM-DD format. Can be passed multiple times.")
    parser.add_argument("--output-csv", required=True, help="Output manifest CSV path.")
    parser.add_argument("--summary-json", help="Optional summary JSON path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dates = args.date if args.date else list(DEFAULT_DATES)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for date in dates:
        filename = f"ais-{date}.parquet"
        rows.append(
            {
                "date": date,
                "filename": filename,
                "url": f"{BASE_URL}/{filename}",
                "local_path": str(ROOT / "data/raw/marinecadastre/ais2024" / filename),
            }
        )

    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "filename", "url", "local_path"])
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "row_count": len(rows),
        "dates": dates,
        "output_csv": str(output_csv),
        "base_url": BASE_URL,
    }
    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"summary_json={summary_path}")

    print(f"output_csv={output_csv}")
    print(f"row_count={len(rows)}")


if __name__ == "__main__":
    main()
