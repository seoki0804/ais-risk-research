#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECOMMENDATION_CSV="${RECOMMENDATION_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv}"
TRANSFER_CHECK_CSV="${TRANSFER_CHECK_CSV:-${ROOT}/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.csv}"
OUT_OF_TIME_THRESHOLD_POLICY_COMPARE_JSON="${OUT_OF_TIME_THRESHOLD_POLICY_COMPARE_JSON:-${ROOT}/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed.json}"
TRANSFER_CALIBRATION_PROBE_DETAIL_CSV="${TRANSFER_CALIBRATION_PROBE_DETAIL_CSV:-${ROOT}/docs/houston_transfer_calibration_probe_2026-04-05_10seed_detail.csv}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-${ROOT}/docs/transfer_policy_governance_lock_2026-04-05_10seed}"
SOURCE_REGION_FOR_TRANSFER_OVERRIDE="${SOURCE_REGION_FOR_TRANSFER_OVERRIDE:-houston}"
METRIC_MODE="${METRIC_MODE:-fixed}"
MAX_TARGET_ECE="${MAX_TARGET_ECE:-0.10}"
MAX_NEGATIVE_PAIRS_ALLOWED="${MAX_NEGATIVE_PAIRS_ALLOWED:-1}"
REQUIRED_OUT_OF_TIME_POLICY="${REQUIRED_OUT_OF_TIME_POLICY:-fixed_baseline_threshold}"
OVERRIDE_MODEL_NAME="${OVERRIDE_MODEL_NAME:-}"
OVERRIDE_METHOD="${OVERRIDE_METHOD:-}"

(
  cd "${ROOT}"
  env PYTHONPATH=src python -m ais_risk.transfer_policy_governance_lock_cli \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --transfer-check-csv "${TRANSFER_CHECK_CSV}" \
    --out-of-time-threshold-policy-compare-json "${OUT_OF_TIME_THRESHOLD_POLICY_COMPARE_JSON}" \
    --transfer-calibration-probe-detail-csv "${TRANSFER_CALIBRATION_PROBE_DETAIL_CSV}" \
    --output-prefix "${OUTPUT_PREFIX}" \
    --source-region-for-transfer-override "${SOURCE_REGION_FOR_TRANSFER_OVERRIDE}" \
    --metric-mode "${METRIC_MODE}" \
    --max-target-ece "${MAX_TARGET_ECE}" \
    --max-negative-pairs-allowed "${MAX_NEGATIVE_PAIRS_ALLOWED}" \
    --required-out-of-time-policy "${REQUIRED_OUT_OF_TIME_POLICY}" \
    --override-model-name "${OVERRIDE_MODEL_NAME}" \
    --override-method "${OVERRIDE_METHOD}"
)

echo "summary_md=${OUTPUT_PREFIX}.md"
echo "summary_json=${OUTPUT_PREFIX}.json"
echo "policy_lock_csv=${OUTPUT_PREFIX}_policy_lock.csv"
echo "projected_transfer_check_csv=${OUTPUT_PREFIX}_projected_transfer_check.csv"
echo "candidate_summary_csv=${OUTPUT_PREFIX}_candidate_summary.csv"
