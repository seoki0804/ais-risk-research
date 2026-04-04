#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-${ROOT}/docs/true_unseen_area_evidence_report_2026-04-04_expanded_models_10seed}"

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.unseen_area_evidence_report_cli \
    --output-prefix "${OUTPUT_PREFIX}" \
    --min-test-positive-support 10 \
    --target-model hgbt \
    --comparator-model logreg
)

echo "detail_csv=${OUTPUT_PREFIX}_detail.csv"
echo "summary_csv=${OUTPUT_PREFIX}_summary.csv"
echo "summary_md=${OUTPUT_PREFIX}.md"
echo "summary_json=${OUTPUT_PREFIX}.json"
