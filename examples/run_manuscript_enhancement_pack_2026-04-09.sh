#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"
export TMPDIR="${ROOT_DIR}/.tmp"
mkdir -p "$TMPDIR"

python -m ais_risk.manuscript_enhancement_pack_cli \
  --results-root docs/results/2026-04-04-expanded-10seed \
  --output-root docs/manuscript/v0.2_2026-04-09
