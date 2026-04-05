#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_ROOT="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"
PACK="$OUT_ROOT/external_binding_handoff_pack_61day"
ZIP="$OUT_ROOT/external_binding_handoff_pack_61day.zip"
CHECKSUM="$PACK/EXTERNAL_BINDING_HANDOFF_CHECKSUMS_61day.txt"

DOCS=(
  "external_binding_minimal_sheet_61day.md"
  "external_dependency_ledger_61day.md"
  "target_venue_intake_sheet_61day.md"
  "venue_specific_final_formatting_readiness_61day.md"
  "final_operator_runbook_61day.md"
  "canonical_outgoing_packet_61day.md"
  "recommended_submission_lane_61day.md"
  "canonical_preflight_note_61day.md"
  "submission_release_operator_latest_61day.md"
  "submission_release_snapshot_verify_latest_61day.md"
  "submission_metadata_real_value_gate_61day.md"
  "submission_strict_real_value_todo_61day.md"
)

SCRIPTS=(
  "open_external_binding_handoff_pack_61day.sh"
  "open_external_binding_minimal_61day.sh"
  "open_canonical_outgoing_packet_61day.sh"
  "run_canonical_preflight_61day.sh"
  "run_venue_pair_preflight_61day.sh"
  "run_submission_release_operator_61day.sh"
  "run_submission_release_regression_suite_61day.sh"
  "run_submission_release_control_tower_61day.sh"
  "build_submission_release_control_tower_61day.py"
  "run_submission_metadata_real_value_gate_61day.sh"
  "audit_submission_metadata_real_value_61day.py"
  "apply_submission_real_value_binding_61day.py"
  "run_apply_submission_real_value_binding_61day.sh"
  "run_strict_real_value_closure_61day.sh"
  "verify_external_binding_handoff_pack_61day.sh"
  "start_external_binding_handoff_pack_61day.sh"
)

CHECKSUM_TARGETS=(
  "EXTERNAL_BINDING_HANDOFF_MANIFEST_61day.md"
  "RUN_ME_FIRST_61day.md"
  "START_HERE_61day.sh"
  "VERIFY_PACK_61day.sh"
  "external_binding_minimal_sheet_61day.md"
  "external_dependency_ledger_61day.md"
  "target_venue_intake_sheet_61day.md"
  "venue_specific_final_formatting_readiness_61day.md"
  "final_operator_runbook_61day.md"
  "canonical_outgoing_packet_61day.md"
  "recommended_submission_lane_61day.md"
  "canonical_preflight_note_61day.md"
  "submission_release_operator_latest_61day.md"
  "submission_release_snapshot_verify_latest_61day.md"
  "submission_metadata_real_value_gate_61day.md"
  "submission_strict_real_value_todo_61day.md"
  "scripts/open_external_binding_handoff_pack_61day.sh"
  "scripts/open_external_binding_minimal_61day.sh"
  "scripts/open_canonical_outgoing_packet_61day.sh"
  "scripts/run_canonical_preflight_61day.sh"
  "scripts/run_venue_pair_preflight_61day.sh"
  "scripts/run_submission_release_operator_61day.sh"
  "scripts/run_submission_release_regression_suite_61day.sh"
  "scripts/run_submission_release_control_tower_61day.sh"
  "scripts/build_submission_release_control_tower_61day.py"
  "scripts/run_submission_metadata_real_value_gate_61day.sh"
  "scripts/audit_submission_metadata_real_value_61day.py"
  "scripts/apply_submission_real_value_binding_61day.py"
  "scripts/run_apply_submission_real_value_binding_61day.sh"
  "scripts/run_strict_real_value_closure_61day.sh"
  "scripts/verify_external_binding_handoff_pack_61day.sh"
  "scripts/start_external_binding_handoff_pack_61day.sh"
)

if [[ ! -d "$PACK" ]]; then
  echo "Pack directory not found: $PACK" >&2
  exit 1
fi

# Keep the real-value gate report fresh for handoff visibility.
real_value_refresh_status="HOLD"
if bash "$ROOT/examples/run_submission_metadata_real_value_gate_61day.sh"; then
  real_value_refresh_status="PASS"
fi
echo "Real-value gate refresh status: $real_value_refresh_status"

# Refresh objective evidence before packaging.
bash "$ROOT/examples/run_submission_release_operator_61day.sh" --strict-source-match

for name in "${DOCS[@]}"; do
  src="$OUT_ROOT/$name"
  dst="$PACK/$name"
  if [[ ! -f "$src" ]]; then
    echo "Missing source document: $src" >&2
    exit 1
  fi
  cp "$src" "$dst"
done

for name in "${SCRIPTS[@]}"; do
  src="$ROOT/examples/$name"
  dst="$PACK/scripts/$name"
  if [[ ! -f "$src" ]]; then
    echo "Missing source script: $src" >&2
    exit 1
  fi
  cp "$src" "$dst"
  chmod +x "$dst"
done

for rel in "${CHECKSUM_TARGETS[@]}"; do
  path="$PACK/$rel"
  if [[ ! -e "$path" ]]; then
    echo "Missing checksum target: $path" >&2
    exit 1
  fi
done

tmp="$(mktemp)"
(
  cd "$PACK"
  : > "$tmp"
  for rel in "${CHECKSUM_TARGETS[@]}"; do
    shasum -a 256 "./$rel" >> "$tmp"
  done
)
mv "$tmp" "$CHECKSUM"

(
  cd "$OUT_ROOT"
  rm -f "$(basename "$ZIP")"
  zip -rq "$(basename "$ZIP")" "$(basename "$PACK")"
)

bash "$ROOT/examples/verify_external_binding_handoff_pack_61day.sh"

echo "External binding handoff pack refreshed:"
echo "  pack: $PACK"
echo "  checksums: $CHECKSUM"
echo "  zip: $ZIP"
