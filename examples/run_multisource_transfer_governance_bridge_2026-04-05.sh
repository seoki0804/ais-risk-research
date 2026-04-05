#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MULTISOURCE_SOURCE_SUMMARY_CSV="${MULTISOURCE_SOURCE_SUMMARY_CSV:-${ROOT}/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed_source_summary.csv}"
TRANSFER_POLICY_GOVERNANCE_LOCK_JSON="${TRANSFER_POLICY_GOVERNANCE_LOCK_JSON:-${ROOT}/docs/transfer_policy_governance_lock_2026-04-05_10seed.json}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-${ROOT}/docs/multisource_transfer_governance_bridge_2026-04-05_10seed}"

(
  cd "${ROOT}"
  env PYTHONPATH=src python -m ais_risk.multisource_transfer_governance_bridge_cli \
    --multisource-source-summary-csv "${MULTISOURCE_SOURCE_SUMMARY_CSV}" \
    --transfer-policy-governance-lock-json "${TRANSFER_POLICY_GOVERNANCE_LOCK_JSON}" \
    --output-prefix "${OUTPUT_PREFIX}"
)

echo "summary_md=${OUTPUT_PREFIX}.md"
echo "summary_json=${OUTPUT_PREFIX}.json"
echo "detail_csv=${OUTPUT_PREFIX}_detail.csv"

