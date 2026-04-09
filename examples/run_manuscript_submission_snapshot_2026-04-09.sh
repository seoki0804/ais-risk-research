#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANUSCRIPT_DIR="$ROOT_DIR/docs/manuscript/v0.2_2026-04-09"
RELEASE_ROOT="$ROOT_DIR/docs/manuscript/releases"

BUNDLE_NAME="submission_bundle_v0.2_2026-04-09.zip"
MANIFEST_NAME="submission_bundle_manifest_v0.2_2026-04-09.txt"
PREFLIGHT_NAME="manuscript_submission_preflight_report_v0.2_2026-04-09.md"
CONSISTENCY_NAME="manuscript_consistency_report_v0.2_2026-04-09.md"

"$ROOT_DIR/examples/run_manuscript_submission_bundle_2026-04-09.sh"

TIMESTAMP_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
GIT_SHA="$(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
SNAPSHOT_ID="submission_snapshot_${TIMESTAMP_UTC}_${GIT_SHA}"
SNAPSHOT_DIR="$RELEASE_ROOT/$SNAPSHOT_ID"
mkdir -p "$SNAPSHOT_DIR"

cp "$MANUSCRIPT_DIR/$BUNDLE_NAME" "$SNAPSHOT_DIR/"
cp "$MANUSCRIPT_DIR/$MANIFEST_NAME" "$SNAPSHOT_DIR/"
cp "$MANUSCRIPT_DIR/$PREFLIGHT_NAME" "$SNAPSHOT_DIR/"
cp "$MANUSCRIPT_DIR/$CONSISTENCY_NAME" "$SNAPSHOT_DIR/"

if command -v shasum >/dev/null 2>&1; then
  SHA256_CMD=(shasum -a 256)
elif command -v sha256sum >/dev/null 2>&1; then
  SHA256_CMD=(sha256sum)
else
  echo "A SHA-256 tool is required (shasum or sha256sum)."
  exit 1
fi

{
  echo "snapshot_id=$SNAPSHOT_ID"
  echo "created_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "git_sha=$GIT_SHA"
  echo "---"
  "${SHA256_CMD[@]}" "$SNAPSHOT_DIR/$BUNDLE_NAME"
  "${SHA256_CMD[@]}" "$SNAPSHOT_DIR/$MANIFEST_NAME"
  "${SHA256_CMD[@]}" "$SNAPSHOT_DIR/$PREFLIGHT_NAME"
  "${SHA256_CMD[@]}" "$SNAPSHOT_DIR/$CONSISTENCY_NAME"
} > "$SNAPSHOT_DIR/snapshot_index.txt"

echo "submission_snapshot_dir_path=${SNAPSHOT_DIR#$ROOT_DIR/}"
echo "submission_snapshot_index_path=${SNAPSHOT_DIR#$ROOT_DIR/}/snapshot_index.txt"
