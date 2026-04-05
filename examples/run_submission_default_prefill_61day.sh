#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"
INPUT_PATH="${1:-$ROOT/submission_intake_template_61day.json}"

python3 /Users/seoki/Desktop/research/examples/apply_default_submission_intake_61day.py \
  --input "$INPUT_PATH"

bash /Users/seoki/Desktop/research/examples/run_submission_intake_pipeline_61day.sh \
  "$INPUT_PATH"

bash /Users/seoki/Desktop/research/examples/run_submission_hard_gate_61day.sh

echo "Default prefill + hard gate refresh completed."
echo "Check:"
echo "  $ROOT/submission_intake_validation_61day.md"
echo "  $ROOT/submission_completion_scorecard_61day.md"
echo "  $ROOT/submission_hard_gate_61day.md"
