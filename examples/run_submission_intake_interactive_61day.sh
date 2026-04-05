#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"
INPUT_PATH="${1:-$ROOT/submission_intake_template_61day.json}"

python3 /Users/seoki/Desktop/research/examples/fill_submission_intake_61day.py \
  --input "$INPUT_PATH"

bash /Users/seoki/Desktop/research/examples/run_submission_intake_pipeline_61day.sh \
  "$INPUT_PATH"
