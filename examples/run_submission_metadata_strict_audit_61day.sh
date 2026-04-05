#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"

bash /Users/seoki/Desktop/research/examples/run_submission_intake_pipeline_61day.sh \
  "$ROOT/submission_intake_template_61day.json"

python3 /Users/seoki/Desktop/research/examples/audit_submission_metadata_strict_61day.py \
  --input "$ROOT/submission_portal_metadata_filled_61day.json" \
  --output "$ROOT/submission_metadata_strict_audit_61day.md"

echo "Submission metadata strict audit refreshed:"
echo "  $ROOT/submission_metadata_strict_audit_61day.md"
