#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
COMPILE_SINGLE="$ROOT/examples/compile_packet_manuscript_bundle_61day.sh"

usage() {
  cat <<'EOF'
Usage:
  compile_venue_pair_manuscript_bundle_61day.sh [--dry-run] <venue_slug>

Arguments:
  venue_slug   Short venue identifier

Examples:
  compile_venue_pair_manuscript_bundle_61day.sh maritime_ai_conf
  compile_venue_pair_manuscript_bundle_61day.sh --dry-run maritime_ai_conf
EOF
}

DRY_RUN=0
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

if [[ ${#POSITIONAL[@]} -lt 1 ]]; then
  usage
  exit 1
fi

VENUE_SLUG="${POSITIONAL[0]}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  bash "$COMPILE_SINGLE" --dry-run "$VENUE_SLUG" blind
  echo
  bash "$COMPILE_SINGLE" --dry-run "$VENUE_SLUG" camera-ready
  exit 0
fi

bash "$COMPILE_SINGLE" "$VENUE_SLUG" blind
echo
bash "$COMPILE_SINGLE" "$VENUE_SLUG" camera-ready

