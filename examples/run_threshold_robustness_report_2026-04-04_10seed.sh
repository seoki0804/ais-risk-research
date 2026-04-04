#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-${ROOT}/docs/threshold_robustness_report_2026-04-04_expanded_models_10seed}"

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.threshold_robustness_report_cli \
    --output-prefix "${OUTPUT_PREFIX}" \
    --cost-profiles "balanced:1:1,fn_heavy:1:3,fn_very_heavy:1:5,fp_heavy:3:1"
)

echo "summary_md=${OUTPUT_PREFIX}.md"
echo "summary_json=${OUTPUT_PREFIX}.json"
echo "detail_csv=${OUTPUT_PREFIX}_detail.csv"
echo "summary_csv=${OUTPUT_PREFIX}_summary.csv"
