#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"

cat <<EOF
Final operator runbook:
  $ROOT/final_operator_runbook_61day.md

Recommended lane:
  $ROOT/recommended_submission_lane_61day.md

Canonical outgoing packet:
  $ROOT/canonical_outgoing_packet_61day.md

Internal release sign-off:
  $ROOT/internal_release_signoff_61day.md
EOF
