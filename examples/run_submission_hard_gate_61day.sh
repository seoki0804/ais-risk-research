#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"
PACKET_DIR="$ROOT/venue_packets/applied_conf_default_blind_61day"
OUT="$ROOT/submission_hard_gate_61day.md"
REAL_VALUE_GATE="$ROOT/submission_metadata_real_value_gate_61day.md"

ALLOW_PROVISIONAL_VALUES=0
if [[ "${1:-}" == "--allow-provisional-values" ]]; then
  ALLOW_PROVISIONAL_VALUES=1
  shift
fi

if [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--allow-provisional-values]" >&2
  exit 2
fi

bash /Users/seoki/Desktop/research/examples/run_completion_scorecard_61day.sh

EXTRA_ARGS=()
if [[ "$ALLOW_PROVISIONAL_VALUES" -eq 1 ]]; then
  EXTRA_ARGS+=(--allow-provisional-values)
fi

python3 /Users/seoki/Desktop/research/examples/assess_submission_hard_gate_61day.py \
  --root "$ROOT" \
  --packet-dir "$PACKET_DIR" \
  --real-value-gate "$REAL_VALUE_GATE" \
  --output "$OUT" \
  ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}

echo "Submission hard gate refreshed:"
echo "  $OUT"
