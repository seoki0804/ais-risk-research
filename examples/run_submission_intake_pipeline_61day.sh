#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"
INPUT_PATH="${1:-$ROOT/submission_intake_template_61day.json}"

python3 /Users/seoki/Desktop/research/examples/validate_submission_intake_61day.py \
  --input "$INPUT_PATH" \
  --output "$ROOT/submission_intake_validation_61day.md"

python3 /Users/seoki/Desktop/research/examples/render_submission_intake_61day.py \
  --input "$INPUT_PATH" \
  --output-json "$ROOT/submission_portal_metadata_filled_61day.json" \
  --output-md "$ROOT/submission_intake_handoff_61day.md"

echo "Submission intake pipeline complete."
echo "Input: $INPUT_PATH"
echo "Validation: $ROOT/submission_intake_validation_61day.md"
echo "Rendered JSON: $ROOT/submission_portal_metadata_filled_61day.json"
echo "Handoff note: $ROOT/submission_intake_handoff_61day.md"
echo "Copy-paste note: $ROOT/submission_portal_copy_paste_filled_61day.md"
echo "Fill queue note: $ROOT/submission_intake_fill_queue_61day.md"
