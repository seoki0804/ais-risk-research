#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
PRELIGHT="$ROOT/examples/run_venue_pair_preflight_61day.sh"
DEFAULT_SLUG="applied_conf_default"

usage() {
  cat <<'EOF'
Usage:
  run_canonical_preflight_61day.sh [--dry-run]

Examples:
  run_canonical_preflight_61day.sh
  run_canonical_preflight_61day.sh --dry-run
EOF
}

if [[ $# -gt 1 ]]; then
  usage
  exit 1
fi

if [[ $# -eq 1 ]]; then
  case "$1" in
    --dry-run)
      bash "$PRELIGHT" --dry-run --reuse-existing "$DEFAULT_SLUG"
      exit 0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 1
      ;;
  esac
fi

bash "$PRELIGHT" --reuse-existing "$DEFAULT_SLUG"
