#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/venue_packets"

usage() {
  cat <<'EOF'
Usage:
  open_venue_pair_packet_61day.sh <venue_slug>

Examples:
  open_venue_pair_packet_61day.sh maritime_applied_conf
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

VENUE_SLUG="$1"
BLIND_DIR="$ROOT/${VENUE_SLUG}_blind_61day"
CAMERA_DIR="$ROOT/${VENUE_SLUG}_camera-ready_61day"

cat <<EOF
Venue pair:
  blind        $BLIND_DIR
  camera-ready $CAMERA_DIR

Reports:
  $BLIND_DIR/VENUE_PACKET_VALIDATION.md
  $BLIND_DIR/VENUE_PACKET_READINESS.md
  $CAMERA_DIR/VENUE_PACKET_VALIDATION.md
  $CAMERA_DIR/VENUE_PACKET_READINESS.md
EOF
