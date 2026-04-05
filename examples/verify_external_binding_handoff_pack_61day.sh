#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_ROOT="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"
PACK="$OUT_ROOT/external_binding_handoff_pack_61day"
ZIP="$OUT_ROOT/external_binding_handoff_pack_61day.zip"
CHECKSUM="$PACK/EXTERNAL_BINDING_HANDOFF_CHECKSUMS_61day.txt"
OPERATOR_REPORT="$PACK/submission_release_operator_latest_61day.md"
SNAPSHOT_REPORT="$PACK/submission_release_snapshot_verify_latest_61day.md"

required_files=(
  "$PACK/EXTERNAL_BINDING_HANDOFF_MANIFEST_61day.md"
  "$PACK/RUN_ME_FIRST_61day.md"
  "$PACK/START_HERE_61day.sh"
  "$PACK/VERIFY_PACK_61day.sh"
  "$PACK/external_binding_minimal_sheet_61day.md"
  "$PACK/external_dependency_ledger_61day.md"
  "$PACK/target_venue_intake_sheet_61day.md"
  "$PACK/venue_specific_final_formatting_readiness_61day.md"
  "$PACK/final_operator_runbook_61day.md"
  "$PACK/canonical_outgoing_packet_61day.md"
  "$PACK/recommended_submission_lane_61day.md"
  "$PACK/canonical_preflight_note_61day.md"
  "$OPERATOR_REPORT"
  "$SNAPSHOT_REPORT"
  "$PACK/submission_metadata_real_value_gate_61day.md"
  "$PACK/submission_strict_real_value_todo_61day.md"
  "$PACK/scripts/open_external_binding_minimal_61day.sh"
  "$PACK/scripts/open_external_binding_handoff_pack_61day.sh"
  "$PACK/scripts/open_canonical_outgoing_packet_61day.sh"
  "$PACK/scripts/run_canonical_preflight_61day.sh"
  "$PACK/scripts/run_venue_pair_preflight_61day.sh"
  "$PACK/scripts/run_submission_release_operator_61day.sh"
  "$PACK/scripts/run_submission_release_regression_suite_61day.sh"
  "$PACK/scripts/run_submission_release_control_tower_61day.sh"
  "$PACK/scripts/build_submission_release_control_tower_61day.py"
  "$PACK/scripts/run_submission_metadata_real_value_gate_61day.sh"
  "$PACK/scripts/audit_submission_metadata_real_value_61day.py"
  "$PACK/scripts/apply_submission_real_value_binding_61day.py"
  "$PACK/scripts/run_apply_submission_real_value_binding_61day.sh"
  "$PACK/scripts/run_strict_real_value_closure_61day.sh"
  "$PACK/scripts/verify_external_binding_handoff_pack_61day.sh"
  "$CHECKSUM"
)

missing=0

for path in "${required_files[@]}"; do
  if [[ ! -e "$path" ]]; then
    echo "Missing: $path" >&2
    missing=1
  fi
done

if [[ ! -f "$ZIP" ]]; then
  echo "Missing zip: $ZIP" >&2
  missing=1
fi

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

(
  cd "$PACK"
  shasum -a 256 -c "$(basename "$CHECKSUM")"
)

operator_overall="$(sed -n 's/^- Overall status: `\([^`]*\)`/\1/p' "$OPERATOR_REPORT" | head -n 1)"
snapshot_integrity="$(sed -n 's/^- Snapshot integrity: `\([^`]*\)`/\1/p' "$SNAPSHOT_REPORT" | head -n 1)"
snapshot_drift="$(sed -n 's/^- Source drift check: `\([^`]*\)`/\1/p' "$SNAPSHOT_REPORT" | head -n 1)"
snapshot_overall="$(sed -n 's/^- Overall status: `\([^`]*\)`/\1/p' "$SNAPSHOT_REPORT" | head -n 1)"

evidence_fail=0
if [[ "${operator_overall:-}" != "PASS" ]]; then
  echo "Evidence status mismatch: operator overall is '${operator_overall:-UNKNOWN}' (expected PASS)" >&2
  evidence_fail=1
fi
if [[ "${snapshot_integrity:-}" != "PASS" ]]; then
  echo "Evidence status mismatch: snapshot integrity is '${snapshot_integrity:-UNKNOWN}' (expected PASS)" >&2
  evidence_fail=1
fi
if [[ "${snapshot_drift:-}" != "MATCH" ]]; then
  echo "Evidence status mismatch: source drift is '${snapshot_drift:-UNKNOWN}' (expected MATCH)" >&2
  evidence_fail=1
fi
if [[ "${snapshot_overall:-}" != "PASS" ]]; then
  echo "Evidence status mismatch: snapshot overall is '${snapshot_overall:-UNKNOWN}' (expected PASS)" >&2
  evidence_fail=1
fi

if [[ "$evidence_fail" -ne 0 ]]; then
  exit 1
fi

echo "External binding handoff pack verified:"
echo "  $PACK"
echo "Zip:"
echo "  $ZIP"
echo "Checksums:"
echo "  $CHECKSUM"
echo "Evidence status:"
echo "  operator_overall: $operator_overall"
echo "  snapshot_integrity: $snapshot_integrity"
echo "  snapshot_drift: $snapshot_drift"
echo "  snapshot_overall: $snapshot_overall"
