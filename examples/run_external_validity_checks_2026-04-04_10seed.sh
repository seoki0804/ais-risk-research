#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="${TMPDIR:-${ROOT}/.tmp}"
mkdir -p "${TMPDIR}"
INPUT_DIR="${INPUT_DIR:-${ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_2026-03-18_leakfix}"
RECOMMENDATION_CSV="${RECOMMENDATION_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_recommendation.csv}"
BASELINE_LEADERBOARD_CSV="${BASELINE_LEADERBOARD_CSV:-${ROOT}/outputs/2026-04-04_all_models_multiarea_expanded/all_models_multiarea_leaderboard.csv}"
RUN_MANIFEST_CSV="${RUN_MANIFEST_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_run_manifest.csv}"
BASELINE_AGGREGATE_CSV="${BASELINE_AGGREGATE_CSV:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_aggregate.csv}"
BASELINE_SWEEP_OUTPUT_ROOT="${BASELINE_SWEEP_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed}"
COMMAND_LOG_PATH="${COMMAND_LOG_PATH:-${ROOT}/outputs/2026-04-04_external_validity_command_log_10seed.txt}"

OOT_OUTPUT_ROOT="${OOT_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_out_of_time_check_10seed}"
OOT_THRESHOLD_POLICY_COMPARE_PREFIX="${OOT_THRESHOLD_POLICY_COMPARE_PREFIX:-${ROOT}/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed}"
TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX="${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX:-${ROOT}/docs/transfer_policy_governance_lock_2026-04-05_10seed}"
TRANSFER_OUTPUT_ROOT="${TRANSFER_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_transfer_check_10seed}"
TRANSFER_THRESHOLD_GRID_STEP="${TRANSFER_THRESHOLD_GRID_STEP:-0.01}"
TRANSFER_MODEL_SCAN_OUTPUT_ROOT="${TRANSFER_MODEL_SCAN_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_transfer_model_scan_10seed}"
MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT="${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-05_transfer_model_scan_multisource_10seed}"
MULTISOURCE_TRANSFER_SUMMARY_PREFIX="${MULTISOURCE_TRANSFER_SUMMARY_PREFIX:-${ROOT}/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed}"
MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX="${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX:-${ROOT}/docs/multisource_transfer_governance_bridge_2026-04-05_10seed}"
TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX="${TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX:-${ROOT}/docs/transfer_override_seed_stress_test_2026-04-05_10seed}"
TRANSFER_OVERRIDE_SOURCE_REGION="${TRANSFER_OVERRIDE_SOURCE_REGION:-houston}"
TRANSFER_OVERRIDE_TARGET_REGIONS="${TRANSFER_OVERRIDE_TARGET_REGIONS:-nola,seattle}"
TRANSFER_OVERRIDE_BASELINE_MODEL="${TRANSFER_OVERRIDE_BASELINE_MODEL:-hgbt}"
TRANSFER_OVERRIDE_MODEL="${TRANSFER_OVERRIDE_MODEL:-rule_score}"
TRANSFER_OVERRIDE_METHOD="${TRANSFER_OVERRIDE_METHOD:-isotonic}"
TRANSFER_OVERRIDE_SEEDS="${TRANSFER_OVERRIDE_SEEDS:-41,42,43,44,45,46,47,48,49,50}"
TRANSFER_OVERRIDE_SPLIT_STRATEGY="${TRANSFER_OVERRIDE_SPLIT_STRATEGY:-own_ship}"
TRANSFER_OVERRIDE_TRAIN_FRACTION="${TRANSFER_OVERRIDE_TRAIN_FRACTION:-0.6}"
TRANSFER_OVERRIDE_VAL_FRACTION="${TRANSFER_OVERRIDE_VAL_FRACTION:-0.2}"
TRANSFER_OVERRIDE_ECE_GATE_MAX="${TRANSFER_OVERRIDE_ECE_GATE_MAX:-0.10}"
TRANSFER_OVERRIDE_MAX_NEGATIVE_PAIRS_ALLOWED="${TRANSFER_OVERRIDE_MAX_NEGATIVE_PAIRS_ALLOWED:-1}"
DATA_ALGORITHM_QUALITY_REVIEW_PREFIX="${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX:-${ROOT}/docs/data_algorithm_quality_review_2026-04-05_10seed}"
TRANSFER_GAP_DIAG_PREFIX="${TRANSFER_GAP_DIAG_PREFIX:-${ROOT}/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics}"
HOUSTON_TIMESTAMP_SWEEP_OUTPUT_ROOT="${HOUSTON_TIMESTAMP_SWEEP_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-05_houston_timestamp_seed_sweep_10seed}"
TEMPORAL_ROBUST_OUTPUT_PREFIX="${TEMPORAL_ROBUST_OUTPUT_PREFIX:-${ROOT}/docs/temporal_robust_recommendation_2026-04-05_houston_10seed}"
HOUSTON_TRANSFER_POLICY_COMPARE_WORKDIR="${HOUSTON_TRANSFER_POLICY_COMPARE_WORKDIR:-${ROOT}/outputs/2026-04-05_transfer_policy_compare_10seed}"
HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX="${HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX:-${ROOT}/docs/houston_transfer_policy_compare_2026-04-05_10seed}"
HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_WORKDIR="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_WORKDIR:-${ROOT}/outputs/2026-04-05_transfer_policy_compare_all_models_10seed}"
HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX:-${ROOT}/docs/houston_transfer_policy_compare_all_models_2026-04-05_10seed}"
HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS:-rule_score,logreg,hgbt,random_forest,extra_trees,torch_mlp}"
HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX="${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX:-${ROOT}/docs/houston_transfer_calibration_probe_2026-04-05_10seed}"
HOUSTON_TRANSFER_CALIBRATION_METHODS="${HOUSTON_TRANSFER_CALIBRATION_METHODS:-none,platt,isotonic}"
UNCERTAINTY_CONTOUR_OUTPUT_ROOT="${UNCERTAINTY_CONTOUR_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-05_uncertainty_contour_panel_10seed}"
EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX="${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX:-${ROOT}/docs/external_validity_manuscript_assets_2026-04-05_10seed}"
RELIABILITY_OUTPUT_ROOT="${RELIABILITY_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_reliability_report_10seed}"
TAXONOMY_OUTPUT_ROOT="${TAXONOMY_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_error_taxonomy_10seed}"
UNSEEN_AREA_REPORT_PREFIX="${UNSEEN_AREA_REPORT_PREFIX:-${ROOT}/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed}"
MANUSCRIPT_FREEZE_PACKET_PREFIX="${MANUSCRIPT_FREEZE_PACKET_PREFIX:-${ROOT}/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed}"
SIGNIFICANCE_CSV="${SIGNIFICANCE_CSV:-${ROOT}/docs/significance_report_2026-04-04_expanded_models_10seed.csv}"
THRESHOLD_ROBUSTNESS_SUMMARY_CSV="${THRESHOLD_ROBUSTNESS_SUMMARY_CSV:-${ROOT}/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed_summary.csv}"
REVIEWER_AUDIT_PREFIX="${REVIEWER_AUDIT_PREFIX:-${ROOT}/docs/reviewer_quality_audit_2026-04-04_expanded_models_10seed}"

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
    "run_out_of_time_threshold_policy_compare_2026-04-05.sh" \
    env RECOMMENDATION_CSV="${RECOMMENDATION_CSV}" \
    BASELINE_LEADERBOARD_CSV="${BASELINE_LEADERBOARD_CSV}" \
    OUT_OF_TIME_OUTPUT_ROOT="${OOT_OUTPUT_ROOT}" \
    OUTPUT_PREFIX="${OOT_THRESHOLD_POLICY_COMPARE_PREFIX}" \
    DATASET_PREFIXES="houston,nola,seattle" \
    THRESHOLD_GRID_STEP="${TRANSFER_THRESHOLD_GRID_STEP}" \
    MAX_OUT_OF_TIME_ECE="0.10" \
    MIN_OUT_OF_TIME_DELTA_F1="-0.05" \
    MAX_IN_TIME_REGRESSION_FROM_BEST_F1="0.02" \
    INCLUDE_ORACLE_POLICY="1" \
    bash examples/run_out_of_time_threshold_policy_compare_2026-04-05.sh

  run_logged \
    "transfer_recommendation_eval_cli" \
    env PYTHONPATH=src python -m ais_risk.transfer_recommendation_eval_cli \
    --input-dir "${INPUT_DIR}" \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --output-root "${TRANSFER_OUTPUT_ROOT}" \
    --threshold-grid-step "${TRANSFER_THRESHOLD_GRID_STEP}"

  run_logged \
    "transfer_gap_diagnostics_cli" \
    env PYTHONPATH=src python -m ais_risk.transfer_gap_diagnostics_cli \
    --transfer-check-csv "${TRANSFER_OUTPUT_ROOT}/transfer_recommendation_check.csv" \
    --output-prefix "${TRANSFER_GAP_DIAG_PREFIX}" \
    --threshold-grid-step "${TRANSFER_THRESHOLD_GRID_STEP}" \
    --bootstrap-samples 500 \
    --random-seed 42

  run_logged \
    "transfer_model_scan_cli_houston" \
    env PYTHONPATH=src python -m ais_risk.transfer_model_scan_cli \
    --source-region "houston" \
    --source-input "${INPUT_DIR}/houston_pooled_pairwise.csv" \
    --targets "nola:${INPUT_DIR}/nola_pooled_pairwise.csv,seattle:${INPUT_DIR}/seattle_pooled_pairwise.csv" \
    --models "rule_score,logreg,hgbt,random_forest,extra_trees,torch_mlp" \
    --output-root "${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}" \
    --split-strategy "own_ship" \
    --threshold-grid-step "${TRANSFER_THRESHOLD_GRID_STEP}" \
    --random-seed 42 \
    --calibration-ece-max 0.10

  run_logged \
    "run_houston_temporal_robustness_2026-04-05_10seed.sh" \
    env INPUT_DIR="${INPUT_DIR}" \
    BASELINE_AGGREGATE_CSV="${BASELINE_AGGREGATE_CSV}" \
    BASELINE_RECOMMENDATION_CSV="${RECOMMENDATION_CSV}" \
    TIMESTAMP_SWEEP_OUTPUT_ROOT="${HOUSTON_TIMESTAMP_SWEEP_OUTPUT_ROOT}" \
    TEMPORAL_ROBUST_OUTPUT_PREFIX="${TEMPORAL_ROBUST_OUTPUT_PREFIX}" \
    bash examples/run_houston_temporal_robustness_2026-04-05_10seed.sh

  run_logged \
    "run_houston_transfer_policy_compare_2026-04-05.sh" \
    env TRANSFER_MODEL_SCAN_DETAIL_CSV="${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan_detail.csv" \
    WORKDIR="${HOUSTON_TRANSFER_POLICY_COMPARE_WORKDIR}" \
    SUMMARY_PREFIX="${HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX}" \
    bash examples/run_houston_transfer_policy_compare_2026-04-05.sh

  run_logged \
    "run_houston_transfer_policy_compare_2026-04-05_all_models.sh" \
    env TRANSFER_MODEL_SCAN_DETAIL_CSV="${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan_detail.csv" \
    WORKDIR="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_WORKDIR}" \
    SUMMARY_PREFIX="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX}" \
    SHORTLIST_MODELS="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS}" \
    TRANSFER_CHECK_LIKE_CSV="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_WORKDIR}/houston_all_models_transfer_check_like.csv" \
    GAP_OUTPUT_PREFIX="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_WORKDIR}/houston_all_models_transfer_gap" \
    bash examples/run_houston_transfer_policy_compare_2026-04-05.sh

  run_logged \
    "run_houston_transfer_calibration_probe_2026-04-05.sh" \
    env TRANSFER_SCAN_DETAIL_CSV="${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan_detail.csv" \
    OUTPUT_PREFIX="${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX}" \
    SOURCE_REGION="houston" \
    MODELS="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS}" \
    METHODS="${HOUSTON_TRANSFER_CALIBRATION_METHODS}" \
    THRESHOLD_GRID_STEP="${TRANSFER_THRESHOLD_GRID_STEP}" \
    ECE_GATE_MAX="0.10" \
    MAX_NEGATIVE_PAIRS_ALLOWED="1" \
    RANDOM_SEED="42" \
    bash examples/run_houston_transfer_calibration_probe_2026-04-05.sh

  run_logged \
    "run_multisource_transfer_model_scan_summary_2026-04-05.sh" \
    env INPUT_DIR="${INPUT_DIR}" \
    OUTPUT_ROOT="${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}" \
    SUMMARY_PREFIX="${MULTISOURCE_TRANSFER_SUMMARY_PREFIX}" \
    MODELS="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS}" \
    THRESHOLD_GRID_STEP="${TRANSFER_THRESHOLD_GRID_STEP}" \
    RANDOM_SEED="42" \
    MAX_TARGET_ECE="0.10" \
    MAX_NEGATIVE_PAIRS="1" \
    bash examples/run_multisource_transfer_model_scan_summary_2026-04-05.sh

  run_logged \
    "run_transfer_policy_governance_lock_2026-04-05.sh" \
    env RECOMMENDATION_CSV="${RECOMMENDATION_CSV}" \
    TRANSFER_CHECK_CSV="${TRANSFER_OUTPUT_ROOT}/transfer_recommendation_check.csv" \
    OUT_OF_TIME_THRESHOLD_POLICY_COMPARE_JSON="${OOT_THRESHOLD_POLICY_COMPARE_PREFIX}.json" \
    TRANSFER_CALIBRATION_PROBE_DETAIL_CSV="${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX}_detail.csv" \
    OUTPUT_PREFIX="${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX}" \
    SOURCE_REGION_FOR_TRANSFER_OVERRIDE="houston" \
    METRIC_MODE="fixed" \
    MAX_TARGET_ECE="0.10" \
    MAX_NEGATIVE_PAIRS_ALLOWED="1" \
    REQUIRED_OUT_OF_TIME_POLICY="fixed_baseline_threshold" \
    OVERRIDE_MODEL_NAME="" \
    OVERRIDE_METHOD="" \
    bash examples/run_transfer_policy_governance_lock_2026-04-05.sh

  run_logged \
    "run_multisource_transfer_governance_bridge_2026-04-05.sh" \
    env MULTISOURCE_SOURCE_SUMMARY_CSV="${MULTISOURCE_TRANSFER_SUMMARY_PREFIX}_source_summary.csv" \
    TRANSFER_POLICY_GOVERNANCE_LOCK_JSON="${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX}.json" \
    OUTPUT_PREFIX="${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX}" \
    bash examples/run_multisource_transfer_governance_bridge_2026-04-05.sh

  run_logged \
    "run_transfer_override_seed_stress_test_2026-04-05.sh" \
    env INPUT_DIR="${INPUT_DIR}" \
    OUTPUT_PREFIX="${TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX}" \
    SOURCE_REGION="${TRANSFER_OVERRIDE_SOURCE_REGION}" \
    TARGET_REGIONS="${TRANSFER_OVERRIDE_TARGET_REGIONS}" \
    BASELINE_MODEL="${TRANSFER_OVERRIDE_BASELINE_MODEL}" \
    OVERRIDE_MODEL="${TRANSFER_OVERRIDE_MODEL}" \
    OVERRIDE_METHOD="${TRANSFER_OVERRIDE_METHOD}" \
    SEEDS="${TRANSFER_OVERRIDE_SEEDS}" \
    SPLIT_STRATEGY="${TRANSFER_OVERRIDE_SPLIT_STRATEGY}" \
    TRAIN_FRACTION="${TRANSFER_OVERRIDE_TRAIN_FRACTION}" \
    VAL_FRACTION="${TRANSFER_OVERRIDE_VAL_FRACTION}" \
    THRESHOLD_GRID_STEP="${TRANSFER_THRESHOLD_GRID_STEP}" \
    ECE_GATE_MAX="${TRANSFER_OVERRIDE_ECE_GATE_MAX}" \
    MAX_NEGATIVE_PAIRS_ALLOWED="${TRANSFER_OVERRIDE_MAX_NEGATIVE_PAIRS_ALLOWED}" \
    TORCH_DEVICE="auto" \
    CALIBRATION_BINS="10" \
    bash examples/run_transfer_override_seed_stress_test_2026-04-05.sh

  run_logged \
    "uncertainty_contour_cli_houston" \
    env PYTHONPATH=src python -m ais_risk.uncertainty_contour_cli \
    --predictions "${BASELINE_SWEEP_OUTPUT_ROOT}/houston/seed_41/houston_pooled_pairwise_tabular_all_models_test_predictions.csv" \
    --pairwise "${INPUT_DIR}/houston_pooled_pairwise.csv" \
    --calibration-bins "${BASELINE_SWEEP_OUTPUT_ROOT}/houston/seed_41/houston_pooled_pairwise_tabular_all_models_calibration_bins.csv" \
    --output-prefix "${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/houston" \
    --models "hgbt"

  run_logged \
    "uncertainty_contour_cli_nola" \
    env PYTHONPATH=src python -m ais_risk.uncertainty_contour_cli \
    --predictions "${BASELINE_SWEEP_OUTPUT_ROOT}/nola/seed_41/nola_pooled_pairwise_tabular_all_models_test_predictions.csv" \
    --pairwise "${INPUT_DIR}/nola_pooled_pairwise.csv" \
    --calibration-bins "${BASELINE_SWEEP_OUTPUT_ROOT}/nola/seed_41/nola_pooled_pairwise_tabular_all_models_calibration_bins.csv" \
    --output-prefix "${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/nola" \
    --models "hgbt"

  run_logged \
    "uncertainty_contour_cli_seattle" \
    env PYTHONPATH=src python -m ais_risk.uncertainty_contour_cli \
    --predictions "${BASELINE_SWEEP_OUTPUT_ROOT}/seattle/seed_41/seattle_pooled_pairwise_tabular_all_models_test_predictions.csv" \
    --pairwise "${INPUT_DIR}/seattle_pooled_pairwise.csv" \
    --calibration-bins "${BASELINE_SWEEP_OUTPUT_ROOT}/seattle/seed_41/seattle_pooled_pairwise_tabular_all_models_calibration_bins.csv" \
    --output-prefix "${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/seattle" \
    --models "extra_trees"

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
    "external_validity_manuscript_assets_cli" \
    env PYTHONPATH=src python -m ais_risk.external_validity_manuscript_assets_cli \
    --transfer-gap-detail-csv "${TRANSFER_GAP_DIAG_PREFIX}_detail.csv" \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --reliability-region-summary-csv "${RELIABILITY_OUTPUT_ROOT}/reliability_recommended_region_summary.csv" \
    --taxonomy-region-summary-csv "${TAXONOMY_OUTPUT_ROOT}/error_taxonomy_region_summary.csv" \
    --contour-summary-json-by-region "houston:${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/houston_report_summary.json,nola:${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/nola_report_summary.json,seattle:${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/seattle_report_summary.json" \
    --output-prefix "${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}"

  run_logged \
    "run_true_new_area_savannah_ownship_focus_augmented_pooled_61day.sh" \
    bash examples/run_true_new_area_savannah_ownship_focus_augmented_pooled_61day.sh

  run_logged \
    "run_true_new_area_la_long_beach_2023_expanded_pooled_61day.sh" \
    bash examples/run_true_new_area_la_long_beach_2023_expanded_pooled_61day.sh

  run_logged \
    "run_true_new_area_ny_nj_2023_extended_pooled_61day.sh" \
    bash examples/run_true_new_area_ny_nj_2023_extended_pooled_61day.sh

  run_logged \
    "run_cross_year_2024_la_long_beach_pooled_61day.sh" \
    bash examples/run_cross_year_2024_la_long_beach_pooled_61day.sh

  run_logged \
    "run_cross_year_la_long_beach_transfer_61day.sh" \
    bash examples/run_cross_year_la_long_beach_transfer_61day.sh

  run_logged \
    "unseen_area_evidence_report_cli" \
    env PYTHONPATH=src python -m ais_risk.unseen_area_evidence_report_cli \
    --output-prefix "${UNSEEN_AREA_REPORT_PREFIX}" \
    --min-test-positive-support 10

  run_logged \
    "manuscript_freeze_packet_cli" \
    env PYTHONPATH=src python -m ais_risk.manuscript_freeze_packet_cli \
    --unseen-area-summary-csv "${UNSEEN_AREA_REPORT_PREFIX}_summary.csv" \
    --threshold-robustness-summary-csv "${THRESHOLD_ROBUSTNESS_SUMMARY_CSV}" \
    --significance-csv "${SIGNIFICANCE_CSV}" \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --aggregate-csv "${BASELINE_AGGREGATE_CSV}" \
    --max-ece "0.10" \
    --max-f1-std "0.03" \
    --output-prefix "${MANUSCRIPT_FREEZE_PACKET_PREFIX}" \
    --min-test-positive-support 10

  run_logged \
    "run_data_algorithm_quality_review_2026-04-05.sh" \
    env RECOMMENDATION_CSV="${RECOMMENDATION_CSV}" \
    AGGREGATE_CSV="${BASELINE_AGGREGATE_CSV}" \
    OUT_OF_TIME_CSV="${OOT_OUTPUT_ROOT}/out_of_time_recommendation_check.csv" \
    TRANSFER_CSV="${TRANSFER_OUTPUT_ROOT}/transfer_recommendation_check.csv" \
    OUT_OF_TIME_THRESHOLD_POLICY_COMPARE_JSON="${OOT_THRESHOLD_POLICY_COMPARE_PREFIX}.json" \
    MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_JSON="${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX}.json" \
    TRANSFER_OVERRIDE_SEED_STRESS_TEST_JSON="${TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX}.json" \
    MANUSCRIPT_FREEZE_PACKET_JSON="${MANUSCRIPT_FREEZE_PACKET_PREFIX}.json" \
    OUTPUT_PREFIX="${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX}" \
    MIN_POSITIVE_SUPPORT="30" \
    MAX_ECE="0.10" \
    MAX_F1_STD="0.03" \
    MIN_OUT_OF_TIME_DELTA_F1="-0.05" \
    MAX_NEGATIVE_TRANSFER_PAIRS="1" \
    bash examples/run_data_algorithm_quality_review_2026-04-05.sh

  run_logged \
    "reviewer_quality_audit_cli" \
    env PYTHONPATH=src python -m ais_risk.reviewer_quality_audit_cli \
    --recommendation-csv "${RECOMMENDATION_CSV}" \
    --aggregate-csv "${BASELINE_AGGREGATE_CSV}" \
    --winner-summary-csv "${ROOT}/outputs/2026-04-04_all_models_seed_sweep_10seed/all_models_seed_sweep_winner_summary.csv" \
    --out-of-time-csv "${OOT_OUTPUT_ROOT}/out_of_time_recommendation_check.csv" \
    --transfer-csv "${TRANSFER_OUTPUT_ROOT}/transfer_recommendation_check.csv" \
    --reliability-region-summary-csv "${RELIABILITY_OUTPUT_ROOT}/reliability_recommended_region_summary.csv" \
    --taxonomy-region-summary-csv "${TAXONOMY_OUTPUT_ROOT}/error_taxonomy_region_summary.csv" \
    --output-prefix "${REVIEWER_AUDIT_PREFIX}" \
    --significance-csv "${SIGNIFICANCE_CSV}" \
    --threshold-robustness-summary-csv "${THRESHOLD_ROBUSTNESS_SUMMARY_CSV}" \
    --unseen-area-summary-csv "${UNSEEN_AREA_REPORT_PREFIX}_summary.csv" \
    --manuscript-freeze-packet-json "${MANUSCRIPT_FREEZE_PACKET_PREFIX}.json" \
    --transfer-model-scan-json "${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan.json" \
    --transfer-gap-summary-csv "${TRANSFER_GAP_DIAG_PREFIX}_summary.csv" \
    --temporal-robust-summary-json "${TEMPORAL_ROBUST_OUTPUT_PREFIX}.json" \
    --out-of-time-threshold-policy-compare-json "${OOT_THRESHOLD_POLICY_COMPARE_PREFIX}.json" \
    --transfer-policy-governance-lock-json "${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX}.json" \
    --transfer-policy-compare-json "${HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX}.json" \
    --transfer-policy-compare-all-models-json "${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX}.json" \
    --transfer-calibration-probe-json "${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX}.json" \
    --external-validity-manuscript-assets-json "${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}.json" \
    --multisource-transfer-model-scan-summary-json "${MULTISOURCE_TRANSFER_SUMMARY_PREFIX}.json" \
    --multisource-transfer-governance-bridge-json "${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX}.json" \
    --data-algorithm-quality-review-json "${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX}.json"

  run_logged \
    "export_github_results_bundle_2026-04-04_expanded_10seed.sh" \
    env COMMAND_LOG_PATH="${COMMAND_LOG_PATH}" INPUT_DATA_DIR="${INPUT_DIR}" \
    bash examples/export_github_results_bundle_2026-04-04_expanded_10seed.sh
)

echo "out_of_time_md=${OOT_OUTPUT_ROOT}/out_of_time_recommendation_check.md"
echo "out_of_time_policy_compare_md=${OOT_THRESHOLD_POLICY_COMPARE_PREFIX}.md"
echo "transfer_policy_governance_lock_md=${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX}.md"
echo "transfer_md=${TRANSFER_OUTPUT_ROOT}/transfer_recommendation_check.md"
echo "transfer_gap_md=${TRANSFER_GAP_DIAG_PREFIX}.md"
echo "transfer_scan_md=${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan.md"
echo "temporal_robust_md=${TEMPORAL_ROBUST_OUTPUT_PREFIX}.md"
echo "transfer_policy_compare_md=${HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX}.md"
echo "transfer_policy_compare_all_models_md=${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX}.md"
echo "transfer_calibration_probe_md=${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX}.md"
echo "multisource_transfer_scan_summary_md=${MULTISOURCE_TRANSFER_SUMMARY_PREFIX}.md"
echo "multisource_transfer_governance_bridge_md=${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX}.md"
echo "transfer_override_seed_stress_test_md=${TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX}.md"
echo "data_algorithm_quality_review_md=${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX}.md"
echo "manuscript_assets_md=${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}.md"
echo "transfer_uncertainty_table_md=${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}_transfer_uncertainty_table.md"
echo "scenario_panels_md=${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}_scenario_panels.md"
echo "reliability_md=${RELIABILITY_OUTPUT_ROOT}/reliability_recommended_summary.md"
echo "taxonomy_md=${TAXONOMY_OUTPUT_ROOT}/error_taxonomy_summary.md"
echo "unseen_area_md=${UNSEEN_AREA_REPORT_PREFIX}.md"
echo "manuscript_freeze_md=${MANUSCRIPT_FREEZE_PACKET_PREFIX}.md"
echo "command_log=${COMMAND_LOG_PATH}"
