#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${DEST_DIR:-${ROOT}/docs/results/2026-04-04-expanded}"

MULTI_DIR="${ROOT}/outputs/2026-04-04_all_models_multiarea_expanded"
SWEEP_DIR="${ROOT}/outputs/2026-04-04_all_models_seed_sweep_expanded"
OOT_DIR="${ROOT}/outputs/2026-04-04_out_of_time_check"
TRANSFER_DIR="${ROOT}/outputs/2026-04-04_transfer_check"

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

MANIFEST_PATH="${DEST_DIR}/bundle_manifest_2026-04-04-expanded.txt"
{
  echo "bundle_date=2026-04-04-expanded"
  echo "source_multiarea_dir=${MULTI_DIR}"
  echo "source_seed_sweep_dir=${SWEEP_DIR}"
  echo "source_out_of_time_dir=${OOT_DIR}"
  echo "source_transfer_dir=${TRANSFER_DIR}"
  echo "copied_files="
  for file_path in "${required_files[@]}"; do
    echo "  - $(basename "${file_path}")"
  done
} > "${MANIFEST_PATH}"

echo "exported_dir=${DEST_DIR}"
echo "manifest=${MANIFEST_PATH}"
