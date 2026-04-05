#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <run-date: YYYY-MM-DD> <target-date-1> [target-date-2 ...]"
  exit 1
fi

RUN_DATE="$1"
shift

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DAILY_SCRIPT="${SCRIPT_DIR}/noaa_daily_bundle_shift_tuning.sh"

if [[ ! -x "${DAILY_SCRIPT}" ]]; then
  echo "daily script missing or not executable: ${DAILY_SCRIPT}"
  exit 1
fi

for TARGET_DATE in "$@"; do
  echo "== run ${TARGET_DATE} =="
  "${DAILY_SCRIPT}" "${TARGET_DATE}" "${RUN_DATE}"
done

echo "status=completed"
