#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
PACKETS_ROOT="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13/venue_packets"
BIND="$ROOT/examples/bind_packet_manuscript_61day.py"

usage() {
  cat <<'EOF'
Usage:
  retrofit_venue_packet_manuscripts_61day.sh [venue_packets_root]

Examples:
  retrofit_venue_packet_manuscripts_61day.sh
  retrofit_venue_packet_manuscripts_61day.sh /path/to/venue_packets
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

TARGET_ROOT="${1:-$PACKETS_ROOT}"

if [[ ! -d "$TARGET_ROOT" ]]; then
  echo "Venue packets root not found: $TARGET_ROOT" >&2
  exit 1
fi

while IFS= read -r packet_dir; do
  packet_name="$(basename "$packet_dir")"
  if [[ "$packet_name" == *_blind_61day ]]; then
    mode="blind"
  elif [[ "$packet_name" == *_camera-ready_61day ]]; then
    mode="camera-ready"
  else
    continue
  fi
  python "$BIND" "$packet_dir" "$mode" >/dev/null
  echo "bound: $packet_name ($mode)"
done < <(find "$TARGET_ROOT" -maxdepth 1 -mindepth 1 -type d | sort)
