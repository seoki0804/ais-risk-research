from __future__ import annotations

import csv
import glob
from pathlib import Path
from typing import Any


def merge_raw_csv_files(
    input_glob: str,
    output_path: str | Path,
    require_header_match: bool = True,
) -> dict[str, Any]:
    paths = sorted(Path(path) for path in glob.glob(input_glob))
    if not paths:
        raise ValueError(f"No input files matched glob: {input_glob}")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    merged_rows = 0
    input_rows = 0
    header: list[str] | None = None
    file_counts: list[dict[str, Any]] = []

    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = None
        for path in paths:
            with path.open("r", encoding="utf-8", newline="") as source_handle:
                reader = csv.DictReader(source_handle)
                current_header = list(reader.fieldnames or [])
                if not current_header:
                    file_counts.append({"path": str(path), "row_count": 0, "status": "empty_header"})
                    continue
                if header is None:
                    header = current_header
                    writer = csv.DictWriter(handle, fieldnames=header)
                    writer.writeheader()
                elif require_header_match and current_header != header:
                    raise ValueError(
                        f"Header mismatch: expected {header}, got {current_header} in {path}"
                    )
                count = 0
                assert writer is not None
                for row in reader:
                    writer.writerow({key: row.get(key, "") for key in header})
                    count += 1
                    merged_rows += 1
                input_rows += count
                file_counts.append({"path": str(path), "row_count": count, "status": "merged"})

    return {
        "input_glob": input_glob,
        "input_file_count": len(paths),
        "output_path": str(output),
        "input_rows": input_rows,
        "output_rows": merged_rows,
        "header": header or [],
        "file_counts": file_counts,
    }
