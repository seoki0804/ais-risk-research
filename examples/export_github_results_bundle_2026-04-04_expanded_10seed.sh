#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${DEST_DIR:-${ROOT}/docs/results/2026-04-04-expanded-10seed}"
INPUT_DATA_DIR="${INPUT_DATA_DIR:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
COMMAND_LOG_PATH="${COMMAND_LOG_PATH:-}"
MANIFEST_DATE_TAG="2026-04-04-expanded-10seed"

MULTI_DIR="${ROOT}/outputs/2026-04-04_all_models_multiarea_expanded"
SWEEP_DIR="${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed"
OOT_DIR="${ROOT}/outputs/2026-04-04_out_of_time_check_10seed"
TRANSFER_DIR="${ROOT}/outputs/2026-04-04_transfer_check_10seed"
RELIABILITY_DIR="${ROOT}/outputs/2026-04-04_reliability_report_10seed"
TAXONOMY_DIR="${ROOT}/outputs/2026-04-04_error_taxonomy_10seed"

mkdir -p "${DEST_DIR}"

required_files=(
  "${MULTI_DIR}/all_models_multiarea_leaderboard.csv"
  "${MULTI_DIR}/all_models_multiarea_leaderboard.md"
  "${SWEEP_DIR}/all_models_seed_sweep_summary.md"
  "${SWEEP_DIR}/all_models_seed_sweep_summary.json"
  "${SWEEP_DIR}/all_models_seed_sweep_aggregate.csv"
  "${SWEEP_DIR}/all_models_seed_sweep_winner_summary.csv"
  "${SWEEP_DIR}/all_models_seed_sweep_recommendation.csv"
  "${SWEEP_DIR}/all_models_seed_sweep_recommendation.json"
  "${SWEEP_DIR}/all_models_seed_sweep_recommendation.md"
  "${OOT_DIR}/out_of_time_recommendation_check.csv"
  "${OOT_DIR}/out_of_time_recommendation_check.md"
  "${TRANSFER_DIR}/transfer_recommendation_check.csv"
  "${TRANSFER_DIR}/transfer_recommendation_check.md"
  "${RELIABILITY_DIR}/reliability_recommended_region_summary.csv"
  "${RELIABILITY_DIR}/reliability_recommended_bins.csv"
  "${RELIABILITY_DIR}/reliability_recommended_summary.md"
  "${RELIABILITY_DIR}/reliability_recommended_summary.json"
  "${RELIABILITY_DIR}/houston_recommended_reliability.png"
  "${RELIABILITY_DIR}/nola_recommended_reliability.png"
  "${RELIABILITY_DIR}/seattle_recommended_reliability.png"
  "${TAXONOMY_DIR}/error_taxonomy_region_summary.csv"
  "${TAXONOMY_DIR}/error_taxonomy_details.csv"
  "${TAXONOMY_DIR}/error_taxonomy_summary.md"
  "${TAXONOMY_DIR}/error_taxonomy_summary.json"
)

for file_path in "${required_files[@]}"; do
  if [[ ! -f "${file_path}" ]]; then
    echo "missing required file: ${file_path}" >&2
    exit 1
  fi
done

for file_path in "${required_files[@]}"; do
  cp "${file_path}" "${DEST_DIR}/"
done

command_logs_for_manifest=()
if [[ -n "${COMMAND_LOG_PATH}" ]]; then
  if [[ ! -f "${COMMAND_LOG_PATH}" ]]; then
    echo "missing command log file: ${COMMAND_LOG_PATH}" >&2
    exit 1
  fi
  command_log_bundle_name="external_validity_command_log_2026-04-04_10seed.txt"
  cp "${COMMAND_LOG_PATH}" "${DEST_DIR}/${command_log_bundle_name}"
  command_logs_for_manifest+=("${DEST_DIR}/${command_log_bundle_name}")
fi

input_files=(
  "${SWEEP_DIR}/all_models_seed_sweep_recommendation.csv"
  "${SWEEP_DIR}/all_models_seed_sweep_run_manifest.csv"
  "${INPUT_DATA_DIR}/houston_pooled_pairwise.csv"
  "${INPUT_DATA_DIR}/nola_pooled_pairwise.csv"
  "${INPUT_DATA_DIR}/seattle_pooled_pairwise.csv"
)

for file_path in "${input_files[@]}"; do
  if [[ ! -f "${file_path}" ]]; then
    echo "missing reproducibility input file: ${file_path}" >&2
    exit 1
  fi
done

manifest_args=(
  --bundle-date "${MANIFEST_DATE_TAG}"
  --bundle-dir "${DEST_DIR}"
  --source-dir "multiarea=${MULTI_DIR}"
  --source-dir "seed_sweep=${SWEEP_DIR}"
  --source-dir "out_of_time=${OOT_DIR}"
  --source-dir "transfer=${TRANSFER_DIR}"
  --source-dir "reliability=${RELIABILITY_DIR}"
  --source-dir "taxonomy=${TAXONOMY_DIR}"
  --manifest-txt "${DEST_DIR}/bundle_manifest_${MANIFEST_DATE_TAG}.txt"
  --manifest-json "${DEST_DIR}/bundle_manifest_${MANIFEST_DATE_TAG}.json"
)

for file_path in "${required_files[@]}"; do
  manifest_args+=(--copied-file "$(basename "${file_path}")")
done
for file_path in "${input_files[@]}"; do
  manifest_args+=(--input-file "${file_path}")
done
for file_path in "${command_logs_for_manifest[@]}"; do
  manifest_args+=(--command-log "${file_path}")
done

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.bundle_manifest_cli "${manifest_args[@]}"
)

MANIFEST_PATH="${DEST_DIR}/bundle_manifest_${MANIFEST_DATE_TAG}.txt"
MANIFEST_JSON_PATH="${DEST_DIR}/bundle_manifest_${MANIFEST_DATE_TAG}.json"

echo "exported_dir=${DEST_DIR}"
echo "manifest=${MANIFEST_PATH}"
echo "manifest_json=${MANIFEST_JSON_PATH}"
