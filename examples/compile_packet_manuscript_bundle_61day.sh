#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_ROOT="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13/venue_packets"

usage() {
  cat <<'EOF'
Usage:
  compile_packet_manuscript_bundle_61day.sh [--dry-run] <venue_slug> [mode]

Arguments:
  venue_slug   Short venue identifier
  mode         blind | camera-ready

Examples:
  compile_packet_manuscript_bundle_61day.sh maritime_ai_conf blind
  compile_packet_manuscript_bundle_61day.sh maritime_ai_conf camera-ready
  compile_packet_manuscript_bundle_61day.sh --dry-run maritime_ai_conf blind
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
MODE="${POSITIONAL[1]:-blind}"
PACKET_DIR="$OUT_ROOT/${VENUE_SLUG}_${MODE}_61day"
BUNDLE_DIR="$PACKET_DIR/manuscript_bundle_61day"
COMPILE_SCRIPT="$BUNDLE_DIR/compile_manuscript_bundle_61day.sh"

if [[ ! -d "$BUNDLE_DIR" ]]; then
  echo "Manuscript bundle not found: $BUNDLE_DIR" >&2
  exit 1
fi

if [[ ! -x "$COMPILE_SCRIPT" ]]; then
  echo "Compile helper not executable: $COMPILE_SCRIPT" >&2
  exit 1
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run only."
  echo "Would compile:"
  echo "  $COMPILE_SCRIPT"
  exit 0
fi

echo "Compiling packet-local manuscript bundle:"
echo "  $BUNDLE_DIR"
echo
bash "$COMPILE_SCRIPT"

