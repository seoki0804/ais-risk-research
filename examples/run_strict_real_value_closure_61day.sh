#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 <venue_name> <venue_round_or_deadline> [--dry-run]" >&2
  exit 2
fi

VENUE_NAME="$1"
VENUE_ROUND="$2"
DRY_RUN_FLAG="${3:-}"

if [[ -n "$DRY_RUN_FLAG" && "$DRY_RUN_FLAG" != "--dry-run" ]]; then
  echo "Usage: $0 <venue_name> <venue_round_or_deadline> [--dry-run]" >&2
  exit 2
fi

echo "Strict real-value closure run"
echo "  venue_name: $VENUE_NAME"
echo "  venue_round_or_deadline: $VENUE_ROUND"
if [[ "$DRY_RUN_FLAG" == "--dry-run" ]]; then
  echo "  mode: dry-run"
fi
echo

if [[ "$DRY_RUN_FLAG" == "--dry-run" ]]; then
  bash /Users/seoki/Desktop/research/examples/run_apply_submission_real_value_binding_61day.sh \
    "$VENUE_NAME" "$VENUE_ROUND" --dry-run
  exit 0
fi

bash /Users/seoki/Desktop/research/examples/run_apply_submission_real_value_binding_61day.sh \
  "$VENUE_NAME" "$VENUE_ROUND"

echo
echo "Running strict release regression suite..."
bash /Users/seoki/Desktop/research/examples/run_submission_release_regression_suite_61day.sh \
  --strict-real-values

echo
echo "Running strict control tower..."
bash /Users/seoki/Desktop/research/examples/run_submission_release_control_tower_61day.sh \
  --from-current \
  --require-real-values

echo
echo "Running strict operator gate..."
bash /Users/seoki/Desktop/research/examples/run_submission_release_operator_61day.sh \
  --strict-source-match \
  --require-real-values

echo
echo "Strict real-value closure completed."
echo "Check:"
echo "  /Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/submission_metadata_real_value_gate_61day.md"
echo "  /Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/submission_release_regression_suite_61day.md"
echo "  /Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/submission_release_control_tower_61day.md"
echo "  /Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/submission_release_operator_latest_61day.md"
