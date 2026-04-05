#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"

python3 /Users/seoki/Desktop/research/examples/validate_submission_intake_61day.py \
  --input "$ROOT/submission_intake_template_61day.json" \
  --output "$ROOT/submission_intake_validation_61day.md"

python3 /Users/seoki/Desktop/research/examples/audit_claim_consistency_61day.py \
  --root "$ROOT" \
  --output "$ROOT/claim_consistency_audit_61day.md"

if bash /Users/seoki/Desktop/research/examples/run_submission_metadata_real_value_gate_61day.sh; then
  echo "Real-value gate refreshed: PASS"
else
  echo "Real-value gate refreshed: HOLD (continuing to keep scorecard/hard-gate reports updated)"
fi

python3 /Users/seoki/Desktop/research/examples/build_completion_scorecard_61day.py \
  --root "$ROOT" \
  --validation "$ROOT/submission_intake_validation_61day.md" \
  --blocker "$ROOT/submission_blocker_sheet_61day.md" \
  --consistency-audit "$ROOT/claim_consistency_audit_61day.md" \
  --real-value-gate "$ROOT/submission_metadata_real_value_gate_61day.md" \
  --output "$ROOT/submission_completion_scorecard_61day.md"

echo "Completion scorecard refreshed:"
echo "  $ROOT/submission_completion_scorecard_61day.md"
echo "Claim consistency audit:"
echo "  $ROOT/claim_consistency_audit_61day.md"
