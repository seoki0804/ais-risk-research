#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
DATE="${1:-2024-09-05}"
RUN_DATE="${2:-2026-03-17_r26}"
AREA="ny_nj_2024"
DATE_TAG="${DATE//-/}"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_cross_year_2024_candidate_scan/${AREA}_${DATE_TAG}"
REMOTE_URL="https://marinecadastre.gov/downloads/ais2024/ais-${DATE}.parquet"
RAW_CSV="${OUT_DIR}/raw_from_parquet.csv"
RAW_STATS="${OUT_DIR}/raw_from_parquet_stats.json"
CURATED_CSV="${OUT_DIR}/curated.csv"
TRACKS_CSV="${OUT_DIR}/tracks.csv"
CANDIDATE_OUT="${OUT_DIR}/own_ship_candidates_top20.csv"
QUALITY_PREFIX="${OUT_DIR}/quality_gate"

usage() {
  cat <<'EOF'
Usage:
  MAX_ROW_GROUPS=1 LIMIT_ROWS=5000 \
    run_cross_year_2024_ny_nj_candidate_scan_61day.sh [DATE] [RUN_DATE]

Description:
  Convert remote 2024 MarineCadastre daily parquet for the NY/NJ harbor window
  into NOAA-style raw CSV, then run the light-weight chain
  `preprocess -> trajectory -> own_ship_candidates -> quality_gate`.
EOF
}

if [[ "${DATE}" == "-h" || "${DATE}" == "--help" ]]; then
  usage
  exit 0
fi

mkdir -p "${OUT_DIR}"

echo "date=${DATE}"
echo "run_date=${RUN_DATE}"
echo "remote_url=${REMOTE_URL}"
echo "out_dir=${OUT_DIR}"

CONVERT_ARGS=(
  --input "${REMOTE_URL}"
  --output "${RAW_CSV}"
  --stats-json "${RAW_STATS}"
  --min-lat "40.3"
  --max-lat "41.1"
  --min-lon "-74.5"
  --max-lon "-73.5"
  --start-time "${DATE}T00:00:00Z"
  --end-time "${DATE}T23:59:59Z"
  --vessel-types "cargo,tanker,passenger,tug,towing,service"
)

if [[ -n "${MAX_ROW_GROUPS:-}" ]]; then
  CONVERT_ARGS+=(--max-row-groups "${MAX_ROW_GROUPS}")
fi

if [[ -n "${LIMIT_ROWS:-}" ]]; then
  CONVERT_ARGS+=(--limit-rows "${LIMIT_ROWS}")
fi

(
  cd "${ROOT}"
  PYTHONPATH=src python "${ROOT}/examples/convert_marinecadastre_parquet_to_raw_csv_61day.py" "${CONVERT_ARGS[@]}"
)

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.preprocess_cli \
    --input "${RAW_CSV}" \
    --output "${CURATED_CSV}" \
    --source-preset "noaa_accessais" \
    --vessel-types "cargo,tanker,passenger,tug,towing,service" \
    --min-lat "40.3" \
    --max-lat "41.1" \
    --min-lon "-74.5" \
    --max-lon "-73.5" \
    --start-time "${DATE}T00:00:00Z" \
    --end-time "${DATE}T23:59:59Z"
)

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.trajectory_cli \
    --input "${CURATED_CSV}" \
    --output "${TRACKS_CSV}" \
    --split-gap-min "10.0" \
    --max-interp-gap-min "2.0" \
    --step-sec "30"
)

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.own_ship_candidates_cli \
    --input "${TRACKS_CSV}" \
    --output "${CANDIDATE_OUT}" \
    --radius-nm "6.0" \
    --top-n "20" \
    --min-targets "1"
)

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.own_ship_quality_gate_cli \
    --input "${CANDIDATE_OUT}" \
    --output-prefix "${QUALITY_PREFIX}"
)

echo "raw_csv=${RAW_CSV}"
echo "raw_stats=${RAW_STATS}"
echo "curated_csv=${CURATED_CSV}"
echo "tracks_csv=${TRACKS_CSV}"
echo "candidate_csv=${CANDIDATE_OUT}"
echo "quality_gate_summary=${OUT_DIR}/quality_gate_summary.json"
echo "quality_gate_rows=${OUT_DIR}/quality_gate_rows.csv"
