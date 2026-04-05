#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
DATE="${1:-2023-09-05}"
RUN_DATE="${2:-2026-03-17_r20}"
AREA="savannah"
RAW_CSV="${ROOT}/data/raw/noaa/noaa_us_coastal_all_${DATE}_${DATE}_v1/raw.csv"
OUT_DIR="${ROOT}/outputs/${RUN_DATE}_new_area_candidate_scan/${AREA}_${DATE//-/}"
CURATED_CSV="${OUT_DIR}/curated.csv"
TRACKS_CSV="${OUT_DIR}/tracks.csv"
CANDIDATE_OUT="${OUT_DIR}/own_ship_candidates_top20.csv"
QUALITY_PREFIX="${OUT_DIR}/quality_gate"

usage() {
  cat <<'EOF'
Usage:
  run_true_new_area_savannah_candidate_scan_61day.sh [DATE] [RUN_DATE]

Description:
  Run reviewer-safe Savannah candidate scan for a single NOAA date,
  using the light-weight chain
  `preprocess -> trajectory -> own_ship_candidates -> quality_gate`.
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

mkdir -p "${OUT_DIR}"

echo "date=${DATE}"
echo "run_date=${RUN_DATE}"
echo "out_dir=${OUT_DIR}"
echo "raw_csv=${RAW_CSV}"

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.preprocess_cli \
    --input "${RAW_CSV}" \
    --output "${CURATED_CSV}" \
    --source-preset "noaa_accessais" \
    --vessel-types "cargo,tanker,passenger,tug,towing,service" \
    --min-lat "31.80" \
    --max-lat "32.32" \
    --min-lon "-81.18" \
    --max-lon "-80.78" \
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

echo "curated_csv=${CURATED_CSV}"
echo "tracks_csv=${TRACKS_CSV}"
echo "candidate_csv=${CANDIDATE_OUT}"
echo "quality_gate_summary=${OUT_DIR}/quality_gate_summary.json"
echo "quality_gate_rows=${OUT_DIR}/quality_gate_rows.csv"
