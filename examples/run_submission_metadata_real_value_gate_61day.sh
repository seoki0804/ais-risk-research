#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"

bash /Users/seoki/Desktop/research/examples/run_submission_intake_pipeline_61day.sh \
  "$ROOT/submission_intake_template_61day.json"

python3 /Users/seoki/Desktop/research/examples/audit_submission_metadata_real_value_61day.py \
  --input "$ROOT/submission_portal_metadata_filled_61day.json" \
  --output "$ROOT/submission_metadata_real_value_gate_61day.md" \
  --tex "$ROOT/paper_conference_8page_asset_locked_61day.tex" \
  --tex "$ROOT/venue_packets/applied_conf_default_camera-ready_61day/manuscript_bundle_61day/paper_camera-ready_bound_61day.tex"

echo "Submission metadata real-value gate refreshed:"
echo "  $ROOT/submission_metadata_real_value_gate_61day.md"
