#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  launch_portfolio_release_pass_61day.sh [--dry-run]
EOF
}

ROOT="/Users/seoki/Desktop/research"
WB="${ROOT}/outputs/presentation_deck_outline_61day_2026-03-13/workbenches/portfolio_workbench_main_61day"

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

FINAL_PASS="${WB}/portfolio_public_release_final_pass_61day.md"
PUBLISH_READY="${WB}/portfolio_publish_ready_page_61day.md"
READY_COPY="${WB}/portfolio_public_page_ready_copy_61day.md"
COPY_PASTE="${WB}/portfolio_copy_paste_sheet_61day_ko_en.md"
FALLBACK_NOTE="${WB}/portfolio_visual_fallback_note_61day.md"
WIDTH_GUIDE="${WB}/portfolio_platform_width_guide_61day.md"
PLACEMENT="${WB}/portfolio_asset_placement_sheet_61day.md"
BUILD_CHECK="${WB}/portfolio_build_checklist_61day.md"
REVIEW_CHECK="${WB}/portfolio_quick_review_checklist_61day.md"
SIGNOFF="${WB}/portfolio_final_signoff_sheet_61day.md"
BUNDLE_MANIFEST="${WB}/portfolio_release_bundle_manifest_61day.md"

for f in "$FINAL_PASS" "$PUBLISH_READY" "$READY_COPY" "$COPY_PASTE" "$FALLBACK_NOTE" "$WIDTH_GUIDE" "$PLACEMENT" "$BUILD_CHECK" "$REVIEW_CHECK" "$SIGNOFF" "$BUNDLE_MANIFEST"; do
  [[ -e "$f" ]] || { echo "Missing required file: $f" >&2; exit 1; }
done

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "$*"
  else
    eval "$@"
  fi
}

run_cmd "open \"$FINAL_PASS\""
run_cmd "open \"$PUBLISH_READY\""
run_cmd "open \"$READY_COPY\""
run_cmd "open \"$COPY_PASTE\""
run_cmd "open \"$FALLBACK_NOTE\""
run_cmd "open \"$WIDTH_GUIDE\""
run_cmd "open \"$PLACEMENT\""
run_cmd "open \"$BUILD_CHECK\""
run_cmd "open \"$REVIEW_CHECK\""
run_cmd "open \"$SIGNOFF\""
run_cmd "open \"$BUNDLE_MANIFEST\""
