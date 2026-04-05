#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OPEN_PACK="$ROOT/examples/open_external_binding_handoff_pack_61day.sh"
VERIFY_PACK="$ROOT/examples/verify_external_binding_handoff_pack_61day.sh"

echo "Opening external binding handoff pack..."
echo
bash "$OPEN_PACK"
echo
echo "Verifying external binding handoff pack..."
echo
bash "$VERIFY_PACK"
echo
echo "Recommended next steps:"
echo "  1. Read external_binding_minimal_sheet_61day.md"
echo "  2. Fill the minimal external inputs"
echo "  3. Run run_canonical_preflight_61day.sh or run_venue_pair_preflight_61day.sh"
echo "  4. Run run_submission_release_operator_61day.sh for final lock and evidence"
echo "  5. Confirm submission_release_operator_latest_61day.md and submission_release_snapshot_verify_latest_61day.md"
echo "  6. Run run_submission_release_regression_suite_61day.sh for end-to-end regression proof"
echo "  7. Run run_submission_release_control_tower_61day.sh for one-page status board"
echo "  8. Run run_submission_metadata_real_value_gate_61day.sh for final venue-value completion gate"
