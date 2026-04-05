#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_DATE="${1:-2026-03-17_r20}"
DATES="${DATES:-2023-09-05,2023-09-06,2023-09-07,2023-09-08}"
SINGLE_WRAPPER="${ROOT}/examples/run_true_new_area_savannah_candidate_scan_61day.sh"

usage() {
  cat <<'EOF'
Usage:
  DATES=2023-09-05,2023-09-06,2023-09-07,2023-09-08 \
    run_true_new_area_savannah_candidate_scan_batch_61day.sh [RUN_DATE]

Description:
  Run the Savannah reviewer-safe candidate scan across multiple dates,
  reusing the single-date wrapper and keeping outputs under one run-date root.
EOF
}

if [[ "${RUN_DATE}" == "-h" || "${RUN_DATE}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -f "${SINGLE_WRAPPER}" ]]; then
  echo "error=missing_single_wrapper path=${SINGLE_WRAPPER}" >&2
  exit 1
fi

IFS=',' read -r -a DATE_ARRAY <<< "${DATES}"
for DATE in "${DATE_ARRAY[@]}"; do
  echo "scan_date=${DATE}"
  bash "${SINGLE_WRAPPER}" "${DATE}" "${RUN_DATE}"
done
