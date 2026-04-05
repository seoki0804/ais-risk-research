#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMPDIR="${TMPDIR:-${ROOT}/.tmp}"
mkdir -p "${TMPDIR}"
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
UNSEEN_AREA_REPORT_PREFIX="${UNSEEN_AREA_REPORT_PREFIX:-${ROOT}/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed}"
MANUSCRIPT_FREEZE_PACKET_PREFIX="${MANUSCRIPT_FREEZE_PACKET_PREFIX:-${ROOT}/docs/manuscript_freeze_packet_2026-04-04_expanded_models_10seed}"
TRANSFER_MODEL_SCAN_OUTPUT_ROOT="${TRANSFER_MODEL_SCAN_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-04_transfer_model_scan_10seed}"
TRANSFER_GAP_DIAG_PREFIX="${TRANSFER_GAP_DIAG_PREFIX:-${ROOT}/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics}"
REVIEWER_AUDIT_PREFIX="${REVIEWER_AUDIT_PREFIX:-${ROOT}/docs/reviewer_quality_audit_2026-04-04_expanded_models_10seed}"
EXAMINER_TODO_PATH="${EXAMINER_TODO_PATH:-${ROOT}/docs/examiner_todo_2026-04-05_transfer_focus.md}"
TEMPORAL_ROBUST_PREFIX="${TEMPORAL_ROBUST_PREFIX:-${ROOT}/docs/temporal_robust_recommendation_2026-04-05_houston_10seed}"
OOT_THRESHOLD_POLICY_COMPARE_PREFIX="${OOT_THRESHOLD_POLICY_COMPARE_PREFIX:-${ROOT}/docs/out_of_time_threshold_policy_compare_2026-04-05_10seed}"
TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX="${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX:-${ROOT}/docs/transfer_policy_governance_lock_2026-04-05_10seed}"
HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX="${HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX:-${ROOT}/docs/houston_transfer_policy_compare_2026-04-05_10seed}"
HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX="${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX:-${ROOT}/docs/houston_transfer_policy_compare_all_models_2026-04-05_10seed}"
HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX="${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX:-${ROOT}/docs/houston_transfer_calibration_probe_2026-04-05_10seed}"
MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT="${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-05_transfer_model_scan_multisource_10seed}"
MULTISOURCE_TRANSFER_SUMMARY_PREFIX="${MULTISOURCE_TRANSFER_SUMMARY_PREFIX:-${ROOT}/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed}"
MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX="${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX:-${ROOT}/docs/multisource_transfer_governance_bridge_2026-04-05_10seed}"
TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX="${TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX:-${ROOT}/docs/transfer_override_seed_stress_test_2026-04-05_10seed}"
DATA_ALGORITHM_QUALITY_REVIEW_PREFIX="${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX:-${ROOT}/docs/data_algorithm_quality_review_2026-04-05_10seed}"
UNCERTAINTY_CONTOUR_OUTPUT_ROOT="${UNCERTAINTY_CONTOUR_OUTPUT_ROOT:-${ROOT}/outputs/2026-04-05_uncertainty_contour_panel_10seed}"
EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX="${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX:-${ROOT}/docs/external_validity_manuscript_assets_2026-04-05_10seed}"
LA_LB_2024_POOL_DIR="${LA_LB_2024_POOL_DIR:-${ROOT}/outputs/2026-04-05_r1_cross_year_2024_la_long_beach_pooled}"
LA_LB_TRANSFER_DIR="${LA_LB_TRANSFER_DIR:-${ROOT}/outputs/2026-04-05_r2_cross_year_la_long_beach_transfer}"
LA_LB_2023_EXT_POOL_DIR="${LA_LB_2023_EXT_POOL_DIR:-${ROOT}/outputs/2026-04-05_r14_true_new_area_la_long_beach_2023_expanded_pooled}"
NY_NJ_2023_EXT_POOL_DIR="${NY_NJ_2023_EXT_POOL_DIR:-${ROOT}/outputs/2026-04-05_r22_nynj_ext_overridepool_true_new_area_ny_nj_2023_extended_pooled}"
SAVANNAH_EXT_POOL_DIR="${SAVANNAH_EXT_POOL_DIR:-${ROOT}/outputs/2026-04-05_r27_true_new_area_savannah_ownship_focus_augmented_pooled}"

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
  "${UNSEEN_AREA_REPORT_PREFIX}.md"
  "${UNSEEN_AREA_REPORT_PREFIX}.json"
  "${UNSEEN_AREA_REPORT_PREFIX}_detail.csv"
  "${UNSEEN_AREA_REPORT_PREFIX}_summary.csv"
)
optional_files=(
  "${TRANSFER_GAP_DIAG_PREFIX}.md"
  "${TRANSFER_GAP_DIAG_PREFIX}.json"
  "${TRANSFER_GAP_DIAG_PREFIX}_detail.csv"
  "${TRANSFER_GAP_DIAG_PREFIX}_summary.csv"
  "${REVIEWER_AUDIT_PREFIX}.md"
  "${REVIEWER_AUDIT_PREFIX}.json"
  "${EXAMINER_TODO_PATH}"
  "${TEMPORAL_ROBUST_PREFIX}.md"
  "${TEMPORAL_ROBUST_PREFIX}.json"
  "${TEMPORAL_ROBUST_PREFIX}_detail.csv"
  "${TEMPORAL_ROBUST_PREFIX}_comparison.csv"
  "${TEMPORAL_ROBUST_PREFIX}_recommendation.csv"
  "${OOT_THRESHOLD_POLICY_COMPARE_PREFIX}.md"
  "${OOT_THRESHOLD_POLICY_COMPARE_PREFIX}.json"
  "${OOT_THRESHOLD_POLICY_COMPARE_PREFIX}_detail.csv"
  "${OOT_THRESHOLD_POLICY_COMPARE_PREFIX}_policy_summary.csv"
  "${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX}.md"
  "${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX}.json"
  "${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX}_policy_lock.csv"
  "${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX}_projected_transfer_check.csv"
  "${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX}_candidate_summary.csv"
  "${HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX}.md"
  "${HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX}.json"
  "${HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX}.csv"
  "${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX}.md"
  "${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX}.json"
  "${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX}.csv"
  "${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX}.md"
  "${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX}.json"
  "${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX}_detail.csv"
  "${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX}_model_method_summary.csv"
  "${MULTISOURCE_TRANSFER_SUMMARY_PREFIX}.md"
  "${MULTISOURCE_TRANSFER_SUMMARY_PREFIX}.json"
  "${MULTISOURCE_TRANSFER_SUMMARY_PREFIX}_detail.csv"
  "${MULTISOURCE_TRANSFER_SUMMARY_PREFIX}_source_summary.csv"
  "${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX}.md"
  "${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX}.json"
  "${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX}_detail.csv"
  "${TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX}.md"
  "${TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX}.json"
  "${TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX}_per_seed.csv"
  "${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX}.md"
  "${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX}.json"
  "${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX}_dataset_scorecard.csv"
  "${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX}_high_risk_models.csv"
  "${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX}_todo.csv"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan.md"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan.json"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan_detail.csv"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan_model_summary.csv"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/nola_transfer_model_scan.md"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/nola_transfer_model_scan.json"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/nola_transfer_model_scan_detail.csv"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/nola_transfer_model_scan_model_summary.csv"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/seattle_transfer_model_scan.md"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/seattle_transfer_model_scan.json"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/seattle_transfer_model_scan_detail.csv"
  "${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}/seattle_transfer_model_scan_model_summary.csv"
  "${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}.md"
  "${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}.json"
  "${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}_transfer_uncertainty_table.csv"
  "${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}_transfer_uncertainty_table.md"
  "${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}_scenario_panels.csv"
  "${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}_scenario_panels.md"
  "${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/houston_report_figure.svg"
  "${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/nola_report_figure.svg"
  "${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/seattle_report_figure.svg"
  "${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/houston_report_summary.json"
  "${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/nola_report_summary.json"
  "${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}/seattle_report_summary.json"
  "${MANUSCRIPT_FREEZE_PACKET_PREFIX}.md"
  "${MANUSCRIPT_FREEZE_PACKET_PREFIX}.json"
  "${MANUSCRIPT_FREEZE_PACKET_PREFIX}_operator_profile_lock.csv"
  "${MANUSCRIPT_FREEZE_PACKET_PREFIX}_model_claim_scope.csv"
  "${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan.md"
  "${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan.json"
  "${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan_detail.csv"
  "${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}/houston_transfer_model_scan_model_summary.csv"
  "${LA_LB_2023_EXT_POOL_DIR}/la_long_beach_2023_expanded_pooled_pairwise_summary.json"
  "${NY_NJ_2023_EXT_POOL_DIR}/ny_nj_2023_extended_pooled_pairwise_summary.json"
  "${SAVANNAH_EXT_POOL_DIR}/savannah_ownship_focus_augmented_pooled_pairwise_summary.json"
  "${LA_LB_2024_POOL_DIR}/la_long_beach_2024_pooled_pairwise_summary.json"
  "${LA_LB_TRANSFER_DIR}/la_long_beach_2023_to_2024_transfer_summary.json"
  "${LA_LB_TRANSFER_DIR}/la_long_beach_2024_to_2023_transfer_summary.json"
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
copied_optional_files=()
for file_path in "${optional_files[@]}"; do
  if [[ -f "${file_path}" ]]; then
    cp "${file_path}" "${DEST_DIR}/"
    copied_optional_files+=("$(basename "${file_path}")")
  fi
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
  --source-dir "unseen_area_report=$(dirname "${UNSEEN_AREA_REPORT_PREFIX}")"
  --source-dir "reviewer_audit=$(dirname "${REVIEWER_AUDIT_PREFIX}")"
  --source-dir "temporal_robust=$(dirname "${TEMPORAL_ROBUST_PREFIX}")"
  --source-dir "out_of_time_threshold_policy_compare=$(dirname "${OOT_THRESHOLD_POLICY_COMPARE_PREFIX}")"
  --source-dir "transfer_policy_governance_lock=$(dirname "${TRANSFER_POLICY_GOVERNANCE_LOCK_PREFIX}")"
  --source-dir "houston_transfer_policy_compare=$(dirname "${HOUSTON_TRANSFER_POLICY_COMPARE_PREFIX}")"
  --source-dir "houston_transfer_policy_compare_all_models=$(dirname "${HOUSTON_TRANSFER_POLICY_COMPARE_ALL_MODELS_PREFIX}")"
  --source-dir "houston_transfer_calibration_probe=$(dirname "${HOUSTON_TRANSFER_CALIBRATION_PROBE_PREFIX}")"
  --source-dir "multisource_transfer_scan_summary=$(dirname "${MULTISOURCE_TRANSFER_SUMMARY_PREFIX}")"
  --source-dir "multisource_transfer_governance_bridge=$(dirname "${MULTISOURCE_TRANSFER_GOVERNANCE_BRIDGE_PREFIX}")"
  --source-dir "transfer_override_seed_stress_test=$(dirname "${TRANSFER_OVERRIDE_SEED_STRESS_TEST_PREFIX}")"
  --source-dir "data_algorithm_quality_review=$(dirname "${DATA_ALGORITHM_QUALITY_REVIEW_PREFIX}")"
  --source-dir "multisource_transfer_scan=${MULTISOURCE_TRANSFER_SCAN_OUTPUT_ROOT}"
  --source-dir "uncertainty_contour=${UNCERTAINTY_CONTOUR_OUTPUT_ROOT}"
  --source-dir "external_validity_assets=$(dirname "${EXTERNAL_VALIDITY_MANUSCRIPT_ASSETS_PREFIX}")"
  --source-dir "transfer_gap_diagnostics=$(dirname "${TRANSFER_GAP_DIAG_PREFIX}")"
  --source-dir "manuscript_freeze_packet=$(dirname "${MANUSCRIPT_FREEZE_PACKET_PREFIX}")"
  --source-dir "transfer_model_scan=${TRANSFER_MODEL_SCAN_OUTPUT_ROOT}"
  --source-dir "la_lb_2023_expanded_pool=${LA_LB_2023_EXT_POOL_DIR}"
  --source-dir "ny_nj_2023_ext_pool=${NY_NJ_2023_EXT_POOL_DIR}"
  --source-dir "savannah_ext_pool=${SAVANNAH_EXT_POOL_DIR}"
  --source-dir "la_lb_2024_pool=${LA_LB_2024_POOL_DIR}"
  --source-dir "la_lb_transfer=${LA_LB_TRANSFER_DIR}"
  --manifest-txt "${DEST_DIR}/bundle_manifest_${MANIFEST_DATE_TAG}.txt"
  --manifest-json "${DEST_DIR}/bundle_manifest_${MANIFEST_DATE_TAG}.json"
)

for file_path in "${required_files[@]}"; do
  manifest_args+=(--copied-file "$(basename "${file_path}")")
done
for file_name in "${copied_optional_files[@]}"; do
  manifest_args+=(--copied-file "${file_name}")
done
for file_path in "${input_files[@]}"; do
  manifest_args+=(--input-file "${file_path}")
done
if ((${#command_logs_for_manifest[@]} > 0)); then
  for file_path in "${command_logs_for_manifest[@]}"; do
    manifest_args+=(--command-log "${file_path}")
  done
fi

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.bundle_manifest_cli "${manifest_args[@]}"
)

MANIFEST_PATH="${DEST_DIR}/bundle_manifest_${MANIFEST_DATE_TAG}.txt"
MANIFEST_JSON_PATH="${DEST_DIR}/bundle_manifest_${MANIFEST_DATE_TAG}.json"

echo "exported_dir=${DEST_DIR}"
echo "manifest=${MANIFEST_PATH}"
echo "manifest_json=${MANIFEST_JSON_PATH}"
