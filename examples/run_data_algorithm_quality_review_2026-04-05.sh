#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="${TMPDIR:-${ROOT}/.tmp}"
mkdir -p "${TMPDIR}"
RECOMMENDATION_CSV="${RECOMMENDATION_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv}"
AGGREGATE_CSV="${AGGREGATE_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv}"
OUT_OF_TIME_CSV="${OUT_OF_TIME_CSV:-${ROOT}/outputs/2026-04-04_out_of_time_check_10seed/out_of_time_recommendation_check.csv}"
TRANSFER_CSV="${TRANSFER_CSV:-${ROOT}/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.csv}"
OUT_OF_TIME_THRESHOLD_POLICY_COMPARE_JSON="${OUT_OF_TIME_THRESHOLD_POLICY_COMPARE_JSON:-${ROOT}/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed.json}"
MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_JSON="${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_JSON:-${ROOT}/docs/multisource_transfer_governance_bridge_2026-04-05_10seed.json}"
TRANSFER_OVERRIDE_SEED_STRESS_TEST_JSON="${TRANSFER_OVERRIDE_SEED_STRESS_TEST_JSON:-${ROOT}/docs/transfer_override_seed_stress_test_2026-04-05_10seed.json}"
MANUSCRIPT_FREEZE_PACKET_JSON="${MANUSCRIPT_FREEZE_PACKET_JSON:-${ROOT}/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed.json}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-${ROOT}/docs/data_algorithm_quality_review_2026-04-05_10seed}"
MIN_POSITIVE_SUPPORT="${MIN_POSITIVE_SUPPORT:-30}"
MAX_ECE="${MAX_ECE:-0.10}"
MAX_F1_STD="${MAX_F1_STD:-0.03}"
MIN_OUT_OF_TIME_DELTA_F1="${MIN_OUT_OF_TIME_DELTA_F1:--0.05}"
MAX_NEGATIVE_TRANSFER_PAIRS="${MAX_NEGATIVE_TRANSFER_PAIRS:-1}"

(
  cd "${ROOT}"
  env PYTHONPATH=src python -m ais_risk.data_algorithm_quality_review_cli \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --aggregate-csv "${AGGREGATE_CSV}" \
    --out-of-time-csv "${OUT_OF_TIME_CSV}" \
    --transfer-csv "${TRANSFER_CSV}" \
    --out-of-time-threshold-policy-compare-json "${OUT_OF_TIME_THRESHOLD_POLICY_COMPARE_JSON}" \
    --multisource-transfer-governance-bridge-json "${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_JSON}" \
    --transfer-override-seed-stress-test-json "${TRANSFER_OVERRIDE_SEED_STRESS_TEST_JSON}" \
    --manuscript-freeze-packet-json "${MANUSCRIPT_FREEZE_PACKET_JSON}" \
    --output-prefix "${OUTPUT_PREFIX}" \
    --min-positive-support "${MIN_POSITIVE_SUPPORT}" \
    --max-ece "${MAX_ECE}" \
    --max-f1-std "${MAX_F1_STD}" \
    --min-out-of-time-delta-f1 "${MIN_OUT_OF_TIME_DELTA_F1}" \
    --max-negative-transfer-pairs "${MAX_NEGATIVE_TRANSFER_PAIRS}"
)

echo "summary_md=${OUTPUT_PREFIX}.md"
echo "summary_json=${OUTPUT_PREFIX}.json"
echo "dataset_scorecard_csv=${OUTPUT_PREFIX}_dataset_scorecard.csv"
echo "high_risk_models_csv=${OUTPUT_PREFIX}_high_risk_models.csv"
echo "todo_csv=${OUTPUT_PREFIX}_todo.csv"
