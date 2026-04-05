#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-03-17_r40}"
DATES="${DATES:-2024-09-01,2024-09-02,2024-09-05,2024-10-08}"
SINGLE_WRAPPER="${ROOT}/examples/run_cross_year_2024_la_long_beach_candidate_scan_61day.sh"

usage() {
  cat <<'EOF'
Usage:
  DATES=2024-09-01,2024-09-02,2024-09-05 \
    run_cross_year_2024_la_long_beach_candidate_scan_batch_61day.sh [RUN_DATE]

Description:
  Run the 2024 LA/Long Beach candidate scan across multiple dates, reusing the
  single-date MarineCadastre-to-NOAA wrapper and keeping outputs under one
  run-date root.
EOF
}

if [[ "${RUN_DATE}" == "-h" || "${RUN_DATE}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -x "${SINGLE_WRAPPER}" && ! -f "${SINGLE_WRAPPER}" ]]; then
  echo "error=missing_single_wrapper path=${SINGLE_WRAPPER}" >&2
  exit 1
fi

IFS=',' read -r -a DATE_ARRAY <<< "${DATES}"
for DATE in "${DATE_ARRAY[@]}"; do
  echo "scan_date=${DATE}"
  bash "${SINGLE_WRAPPER}" "${DATE}" "${RUN_DATE}"
done
