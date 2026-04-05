#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_ROOT="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13/venue_packets"

usage() {
  cat <<'EOF'
Usage:
  open_packet_manuscript_bundle_61day.sh <venue_slug> [mode]

Arguments:
  venue_slug   Short venue identifier
  mode         blind | camera-ready

Examples:
  open_packet_manuscript_bundle_61day.sh maritime_ai_conf blind
  open_packet_manuscript_bundle_61day.sh maritime_ai_conf camera-ready
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

VENUE_SLUG="$1"
MODE="${2:-blind}"
PACKET_DIR="$OUT_ROOT/${VENUE_SLUG}_${MODE}_61day"
BUNDLE_DIR="$PACKET_DIR/manuscript_bundle_61day"

if [[ ! -d "$BUNDLE_DIR" ]]; then
  echo "Manuscript bundle not found: $BUNDLE_DIR" >&2
  exit 1
fi

echo "Manuscript bundle:"
echo "  $BUNDLE_DIR"
echo
echo "Key files:"
echo "  $BUNDLE_DIR/MANUSCRIPT_BUNDLE_NOTE_61day.md"
echo "  $BUNDLE_DIR/compile_manuscript_bundle_61day.sh"
if [[ "$MODE" == "blind" ]]; then
  echo "  $BUNDLE_DIR/paper_blind_bound_61day.tex"
else
  echo "  $BUNDLE_DIR/paper_camera-ready_bound_61day.tex"
fi
echo "  $BUNDLE_DIR/paper_conference_8page_asset_locked_61day.bbl"
echo "  $BUNDLE_DIR/literature_reference_pack_61day.bib"
echo "  $BUNDLE_DIR/conference_print_assets_61day"
