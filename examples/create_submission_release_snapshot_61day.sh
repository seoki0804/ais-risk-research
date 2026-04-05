#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"
SNAP_ROOT="$ROOT/submission_release_snapshots_61day"
LOCK_DIR="$SNAP_ROOT/.snapshot_lock_61day"

SKIP_PREFLIGHT=false
PREFLIGHT_STATUS="SKIPPED_BY_FLAG"
if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [--skip-preflight]" >&2
  exit 2
fi

if [[ $# -eq 1 ]]; then
  if [[ "$1" == "--skip-preflight" ]]; then
    SKIP_PREFLIGHT=true
  else
    echo "Usage: $0 [--skip-preflight]" >&2
    exit 2
  fi
fi

if [[ "$SKIP_PREFLIGHT" == "false" ]]; then
  bash /Users/seoki/Desktop/research/examples/run_submission_final_preflight_61day.sh
  PREFLIGHT_STATUS="PASS_CONFIRMED"
fi

mkdir -p "$SNAP_ROOT"

wait_count=0
while ! mkdir "$LOCK_DIR" 2>/dev/null; do
  sleep 0.2
  wait_count=$((wait_count + 1))
  if [[ "$wait_count" -ge 600 ]]; then
    echo "Timeout waiting for snapshot lock: $LOCK_DIR" >&2
    exit 1
  fi
done

release_lock() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap release_lock EXIT

TS="$(date '+%Y%m%d_%H%M%S')"
while [[ -e "$SNAP_ROOT/$TS" || -e "$SNAP_ROOT/$TS.zip" ]]; do
  sleep 1
  TS="$(date '+%Y%m%d_%H%M%S')"
done

SNAP_DIR="$SNAP_ROOT/$TS"
MANIFEST="$SNAP_DIR/SNAPSHOT_MANIFEST_61day.md"
mkdir "$SNAP_DIR"

FILES=(
  "$ROOT/submission_intake_template_61day.json"
  "$ROOT/submission_portal_metadata_filled_61day.json"
  "$ROOT/submission_portal_copy_paste_filled_61day.md"
  "$ROOT/submission_intake_handoff_61day.md"
  "$ROOT/submission_intake_validation_61day.md"
  "$ROOT/submission_completion_scorecard_61day.md"
  "$ROOT/claim_consistency_audit_61day.md"
  "$ROOT/submission_hard_gate_61day.md"
  "$ROOT/submission_readiness_certificate_61day.md"
  "$ROOT/submission_metadata_strict_audit_61day.md"
  "$ROOT/venue_packets/applied_conf_default_blind_61day/manuscript_bundle_61day/paper_blind_bound_61day.pdf"
  "$ROOT/venue_packets/applied_conf_default_camera-ready_61day/manuscript_bundle_61day/paper_camera-ready_bound_61day.pdf"
)

for src in "${FILES[@]}"; do
  if [[ ! -f "$src" ]]; then
    echo "Missing required snapshot file: $src" >&2
    exit 1
  fi
  cp "$src" "$SNAP_DIR/"
done

{
  echo "# Submission Release Snapshot 61day"
  echo
  echo "- Generated: \`$(date '+%Y-%m-%dT%H:%M:%S%z')\`"
  echo "- Snapshot directory: \`$SNAP_DIR\`"
  echo "- Source root: \`$ROOT\`"
  echo
  echo "## Included Files (SHA256)"
  for src in "${FILES[@]}"; do
    name="$(basename "$src")"
    hash="$(shasum -a 256 "$SNAP_DIR/$name" | awk '{print $1}')"
    echo "- \`$name\`: \`$hash\`"
    echo "  - source: \`$src\`"
  done
  echo
  echo "## Preflight Requirement"
  if [[ "$PREFLIGHT_STATUS" == "PASS_CONFIRMED" ]]; then
    echo "- \`run_submission_final_preflight_61day.sh\` returned \`Overall status: PASS\` before snapshot copy."
  else
    echo "- Preflight was skipped via \`--skip-preflight\`; caller must ensure \`run_submission_final_preflight_61day.sh\` already passed."
  fi
} > "$MANIFEST"

(
  cd "$SNAP_ROOT"
  zip -rq "${TS}.zip" "$TS"
)

echo "Submission release snapshot created:"
echo "  directory: $SNAP_DIR"
echo "  manifest:  $MANIFEST"
echo "  zip:       $SNAP_ROOT/${TS}.zip"
