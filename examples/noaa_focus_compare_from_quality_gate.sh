#!/usr/bin/env bash
set -euo pipefail

# Example wrapper for running lightweight focus-MMSI compare from quality-gate results.
# Usage:
#   MANIFEST=data/manifests/noaa_houston_focus_2023-08-01_0000_2359_v1.md \
#   RAW_INPUT=data/raw/noaa/noaa_us_coastal_all_2023-08-01_2023-08-01_v1/raw_focus_houston_0000_2359.csv \
#   GATE_ROWS_CSV=research_logs/2026-03-14_noaa_houston_focus_candidates_pilot_quality_gate_rows.csv \
#   ./examples/noaa_focus_compare_from_quality_gate.sh

MANIFEST="${MANIFEST:?set MANIFEST}"
RAW_INPUT="${RAW_INPUT:?set RAW_INPUT}"
GATE_ROWS_CSV="${GATE_ROWS_CSV:?set GATE_ROWS_CSV}"

CONFIG_PATH="${CONFIG_PATH:-configs/base.toml}"
MODELSETS="${MODELSETS:-rule_score,logreg,hgbt}"
MAX_PASSED="${MAX_PASSED:-4}"
OUTPUT_TAG="${OUTPUT_TAG:-$(date +%F)_quality_gate_focus_compare}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-research_logs/${OUTPUT_TAG}}"
OUTPUT_ROOT="${OUTPUT_ROOT:-outputs/${OUTPUT_TAG}_runs}"
TORCH_DEVICE="${TORCH_DEVICE:-cpu}"
OWN_SHIP_CASE_EVAL_MIN_ROWS="${OWN_SHIP_CASE_EVAL_MIN_ROWS:-30}"
OWN_SHIP_CASE_EVAL_REPEAT_COUNT="${OWN_SHIP_CASE_EVAL_REPEAT_COUNT:-2}"
PRINT_ONLY="${PRINT_ONLY:-0}"
CLEAN_OUTPUT_ROOT="${CLEAN_OUTPUT_ROOT:-0}"

FOCUS_MMSIS="$(python - <<'PY' "$GATE_ROWS_CSV" "$MAX_PASSED"
import csv
import sys

path = sys.argv[1]
limit = max(1, int(sys.argv[2]))
rows = []
with open(path, "r", encoding="utf-8", newline="") as handle:
    for row in csv.DictReader(handle):
        passed = str(row.get("gate_passed", "")).strip().lower() in {"true", "1", "yes"}
        if not passed:
            continue
        try:
            rank = int(str(row.get("rank", "")).strip())
        except Exception:
            rank = 999999
        mmsi = str(row.get("mmsi", "")).strip()
        if not mmsi:
            continue
        rows.append((rank, mmsi))

rows.sort(key=lambda item: (item[0], item[1]))
selected = [mmsi for _, mmsi in rows[:limit]]
print(",".join(selected))
PY
)"

if [[ -z "${FOCUS_MMSIS}" ]]; then
  echo "No passed MMSI found in ${GATE_ROWS_CSV}" >&2
  exit 1
fi

echo "focus_mmsis=${FOCUS_MMSIS}"

if [[ "${PRINT_ONLY}" == "1" ]]; then
  exit 0
fi

if [[ "${CLEAN_OUTPUT_ROOT}" == "1" ]]; then
  rm -rf "${OUTPUT_ROOT}"
  rm -f "${OUTPUT_PREFIX}"_summary.json \
        "${OUTPUT_PREFIX}"_summary.md \
        "${OUTPUT_PREFIX}"_mmsi_rows.csv \
        "${OUTPUT_PREFIX}"_modelset_rows.csv \
        "${OUTPUT_PREFIX}"_aggregate.csv
fi

PYTHONPATH=src python -m ais_risk.focus_mmsi_compare_cli \
  --manifest "${MANIFEST}" \
  --raw-input "${RAW_INPUT}" \
  --output-prefix "${OUTPUT_PREFIX}" \
  --output-root "${OUTPUT_ROOT}" \
  --config "${CONFIG_PATH}" \
  --focus-own-ship-mmsis "${FOCUS_MMSIS}" \
  --benchmark-modelsets "${MODELSETS}" \
  --pairwise-split-strategy own_ship \
  --no-run-calibration-eval \
  --no-run-own-ship-loo \
  --run-own-ship-case-eval \
  --own-ship-case-eval-min-rows "${OWN_SHIP_CASE_EVAL_MIN_ROWS}" \
  --own-ship-case-eval-repeat-count "${OWN_SHIP_CASE_EVAL_REPEAT_COUNT}" \
  --torch-device "${TORCH_DEVICE}" \
  --random-seed 42
