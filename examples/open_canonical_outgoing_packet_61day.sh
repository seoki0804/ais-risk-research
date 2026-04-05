#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_BASE="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"
PACKET_DIR="$OUT_BASE/venue_packets/applied_conf_default_blind_61day"

echo "Canonical outgoing packet"
echo "  packet: $PACKET_DIR"
echo
echo "Open in this order:"
echo "  1. $OUT_BASE/canonical_outgoing_packet_61day.md"
echo "  2. $OUT_BASE/recommended_submission_lane_61day.md"
echo "  3. $OUT_BASE/hard_reset_reassessment_61day.md"
echo "  4. $OUT_BASE/paper_main_story_reduction_map_61day.md"
echo "  5. $PACKET_DIR/VENUE_PACKET_VALIDATION.md"
echo "  6. $PACKET_DIR/VENUE_PACKET_READINESS.md"
echo "  7. $PACKET_DIR"
