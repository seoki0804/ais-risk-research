#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_BASE="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"
MODE="${1:-blind}"

usage() {
  cat <<'EOF'
Usage:
  launch_default_applied_conference_61day.sh [mode]

Arguments:
  mode   blind | camera-ready

Examples:
  launch_default_applied_conference_61day.sh blind
  launch_default_applied_conference_61day.sh camera-ready
EOF
}

case "$MODE" in
  blind|camera-ready)
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    echo "Unsupported mode: $MODE" >&2
    usage
    exit 1
    ;;
esac

PROFILE_DOC="$OUT_BASE/target_venue_default_applied_conference_profile_61day.md"
INTAKE_DOC="$OUT_BASE/target_venue_intake_applied_conference_default_61day.md"
PACKET_NOTE="$OUT_BASE/applied_conference_default_packet_note_61day.md"
READINESS_DOC="$OUT_BASE/venue_specific_final_formatting_readiness_61day.md"
RESET_DOC="$OUT_BASE/hard_reset_reassessment_61day.md"
REDUCTION_DOC="$OUT_BASE/paper_main_story_reduction_map_61day.md"
LAUNCHER="$ROOT/examples/launch_venue_specific_final_formatting_61day.sh"

if [[ "$MODE" == "blind" ]]; then
  PACKET_DIR="$OUT_BASE/venue_packets/applied_conf_default_blind_61day"
else
  PACKET_DIR="$OUT_BASE/venue_packets/applied_conf_default_camera-ready_61day"
fi
VALIDATION_DOC="$PACKET_DIR/VENUE_PACKET_VALIDATION.md"
READINESS_REPORT="$PACKET_DIR/VENUE_PACKET_READINESS.md"

echo "Default applied conference launcher"
echo "  mode: $MODE"
echo
echo "Open in this order:"
echo "  1. $RESET_DOC"
echo "  2. $REDUCTION_DOC"
echo "  3. $PROFILE_DOC"
echo "  4. $INTAKE_DOC"
echo "  5. $PACKET_NOTE"
echo "  6. $READINESS_DOC"
echo "  7. $VALIDATION_DOC"
echo "  8. $READINESS_REPORT"
echo "  9. $PACKET_DIR"
echo
echo "General launcher equivalent:"
echo "  bash $LAUNCHER applied_conf_default $MODE"
