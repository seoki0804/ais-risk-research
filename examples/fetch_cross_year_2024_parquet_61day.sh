#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-03-17_r25}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_cross_year_2024_fetch"
MANIFEST_CSV="${OUT_DIR}/cross_year_2024_manifest.csv"
SUMMARY_JSON="${OUT_DIR}/cross_year_2024_manifest_summary.json"
TARGET_DIR="${ROOT}/data/raw/marinecadastre/ais2024"
PRINT_ONLY="${PRINT_ONLY:-0}"

usage() {
  cat <<'EOF'
Usage:
  PRINT_ONLY=1 fetch_cross_year_2024_parquet_61day.sh [RUN_DATE]

Description:
  Build a small 2024 MarineCadastre daily parquet manifest and optionally fetch
  the selected files into `data/raw/marinecadastre/ais2024`.

Default dates:
  2024-08-01, 2024-09-05, 2024-10-08
EOF
}

if [[ "${RUN_DATE}" == "-h" || "${RUN_DATE}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "${OUT_DIR}" "${TARGET_DIR}"

python "${ROOT}/examples/build_cross_year_2024_url_manifest_61day.py" \
  --output-csv "${MANIFEST_CSV}" \
  --summary-json "${SUMMARY_JSON}"

if [[ "${PRINT_ONLY}" == "1" ]]; then
  echo "print_only=1"
  cat "${MANIFEST_CSV}"
  exit 0
fi

python - <<'PY' "${MANIFEST_CSV}"
import csv
import subprocess
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
with manifest.open() as handle:
    for row in csv.DictReader(handle):
        local_path = Path(row["local_path"])
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if local_path.exists():
            print(f"skip_exists={local_path}")
            continue
        print(f"fetch_url={row['url']}")
        print(f"save_path={local_path}")
        subprocess.run(
            ["curl", "-L", "--fail", "--progress-bar", "-o", str(local_path), row["url"]],
            check=True,
        )
PY

echo "manifest_csv=${MANIFEST_CSV}"
echo "target_dir=${TARGET_DIR}"
