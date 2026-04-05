#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-04-05_r27}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_true_new_area_savannah_ownship_focus_augmented_pooled"
POOLED_CSV="${OUT_DIR}/savannah_ownship_focus_augmented_pooled_pairwise.csv"
POOLED_SUMMARY="${OUT_DIR}/savannah_ownship_focus_augmented_pooled_pairwise_summary.json"

BASE_POOLED_INPUT="${BASE_POOLED_INPUT_OVERRIDE:-${ROOT}/outputs/2026-04-05_r25_true_new_area_savannah_oct_expanded_pooled/savannah_oct_expanded_pooled_pairwise.csv}"
EXTRA_20230902_INPUT="${EXTRA_20230902_INPUT_OVERRIDE:-${ROOT}/outputs/2026-04-05_r15_sav_override_true_new_area_savannah_20230902/savannah_true_extension_2023-09-02/savannah_pairwise_dataset.csv}"
OWN_MMSI_ALLOWLIST="${OWN_MMSI_ALLOWLIST_OVERRIDE:-211839000,218474000,367726210,368130910,373712000,431888000,477524100,538007911,563066900}"

usage() {
  cat <<'EOF'
Usage:
  run_true_new_area_savannah_ownship_focus_augmented_pooled_61day.sh [RUN_DATE]

Description:
  Build Savannah own-ship support-focused pooled dataset by:
  1) starting from Savannah October-expanded pooled CSV
  2) augmenting with the 2023-09-02 override bundle
  3) filtering to a quality-gated own_mmsi allowlist
  then running own_ship/timestamp hgbt/logreg benchmarks.
EOF
}

if [[ "${RUN_DATE}" == "-h" || "${RUN_DATE}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -f "${BASE_POOLED_INPUT}" ]]; then
  echo "error=missing_base_input path=${BASE_POOLED_INPUT}" >&2
  exit 1
fi
if [[ ! -f "${EXTRA_20230902_INPUT}" ]]; then
  echo "error=missing_extra_input path=${EXTRA_20230902_INPUT}" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

(
  cd "${ROOT}"
  BASE_POOLED_INPUT="${BASE_POOLED_INPUT}" \
  EXTRA_20230902_INPUT="${EXTRA_20230902_INPUT}" \
  OWN_MMSI_ALLOWLIST="${OWN_MMSI_ALLOWLIST}" \
  POOLED_CSV="${POOLED_CSV}" \
  POOLED_SUMMARY="${POOLED_SUMMARY}" \
  python - <<'PY'
import csv
import json
import os
import re
from pathlib import Path

base_input = Path(os.environ["BASE_POOLED_INPUT"]).resolve()
extra_input = Path(os.environ["EXTRA_20230902_INPUT"]).resolve()
output_csv = Path(os.environ["POOLED_CSV"]).resolve()
summary_json = Path(os.environ["POOLED_SUMMARY"]).resolve()
allow = {item.strip() for item in str(os.environ["OWN_MMSI_ALLOWLIST"]).split(",") if item.strip()}

output_csv.parent.mkdir(parents=True, exist_ok=True)
summary_json.parent.mkdir(parents=True, exist_ok=True)

row_count = 0
file_counts = []
fieldnames = None

with output_csv.open("w", encoding="utf-8", newline="") as out_handle:
    writer = None
    for source_path in [base_input, extra_input]:
        source_rows = 0
        with source_path.open("r", encoding="utf-8", newline="") as in_handle:
            reader = csv.DictReader(in_handle)
            current_fields = list(reader.fieldnames or [])
            if not current_fields:
                file_counts.append({"path": str(source_path), "row_count": 0, "status": "empty_header"})
                continue
            if fieldnames is None:
                fieldnames = current_fields
                writer = csv.DictWriter(out_handle, fieldnames=fieldnames)
                writer.writeheader()
            if writer is None:
                raise ValueError("CSV writer not initialized")
            source_date_fallback = ""
            date_match = re.search(r"true_extension_(\\d{4}-\\d{2}-\\d{2})", source_path.as_posix())
            if date_match:
                source_date_fallback = date_match.group(1)
            assert writer is not None
            for row in reader:
                own_mmsi = str(row.get("own_mmsi", "")).strip()
                if own_mmsi not in allow:
                    continue
                payload = {key: row.get(key, "") for key in fieldnames}
                if "source_date" in fieldnames and not payload.get("source_date"):
                    payload["source_date"] = source_date_fallback
                writer.writerow(payload)
                source_rows += 1
                row_count += 1
        file_counts.append({"path": str(source_path), "row_count": source_rows, "status": "merged_filtered"})

summary_payload = {
    "inputs": [str(base_input), str(extra_input)],
    "allowlist": sorted(allow),
    "output": str(output_csv),
    "output_rows": row_count,
    "file_counts": file_counts,
}
summary_json.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
print(f"summary_json={summary_json}")
print(f"output={output_csv}")
print(f"output_rows={row_count}")
PY
)

for split in own_ship timestamp; do
  out_prefix="${OUT_DIR}/savannah_ownship_focus_augmented_pooled_${split}"
  (
    cd "${ROOT}"
    PYTHONPATH=src python -m ais_risk.benchmark_cli \
      --input "${POOLED_CSV}" \
      --output-prefix "${out_prefix}" \
      --models hgbt,logreg \
      --split-strategy "${split}"
  )
done

echo "pooled_csv=${POOLED_CSV}"
echo "pooled_summary=${POOLED_SUMMARY}"
echo "own_ship_summary=${OUT_DIR}/savannah_ownship_focus_augmented_pooled_own_ship_summary.json"
echo "timestamp_summary=${OUT_DIR}/savannah_ownship_focus_augmented_pooled_timestamp_summary.json"
