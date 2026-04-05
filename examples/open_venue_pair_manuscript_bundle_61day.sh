#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OPEN_SINGLE="$ROOT/examples/open_packet_manuscript_bundle_61day.sh"

usage() {
  cat <<'EOF'
Usage:
  open_venue_pair_manuscript_bundle_61day.sh <venue_slug>

Arguments:
  venue_slug   Short venue identifier

Examples:
  open_venue_pair_manuscript_bundle_61day.sh maritime_ai_conf
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

VENUE_SLUG="$1"

bash "$OPEN_SINGLE" "$VENUE_SLUG" blind
echo
bash "$OPEN_SINGLE" "$VENUE_SLUG" camera-ready
