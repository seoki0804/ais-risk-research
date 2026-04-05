#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
DATE="${1:-2024-09-05}"
RUN_DATE="${2:-2026-03-17_r49}"
MAX_ROW_GROUPS="${MAX_ROW_GROUPS:-2}"
LIMIT_ROWS="${LIMIT_ROWS:-12000}"

usage() {
  cat <<'EOF'
Usage:
  MAX_ROW_GROUPS=2 LIMIT_ROWS=12000 \
    run_cross_year_2024_same_area_smoke_compare_61day.sh [DATE] [RUN_DATE]

Description:
  Run a limited 2024 MarineCadastre smoke candidate scan for the three
  same-area harbors used in the main study: Houston, NOLA, Seattle.
EOF
}

if [[ "${DATE}" == "-h" || "${DATE}" == "--help" ]]; then
  usage
  exit 0
fi

run_one() {
  local area="$1"
  local min_lat="$2"
  local max_lat="$3"
  local min_lon="$4"
  local max_lon="$5"
  local out_dir="${ROOT}/outputs/${RUN_DATE}_cross_year_2024_same_area_smoke_compare/${area}_${DATE//-/}"
  local remote_url="https://marinecadastre.gov/downloads/ais2024/ais-${DATE}.parquet"
  local raw_csv="${out_dir}/raw_from_parquet.csv"
  local raw_stats="${out_dir}/raw_from_parquet_stats.json"
  local curated_csv="${out_dir}/curated.csv"
  local tracks_csv="${out_dir}/tracks.csv"
  local candidate_csv="${out_dir}/own_ship_candidates_top20.csv"
  local quality_prefix="${out_dir}/quality_gate"

  mkdir -p "${out_dir}"

  (
    cd "${ROOT}"
    PYTHONPATH=src python "${ROOT}/examples/convert_marinecadastre_parquet_to_raw_csv_61day.py" \
      --input "${remote_url}" \
      --output "${raw_csv}" \
      --stats-json "${raw_stats}" \
      --min-lat "${min_lat}" \
      --max-lat "${max_lat}" \
      --min-lon "${min_lon}" \
      --max-lon "${max_lon}" \
      --start-time "${DATE}T00:00:00Z" \
      --end-time "${DATE}T23:59:59Z" \
      --vessel-types "cargo,tanker,passenger,tug,towing,service" \
      --max-row-groups "${MAX_ROW_GROUPS}" \
      --limit-rows "${LIMIT_ROWS}"
  )

  (
    cd "${ROOT}"
    PYTHONPATH=src python -m ais_risk.preprocess_cli \
      --input "${raw_csv}" \
      --output "${curated_csv}" \
      --source-preset "noaa_accessais" \
      --vessel-types "cargo,tanker,passenger,tug,towing,service" \
      --min-lat "${min_lat}" \
      --max-lat "${max_lat}" \
      --min-lon "${min_lon}" \
      --max-lon "${max_lon}" \
      --start-time "${DATE}T00:00:00Z" \
      --end-time "${DATE}T23:59:59Z"
  )

  (
    cd "${ROOT}"
    PYTHONPATH=src python -m ais_risk.trajectory_cli \
      --input "${curated_csv}" \
      --output "${tracks_csv}" \
      --split-gap-min "10.0" \
      --max-interp-gap-min "2.0" \
      --step-sec "30"
  )

  (
    cd "${ROOT}"
    PYTHONPATH=src python -m ais_risk.own_ship_candidates_cli \
      --input "${tracks_csv}" \
      --output "${candidate_csv}" \
      --radius-nm "6.0" \
      --top-n "20" \
      --min-targets "1"
  )

  (
    cd "${ROOT}"
    PYTHONPATH=src python -m ais_risk.own_ship_quality_gate_cli \
      --input "${candidate_csv}" \
      --output-prefix "${quality_prefix}"
  )

  echo "area=${area} quality_gate_summary=${out_dir}/quality_gate_summary.json"
}

run_one "houston_2024" "29.0" "30.5" "-96.0" "-94.5"
run_one "nola_2024" "29.0" "30.5" "-91.5" "-89.5"
run_one "seattle_2024" "47.0" "48.5" "-123.5" "-122.0"
