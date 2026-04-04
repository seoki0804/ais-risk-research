#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-${ROOT}/docs/reviewer_quality_audit_2026-04-04_expanded_models_10seed}"

(
  cd "${ROOT}"
  PYTHONPATH=src python -m ais_risk.reviewer_quality_audit_cli \
    --output-prefix "${OUTPUT_PREFIX}"
)

echo "summary_md=${OUTPUT_PREFIX}.md"
echo "summary_json=${OUTPUT_PREFIX}.json"
