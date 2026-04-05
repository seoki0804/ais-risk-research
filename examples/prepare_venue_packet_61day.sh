#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
SRC_DIR="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13/submission_ready_bundle_61day"
OUT_ROOT="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13/venue_packets"

usage() {
  cat <<'EOF'
Usage:
  prepare_venue_packet_61day.sh [--dry-run] [--print-path] <venue_slug> [mode]

Arguments:
  venue_slug   Short venue identifier, e.g. icra_workshop, ocex_demo, journal_x
  mode         blind | camera-ready | journal | internal

Examples:
  prepare_venue_packet_61day.sh icra_workshop blind
  prepare_venue_packet_61day.sh tmr_journal journal
  prepare_venue_packet_61day.sh --dry-run icra_workshop blind
EOF
}

DRY_RUN=0
PRINT_PATH=0
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --print-path)
      PRINT_PATH=1
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

case "$MODE" in
  blind|camera-ready|journal|internal)
    ;;
  *)
    echo "Unsupported mode: $MODE" >&2
    usage
    exit 1
    ;;
esac

DEST_DIR="$OUT_ROOT/${VENUE_SLUG}_${MODE}_61day"

if [[ -e "$DEST_DIR" ]]; then
  echo "Destination already exists: $DEST_DIR" >&2
  exit 1
fi

if [[ "$PRINT_PATH" -eq 1 ]]; then
  echo "$DEST_DIR"
  if [[ "$DRY_RUN" -eq 0 ]]; then
    exit 0
  fi
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run only. Would create:"
  echo "  $DEST_DIR"
  echo
  echo "Would copy from:"
  echo "  $SRC_DIR"
  echo
  echo "Would create note file:"
  echo "  $DEST_DIR/VENUE_PACKET_NOTES.md"
  exit 0
fi

mkdir -p "$OUT_ROOT"
cp -R "$SRC_DIR" "$DEST_DIR"

cat > "$DEST_DIR/VENUE_PACKET_NOTES.md" <<EOF
# Venue Packet Notes

- Venue slug: \`$VENUE_SLUG\`
- Mode: \`$MODE\`
- Created from: \`submission_ready_bundle_61day\`

## First steps

1. Fill \`target_venue_intake_sheet_61day.md\`
2. Open \`venue_specific_adaptation_runbook_61day.md\`
3. Pick the correct path:
   - \`blind_submission_final_pass_61day.md\` for double-blind review
   - \`camera_ready_final_pass_61day.md\` for accepted camera-ready editing

## If this is a blind submission

Use in this order:
1. \`anonymous_submission_portal_variants_61day.md\`
2. \`anonymous_wording_final_pass_61day.md\`
3. \`blind_review_compliance_checklist_61day.md\`
4. \`submission_final_qc_checklist_61day.md\`

## If this is a camera-ready submission

Use in this order:
1. \`camera_ready_front_matter_template_61day.md\`
2. \`camera_ready_metadata_fill_pack_61day.md\`
3. \`camera_ready_metadata_fill_template_61day.json\`
4. \`submission_final_qc_checklist_61day.md\`

## Working notes

- Intake status:
- Abstract limit:
- Page limit:
- Supplementary allowed:
- Figure format:
- Blind review policy:
- Camera-ready metadata ready:
- Final output file:
EOF

echo "Created venue packet:"
echo "  $DEST_DIR"
echo
echo "Next:"
echo "  1. Open target_venue_intake_sheet_61day.md"
echo "  2. Open venue_specific_adaptation_runbook_61day.md"
echo "  3. Use VENUE_PACKET_NOTES.md for venue-specific progress tracking"
