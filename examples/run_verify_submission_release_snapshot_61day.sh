#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"
SNAP_ROOT="$ROOT/submission_release_snapshots_61day"
OUT="$ROOT/submission_release_snapshot_verify_latest_61day.md"

STRICT_FLAG=""
if [[ "${1:-}" == "--strict-source-match" ]]; then
  STRICT_FLAG="--strict-source-match"
fi

python3 /Users/seoki/Desktop/research/examples/verify_submission_release_snapshot_61day.py \
  --snapshot-root "$SNAP_ROOT" \
  --output "$OUT" \
  $STRICT_FLAG

echo "Snapshot verification report:"
echo "  $OUT"
