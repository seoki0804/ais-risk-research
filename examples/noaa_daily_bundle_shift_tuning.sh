#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <date: YYYY-MM-DD> [run-date: YYYY-MM-DD]"
  exit 1
fi

TARGET_DATE="$1"
RUN_DATE="${2:-$(date +%F)}"

DATASET_ID="noaa_us_coastal_all_${TARGET_DATE}_${TARGET_DATE}_v1"
DATA_ROOT="data/raw/noaa/${DATASET_ID}"
RAW_CSV="${DATA_ROOT}/raw.csv"
DOWNLOAD_DIR="${DATA_ROOT}/downloads/${TARGET_DATE}"
ZIP_PATH="${DATA_ROOT}/downloads/AIS_${TARGET_DATE//-/_}.zip"

BUNDLE_ROOT="outputs/noaa_focus_pairwise_bundle_${RUN_DATE}"
BUNDLE_PREFIX="${BUNDLE_ROOT}/noaa_focus_pairwise_bundle_${TARGET_DATE}"
SHIFT_PREFIX="outputs/scenario_shift_multi_${TARGET_DATE}_${RUN_DATE}/scenario_shift_multi_${TARGET_DATE}"
TUNING_PREFIX="outputs/scenario_threshold_tuning_${TARGET_DATE}_${RUN_DATE}/scenario_threshold_tuning_${TARGET_DATE}"
MERGE_SUMMARY="research_logs/${RUN_DATE}_noaa_raw_merge_${DATASET_ID}_summary.json"

mkdir -p "${DOWNLOAD_DIR}"
mkdir -p "${BUNDLE_ROOT}" "$(dirname "${SHIFT_PREFIX}")" "$(dirname "${TUNING_PREFIX}")"

if [[ ! -f "${RAW_CSV}" ]]; then
  if [[ -f "${ZIP_PATH}" && ! -f "${DOWNLOAD_DIR}/AIS_${TARGET_DATE//-/_}.csv" ]]; then
    unzip -o "${ZIP_PATH}" -d "${DOWNLOAD_DIR}"
  fi
  PYTHONPATH=src python -m ais_risk.raw_merge_cli \
    --input-glob "${DOWNLOAD_DIR}/*.csv" \
    --output "${RAW_CSV}" \
    --summary-json "${MERGE_SUMMARY}"
fi

PYTHONPATH=src python -m ais_risk.noaa_focus_pairwise_bundle_cli \
  --raw-input "${RAW_CSV}" \
  --output-prefix "${BUNDLE_PREFIX}" \
  --region 'houston|29.0|30.5|-96.0|-94.5|368184980,368198210,368216230,368110070,368221490' \
  --region 'nola|29.0|30.5|-91.5|-89.5|368102290,368055920,368119110,367138710,367162750' \
  --region 'seattle|47.0|48.5|-123.5|-122.0|366929710,366772760,366759130,366749710,367608860' \
  --source-preset noaa_accessais \
  --start-time "${TARGET_DATE}T00:00:00Z" \
  --end-time "${TARGET_DATE}T23:59:59Z" \
  --time-label 0000_2359 \
  --pairwise-sample-every 5 \
  --pairwise-max-timestamps-per-ship 120

PYTHONPATH=src python -m ais_risk.scenario_shift_eval_cli \
  --run "houston_24h_${TARGET_DATE//-/}|${BUNDLE_PREFIX}/houston_pairwise_dataset.csv|${DATA_ROOT}/raw_focus_houston_0000_2359.csv" \
  --run "nola_24h_${TARGET_DATE//-/}|${BUNDLE_PREFIX}/nola_pairwise_dataset.csv|${DATA_ROOT}/raw_focus_nola_0000_2359.csv" \
  --run "seattle_24h_${TARGET_DATE//-/}|${BUNDLE_PREFIX}/seattle_pairwise_dataset.csv|${DATA_ROOT}/raw_focus_seattle_0000_2359.csv" \
  --output-prefix "${SHIFT_PREFIX}" \
  --sample-count 3 \
  --min-pair-rows 2 \
  --min-local-target-count 1 \
  --min-snapshot-targets 1 \
  --min-time-gap-min 120

PYTHONPATH=src python -m ais_risk.scenario_threshold_tuning_cli \
  --scenario-shift-summary "${SHIFT_PREFIX}_summary.json" \
  --output-prefix "${TUNING_PREFIX}" \
  --safe-min 0.25 \
  --safe-max 0.45 \
  --safe-step 0.05 \
  --warning-min 0.55 \
  --warning-max 0.80 \
  --warning-step 0.05 \
  --target-warning-nonzero-ratio 0.40 \
  --min-warning-delta-abs-mean 0.005 \
  --min-caution-delta-abs-mean 0.05 \
  --top-k 12 \
  --bootstrap-iterations 300 \
  --bootstrap-random-seed 42

echo "bundle_summary=${BUNDLE_PREFIX}_summary.md"
echo "shift_summary=${SHIFT_PREFIX}_summary.md"
echo "tuning_summary=${TUNING_PREFIX}_summary.md"
