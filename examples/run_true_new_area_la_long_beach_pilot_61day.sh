#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
DATE="${1:-2023-09-05}"
RUN_DATE="${2:-2026-03-17_r6}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_true_new_area_la_long_beach_${DATE//-/}"
RAW_CSV="${ROOT}/data/raw/noaa/noaa_us_coastal_all_${DATE}_${DATE}_v1/raw.csv"
BUNDLE_PREFIX="${OUT_DIR}/la_long_beach_true_extension_${DATE}"
FOCUS_DIR="${OUT_DIR}/focus"
DEFAULT_REGION_SPEC="la_long_beach|33.4|34.2|-118.6|-117.7|366755010,366892000,366760650,368010330"
REGION_SPEC="${REGION_SPEC_OVERRIDE:-${DEFAULT_REGION_SPEC}}"
DATASET_CSV="${BUNDLE_PREFIX}/la_long_beach_pairwise_dataset.csv"

usage() {
  cat <<'EOF'
Usage:
  REGION_SPEC_OVERRIDE='la_long_beach|min_lat|max_lat|min_lon|max_lon|mmsi1,...' \
    run_true_new_area_la_long_beach_pilot_61day.sh [DATE] [RUN_DATE]

Description:
  Build a reviewer-grade brand-new-area LA/Long Beach NOAA pairwise pilot bundle
  with main benchmark label distance 0.5 nm, then run own_ship and timestamp
  hgbt/logreg benchmarks.
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

mkdir -p "${OUT_DIR}" "${FOCUS_DIR}"

echo "date=${DATE}"
echo "run_date=${RUN_DATE}"
echo "out_dir=${OUT_DIR}"
echo "raw_csv=${RAW_CSV}"
echo "region_spec=${REGION_SPEC}"

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.noaa_focus_pairwise_bundle_cli \
    --raw-input "${RAW_CSV}" \
    --output-prefix "${BUNDLE_PREFIX}" \
    --focus-output-dir "${FOCUS_DIR}" \
    --source-preset noaa_accessais \
    --start-time "${DATE}T00:00:00Z" \
    --end-time "${DATE}T23:59:59Z" \
    --time-label 0000_2359 \
    --pairwise-sample-every 5 \
    --pairwise-max-timestamps-per-ship 120 \
    --pairwise-label-distance-nm 0.5 \
    --region "${REGION_SPEC}"
)

for split in own_ship timestamp; do
  out_prefix="${OUT_DIR}/la_long_beach_${DATE}_${split}"
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

echo "bundle_prefix=${BUNDLE_PREFIX}"
echo "dataset_csv=${DATASET_CSV}"
echo "own_ship_summary=${OUT_DIR}/la_long_beach_${DATE}_own_ship_summary.json"
echo "timestamp_summary=${OUT_DIR}/la_long_beach_${DATE}_timestamp_summary.json"
