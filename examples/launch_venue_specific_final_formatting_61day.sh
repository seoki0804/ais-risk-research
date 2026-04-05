#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_BASE="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"
MODE="blind"
VENUE_SLUG="sample_conference"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  launch_venue_specific_final_formatting_61day.sh [--dry-run] [venue_slug] [mode]

Arguments:
  venue_slug   Short venue identifier. Default: sample_conference
  mode         blind | camera-ready | journal | internal

Examples:
  launch_venue_specific_final_formatting_61day.sh --dry-run sample_conference blind
  launch_venue_specific_final_formatting_61day.sh icra_workshop blind
  launch_venue_specific_final_formatting_61day.sh tmr_journal journal
EOF
}

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

if [[ ${#POSITIONAL[@]} -ge 1 ]]; then
  VENUE_SLUG="${POSITIONAL[0]}"
fi

if [[ ${#POSITIONAL[@]} -ge 2 ]]; then
  MODE="${POSITIONAL[1]}"
fi

case "$MODE" in
  blind|camera-ready|journal|internal)
    ;;
  *)
    echo "Unsupported mode: $MODE" >&2
    usage
    exit 1
    ;;
esac

READINESS_DOC="$OUT_BASE/venue_specific_final_formatting_readiness_61day.md"
RESET_DOC="$OUT_BASE/hard_reset_reassessment_61day.md"
REDUCTION_DOC="$OUT_BASE/paper_main_story_reduction_map_61day.md"
FIT_DOC="$OUT_BASE/target_venue_fit_assessment_61day.md"
QUICK_DOC="$OUT_BASE/target_venue_choice_quick_sheet_61day.md"
INTAKE_DOC="$OUT_BASE/target_venue_intake_sheet_61day.md"
PAPER_PASS="$OUT_BASE/workbenches/paper_workbench_main_61day/paper_template_insertion_final_pass_61day.md"
BIB_DOC="$OUT_BASE/paper_bibliography_insertion_rehearsal_61day.md"
BLIND_DOC="$OUT_BASE/blind_submission_final_pass_61day.md"
CAMERA_DOC="$OUT_BASE/venue_ops_kit_61day/camera_ready_final_pass_61day.md"
QA_DOC="$OUT_BASE/venue_completion_packet_61day/submission_final_qc_checklist_61day.md"
SIGNOFF_DOC="$OUT_BASE/workbenches/paper_workbench_main_61day/paper_final_signoff_sheet_61day.md"
DEST_DIR="$OUT_BASE/venue_packets/${VENUE_SLUG}_${MODE}_61day"
VALIDATION_DOC="$DEST_DIR/VENUE_PACKET_VALIDATION.md"
READINESS_REPORT="$DEST_DIR/VENUE_PACKET_READINESS.md"

echo "Venue-specific final formatting launcher"
echo "  venue_slug: $VENUE_SLUG"
echo "  mode:       $MODE"
echo
echo "Open in this order:"
echo "  1. $RESET_DOC"
echo "  2. $REDUCTION_DOC"
echo "  3. $READINESS_DOC"
echo "  4. $FIT_DOC"
echo "  5. $QUICK_DOC"
echo "  6. $INTAKE_DOC"
echo "  7. $PAPER_PASS"
echo "  8. $BIB_DOC"
if [[ "$MODE" == "blind" ]]; then
  echo "  9. $BLIND_DOC"
else
  echo "  9. $CAMERA_DOC"
fi
echo "  10. $QA_DOC"
echo "  11. $SIGNOFF_DOC"
echo "  12. $VALIDATION_DOC"
echo "  13. $READINESS_REPORT"
echo

PREPARE="$ROOT/examples/prepare_venue_packet_61day.sh"
if [[ "$DRY_RUN" -eq 1 ]]; then
  if [[ -e "$DEST_DIR" ]]; then
    echo "Dry run note: destination already exists."
    echo "  $DEST_DIR"
    exit 0
  fi
  "$PREPARE" --dry-run "$VENUE_SLUG" "$MODE"
else
  "$PREPARE" "$VENUE_SLUG" "$MODE"
fi
