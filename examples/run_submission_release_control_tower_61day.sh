#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_ROOT="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"
OUT="$OUT_ROOT/submission_release_control_tower_61day.md"

RUN_REGRESSION=true
STRICT_REAL_VALUES=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --from-current)
      RUN_REGRESSION=false
      ;;
    --require-real-values)
      STRICT_REAL_VALUES=true
      ;;
    *)
      echo "Usage: $0 [--from-current] [--require-real-values]" >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "$RUN_REGRESSION" == "true" ]]; then
  if [[ "$STRICT_REAL_VALUES" == "true" ]]; then
    bash /Users/seoki/Desktop/research/examples/run_submission_release_regression_suite_61day.sh \
      --strict-real-values
  else
    bash /Users/seoki/Desktop/research/examples/run_submission_release_regression_suite_61day.sh
  fi
fi

BUILD_CMD=(
  python3
  /Users/seoki/Desktop/research/examples/build_submission_release_control_tower_61day.py
  --root "$OUT_ROOT"
  --output "$OUT"
)
if [[ "$STRICT_REAL_VALUES" == "true" ]]; then
  BUILD_CMD+=(--require-real-values)
fi
"${BUILD_CMD[@]}"

echo "Submission release control tower:"
echo "  $OUT"
