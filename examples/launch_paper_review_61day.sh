#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  launch_paper_review_61day.sh [--dry-run]
EOF
}

ROOT="/Users/seoki/Desktop/research"
WB="${ROOT}/outputs/presentation_deck_outline_61day_2026-03-13/workbenches/paper_workbench_main_61day"

DRY_RUN=0

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
      echo "Unexpected argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

PDF="${WB}/paper_conference_8page_asset_locked_61day.pdf"
PREVIEW="${WB}/previews/paper_conference_8page_asset_locked_61day.pdf.png"
REVIEWER_PASS="${WB}/paper_reviewer_final_pass_61day.md"
PREVIEW_NOTE="${WB}/paper_pdf_preview_note_61day.md"
COMPILE_NOTE="${WB}/paper_compile_result_note_61day.md"
WORKING_DRAFT="${WB}/paper_conference_8page_working_draft_61day.tex"
WORKLIST="${WB}/PAPER_EDIT_WORKLIST_61day.md"
CUT_MAP="${WB}/paper_conference_cut_map_61day.md"
LAYOUT_MAP="${WB}/paper_page_layout_map_61day.md"
TABLES="${WB}/table_final_bundle_61day.md"

for f in "$PDF" "$PREVIEW" "$REVIEWER_PASS" "$PREVIEW_NOTE" "$COMPILE_NOTE" "$WORKING_DRAFT" "$WORKLIST" "$CUT_MAP" "$LAYOUT_MAP" "$TABLES"; do
  [[ -e "$f" ]] || { echo "Missing required file: $f" >&2; exit 1; }
done

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "$*"
  else
    eval "$@"
  fi
}

echo "Paper PDF: $PDF"

run_cmd "open \"$PDF\""
run_cmd "open \"$PREVIEW\""
run_cmd "open \"$REVIEWER_PASS\""
run_cmd "open \"$PREVIEW_NOTE\""
run_cmd "open \"$COMPILE_NOTE\""
run_cmd "open \"$LAYOUT_MAP\""
run_cmd "open \"$CUT_MAP\""
run_cmd "open \"$TABLES\""
run_cmd "open \"$WORKING_DRAFT\""
run_cmd "open \"$WORKLIST\""
