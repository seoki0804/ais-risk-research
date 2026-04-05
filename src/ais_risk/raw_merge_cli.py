from __future__ import annotations

import argparse
import json
from pathlib import Path

from .raw_merge import merge_raw_csv_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Merge multiple raw AIS CSV files into a single raw.csv."
    )
    parser.add_argument("--input-glob", required=True, help="Glob pattern for input CSV files.")
    parser.add_argument("--output", required=True, help="Output merged CSV path.")
    parser.add_argument("--allow-header-mismatch", action="store_true", help="Allow differing headers across files.")
    parser.add_argument("--summary-json", help="Optional path to save merge summary JSON.")
    args = parser.parse_args()

    summary = merge_raw_csv_files(
        input_glob=args.input_glob,
        output_path=args.output,
        require_header_match=not bool(args.allow_header_mismatch),
    )
    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"summary_json={summary_path}")
    print(f"output={summary['output_path']}")
    print(f"input_files={summary['input_file_count']}")
    print(f"output_rows={summary['output_rows']}")


if __name__ == "__main__":
    main()
