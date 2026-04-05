#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"
OUT="$ROOT/submission_readiness_certificate_61day.md"

bash /Users/seoki/Desktop/research/examples/run_submission_hard_gate_61day.sh

python3 /Users/seoki/Desktop/research/examples/generate_submission_readiness_certificate_61day.py \
  --root "$ROOT" \
  --output "$OUT"

echo "Submission readiness certificate refreshed:"
echo "  $OUT"
