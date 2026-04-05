#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 <venue_name> <venue_round_or_deadline> [--dry-run]" >&2
  exit 2
fi

VENUE_NAME="$1"
VENUE_ROUND="$2"
DRY_RUN_FLAG="${3:-}"

EXTRA_ARGS=()
if [[ -n "$DRY_RUN_FLAG" ]]; then
  if [[ "$DRY_RUN_FLAG" != "--dry-run" ]]; then
    echo "Usage: $0 <venue_name> <venue_round_or_deadline> [--dry-run]" >&2
    exit 2
  fi
  EXTRA_ARGS+=(--dry-run)
fi

python3 /Users/seoki/Desktop/research/examples/apply_submission_real_value_binding_61day.py \
  --venue-name "$VENUE_NAME" \
  --venue-round "$VENUE_ROUND" \
  ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}

if [[ "$DRY_RUN_FLAG" == "--dry-run" ]]; then
  echo
  echo "Dry-run complete."
  exit 0
fi

echo
echo "Re-running real-value gate after binding updates..."
if bash /Users/seoki/Desktop/research/examples/run_submission_metadata_real_value_gate_61day.sh; then
  echo "Real-value gate: PASS"
else
  echo "Real-value gate: HOLD (check report for remaining blockers)"
fi

echo
echo "Report:"
echo "  /Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/submission_metadata_real_value_gate_61day.md"
