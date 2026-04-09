#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python "$ROOT_DIR/examples/verify_manuscript_submission_bundle_2026-04-09.py" \
  --manuscript-dir "$ROOT_DIR/docs/manuscript/v0.2_2026-04-09" \
  --bundle-name "submission_bundle_v0.2_2026-04-09.zip" \
  --manifest-name "submission_bundle_manifest_v0.2_2026-04-09.txt"
