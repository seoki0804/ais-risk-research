#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pyarrow.parquet as pq


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect schema for a MarineCadastre AIS parquet file.")
    parser.add_argument("input", help="Path to local parquet file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Missing parquet file: {input_path}")

    parquet = pq.ParquetFile(input_path)
    print(f"input={input_path}")
    print(f"num_row_groups={parquet.num_row_groups}")
    print("schema:")
    print(parquet.schema_arrow)


if __name__ == "__main__":
    main()
