#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="${INPUT_DIR:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
RECOMMENDATION_CSV="${RECOMMENDATION_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv}"
BASELINE_LEADERBOARD_CSV="${BASELINE_LEADERBOARD_CSV:-${ROOT}/outputs/2026-04-04_all_models_multiarea_expanded/all_models_multiarea_leaderboard.csv}"
RUN_MANIFEST_CSV="${RUN_MANIFEST_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_run_manifest.csv}"
COMMAND_LOG_PATH="${COMMAND_LOG_PATH:-${ROOT}/outputs/2026-04-04_external_validity_command_log_10seed.txt}"

OOT_OUTPUT_ROOT="${OOT_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_out_of_time_check_10seed}"
TRANSFER_OUTPUT_ROOT="${TRANSFER_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_transfer_check_10seed}"
RELIABILITY_OUTPUT_ROOT="${RELIABILITY_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_reliability_report_10seed}"
TAXONOMY_OUTPUT_ROOT="${TAXONOMY_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_error_taxonomy_10seed}"

mkdir -p "$(dirname "${COMMAND_LOG_PATH}")"
: > "${COMMAND_LOG_PATH}"

run_logged() {
  local label="$1"
  shift
  local -a command=("$@")
  {
    echo "=== ${label} ==="
    echo "timestamp_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    printf "command="
    printf "%q " "${command[@]}"
    echo
  } | tee -a "${COMMAND_LOG_PATH}"
  "${command[@]}" 2>&1 | tee -a "${COMMAND_LOG_PATH}"
}

(
  cd "${ROOT}"
  run_logged \
    "out_of_time_eval_cli" \
    env PYTHONPATH=src python -m ais_risk.out_of_time_eval_cli \
    --input-dir "${INPUT_DIR}" \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --baseline-leaderboard-csv "${BASELINE_LEADERBOARD_CSV}" \
    --output-root "${OOT_OUTPUT_ROOT}"

  run_logged \
    "transfer_recommendation_eval_cli" \
    env PYTHONPATH=src python -m ais_risk.transfer_recommendation_eval_cli \
    --input-dir "${INPUT_DIR}" \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --output-root "${TRANSFER_OUTPUT_ROOT}"

  run_logged \
    "reliability_report_cli" \
    env PYTHONPATH=src python -m ais_risk.reliability_report_cli \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --run-manifest-csv "${RUN_MANIFEST_CSV}" \
    --output-root "${RELIABILITY_OUTPUT_ROOT}"

  run_logged \
    "error_taxonomy_report_cli" \
    env PYTHONPATH=src python -m ais_risk.error_taxonomy_report_cli \
    --input-dir "${INPUT_DIR}" \
    --regions "houston,nola,seattle" \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --run-manifest-csv "${RUN_MANIFEST_CSV}" \
    --output-root "${TAXONOMY_OUTPUT_ROOT}" \
    --seed 42

  run_logged \
    "export_github_results_bundle_2026-04-04_expanded_10seed.sh" \
    env COMMAND_LOG_PATH="${COMMAND_LOG_PATH}" INPUT_DATA_DIR="${INPUT_DIR}" \
    bash examples/export_github_results_bundle_2026-04-04_expanded_10seed.sh
)

echo "out_of_time_md=${OOT_OUTPUT_ROOT}/out_of_time_recommendation_check.md"
echo "transfer_md=${TRANSFER_OUTPUT_ROOT}/transfer_recommendation_check.md"
echo "reliability_md=${RELIABILITY_OUTPUT_ROOT}/reliability_recommended_summary.md"
echo "taxonomy_md=${TAXONOMY_OUTPUT_ROOT}/error_taxonomy_summary.md"
echo "command_log=${COMMAND_LOG_PATH}"
