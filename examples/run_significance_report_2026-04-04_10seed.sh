#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-${ROOT}/docs/significance_report_2026-04-04_expanded_models_10seed}"

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.significance_report_cli \
    --output-prefix "${OUTPUT_PREFIX}" \
    --bootstrap-samples 5000 \
    --bootstrap-seed 42 \
    --min-pairs 5
)

echo "csv=${OUTPUT_PREFIX}.csv"
echo "md=${OUTPUT_PREFIX}.md"
echo "json=${OUTPUT_PREFIX}.json"
