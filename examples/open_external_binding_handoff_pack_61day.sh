#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_ROOT="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"
PACK="$OUT_ROOT/external_binding_handoff_pack_61day"

echo "External binding handoff pack:"
echo "  $PACK"
echo
echo "Key files:"
echo "  $PACK/EXTERNAL_BINDING_HANDOFF_MANIFEST_61day.md"
echo "  $PACK/external_binding_minimal_sheet_61day.md"
echo "  $PACK/external_dependency_ledger_61day.md"
echo "  $PACK/target_venue_intake_sheet_61day.md"
echo "  $PACK/venue_specific_final_formatting_readiness_61day.md"
echo "  $PACK/final_operator_runbook_61day.md"
echo "  $PACK/submission_release_operator_latest_61day.md"
echo "  $PACK/submission_release_snapshot_verify_latest_61day.md"
echo "  $PACK/submission_metadata_real_value_gate_61day.md"
echo
echo "Key scripts:"
echo "  $PACK/scripts/open_external_binding_minimal_61day.sh"
echo "  $PACK/scripts/run_canonical_preflight_61day.sh"
echo "  $PACK/scripts/run_venue_pair_preflight_61day.sh"
echo "  $PACK/scripts/run_submission_release_operator_61day.sh"
echo "  $PACK/scripts/run_submission_release_regression_suite_61day.sh"
echo "  $PACK/scripts/run_submission_release_control_tower_61day.sh"
echo "  $PACK/scripts/build_submission_release_control_tower_61day.py"
echo "  $PACK/scripts/run_submission_metadata_real_value_gate_61day.sh"
echo "  $PACK/scripts/audit_submission_metadata_real_value_61day.py"
echo "  $PACK/scripts/verify_external_binding_handoff_pack_61day.sh"
