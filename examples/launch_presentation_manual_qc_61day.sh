#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  launch_presentation_manual_qc_61day.sh <mode> [app] [--dry-run]

Modes:
  5min | 3min

Apps:
  powerpoint | keynote

Examples:
  launch_presentation_manual_qc_61day.sh 5min powerpoint
  launch_presentation_manual_qc_61day.sh 3min keynote --dry-run
EOF
}

ROOT="/Users/seoki/Desktop/research"
WB="${ROOT}/outputs/presentation_deck_outline_61day_2026-03-13/workbenches/presentation_workbench_main_61day"

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

MODE="$1"
shift

APP="powerpoint"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    powerpoint|keynote)
      APP="$1"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unexpected argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

case "$MODE" in
  5min)
    PPTX="${WB}/presentation_8slide_production_draft_61day.pptx"
    PDF="${WB}/presentation_8slide_production_draft_61day.pdf"
    PREVIEW="${WB}/previews/presentation_8slide_production_draft_61day.pptx.png"
    ;;
  3min)
    PPTX="${WB}/presentation_3minute_production_draft_61day.pptx"
    PDF="${WB}/presentation_3minute_production_draft_61day.pdf"
    PREVIEW="${WB}/previews/presentation_3minute_production_draft_61day.pptx.png"
    ;;
  *)
    echo "Unsupported mode: ${MODE}" >&2
    usage >&2
    exit 1
    ;;
esac

case "$APP" in
  powerpoint)
    APP_NAME="Microsoft PowerPoint"
    ;;
  keynote)
    APP_NAME="Keynote"
    ;;
  *)
    echo "Unsupported app: ${APP}" >&2
    exit 1
    ;;
esac

MANUAL_PASS="${WB}/presentation_manual_qc_final_pass_61day.md"
ADJUSTMENT_LOG="${WB}/presentation_manual_adjustment_log_template_61day.md"
APP_CHECK="${WB}/presentation_app_adjustment_checklist_61day.md"
BUILD_CHECK="${WB}/presentation_deck_build_checklist_61day.md"
REHEARSAL_CHECK="${WB}/presentation_rehearsal_quick_checklist_61day.md"
PREVIEW_NOTE="${WB}/presentation_pptx_preview_note_61day.md"

for f in "$PPTX" "$PDF" "$PREVIEW" "$MANUAL_PASS" "$ADJUSTMENT_LOG" "$APP_CHECK" "$BUILD_CHECK" "$REHEARSAL_CHECK" "$PREVIEW_NOTE"; do
  [[ -e "$f" ]] || { echo "Missing required file: $f" >&2; exit 1; }
done

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "$*"
  else
    eval "$@"
  fi
}

echo "Mode: $MODE"
echo "App: $APP_NAME"
echo "PPTX: $PPTX"
echo "PDF: $PDF"

run_cmd "open -a \"$APP_NAME\" \"$PPTX\""
run_cmd "open \"$PDF\""
run_cmd "open \"$PREVIEW\""
run_cmd "open \"$MANUAL_PASS\""
run_cmd "open \"$ADJUSTMENT_LOG\""
run_cmd "open \"$APP_CHECK\""
run_cmd "open \"$BUILD_CHECK\""
run_cmd "open \"$REHEARSAL_CHECK\""
run_cmd "open \"$PREVIEW_NOTE\""
