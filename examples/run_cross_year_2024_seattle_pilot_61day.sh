#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
DATE="${1:-2024-09-05}"
RUN_DATE="${2:-2026-03-17_r50}"
DATE_TAG="${DATE//-/}"
DEFAULT_BASE="${ROOT}/outputs/2026-03-17_r49_cross_year_2024_same_area_smoke_compare/seattle_2024_${DATE_TAG}"
RAW_CSV="${RAW_CSV_OVERRIDE:-${DEFAULT_BASE}/raw_from_parquet.csv}"
QUALITY_ROWS="${QUALITY_ROWS_OVERRIDE:-${DEFAULT_BASE}/quality_gate_rows.csv}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_cross_year_2024_seattle_pilot_${DATE_TAG}"
PREFIX="${OUT_DIR}/seattle_2024_${DATE_TAG}"
FOCUS_DIR="${OUT_DIR}/focus"
DATASET_CSV="${PREFIX}/seattle_2024_pairwise_dataset.csv"
TOP_N_OWN_SHIPS="${TOP_N_OWN_SHIPS:-5}"

usage() {
  cat <<'EOF'
Usage:
  RAW_CSV_OVERRIDE=/path/to/raw.csv \
  QUALITY_ROWS_OVERRIDE=/path/to/quality_gate_rows.csv \
    run_cross_year_2024_seattle_pilot_61day.sh [DATE] [RUN_DATE]

Description:
  Build a first cross-year Seattle pairwise pilot from a previously converted
  2024 raw-like CSV and a quality-gate rows CSV. The wrapper automatically
  selects the top gate-passed MMSIs and runs own_ship/timestamp hgbt/logreg
  benchmarks with the main `0.5 nm` label.
EOF
}

if [[ "${DATE}" == "-h" || "${DATE}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -f "${RAW_CSV}" ]]; then
  echo "error=missing_raw_csv path=${RAW_CSV}" >&2
  exit 1
fi

if [[ ! -f "${QUALITY_ROWS}" ]]; then
  echo "error=missing_quality_rows path=${QUALITY_ROWS}" >&2
  exit 1
fi

OWN_MMSIS="$(
  python - <<'PY' "${QUALITY_ROWS}" "${TOP_N_OWN_SHIPS}"
import csv
import sys

path = sys.argv[1]
top_n = int(sys.argv[2])
with open(path, encoding="utf-8", newline="") as handle:
    rows = list(csv.DictReader(handle))
passed = [row["mmsi"] for row in rows if row.get("gate_passed") == "True"]
selected = passed[:top_n]
print(",".join(selected))
PY
)"

if [[ -z "${OWN_MMSIS}" ]]; then
  echo "error=no_passed_own_mmsis quality_rows=${QUALITY_ROWS}" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}" "${FOCUS_DIR}"

echo "date=${DATE}"
echo "run_date=${RUN_DATE}"
echo "raw_csv=${RAW_CSV}"
echo "quality_rows=${QUALITY_ROWS}"
echo "own_mmsis=${OWN_MMSIS}"

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.noaa_focus_pairwise_bundle_cli \
    --raw-input "${RAW_CSV}" \
    --output-prefix "${PREFIX}" \
    --focus-output-dir "${FOCUS_DIR}" \
    --source-preset noaa_accessais \
    --start-time "${DATE}T00:00:00Z" \
    --end-time "${DATE}T23:59:59Z" \
    --time-label 0000_2359 \
    --pairwise-sample-every 5 \
    --pairwise-max-timestamps-per-ship 120 \
    --pairwise-label-distance-nm 0.5 \
    --region "seattle_2024|47.0|48.5|-123.5|-122.0|${OWN_MMSIS}"
)

for split in own_ship timestamp; do
  out_prefix="${OUT_DIR}/seattle_2024_${DATE}_${split}"
  echo "benchmark_split=${split} output_prefix=${out_prefix}"
  if ! (
    cd "${ROOT}"
    PYTHONPATH=src python -m ais_risk.benchmark_cli \
      --input "${DATASET_CSV}" \
      --output-prefix "${out_prefix}" \
      --models hgbt,logreg \
      --split-strategy "${split}"
  ); then
    echo "benchmark_failed_split=${split}" >&2
  fi
done

echo "bundle_prefix=${PREFIX}"
echo "dataset_csv=${DATASET_CSV}"
echo "own_ship_summary=${OUT_DIR}/seattle_2024_${DATE}_own_ship_summary.json"
echo "timestamp_summary=${OUT_DIR}/seattle_2024_${DATE}_timestamp_summary.json"
