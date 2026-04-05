#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  launch_portfolio_github_pass_61day.sh [--dry-run]
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

README_MD="${ROOT}/README.md"
PUBLIC_PAGE="${ROOT}/PORTFOLIO_PUBLIC_PAGE.md"
FINAL_PASS="${WB}/portfolio_github_final_pass_61day.md"
WIDTH_GUIDE="${WB}/portfolio_platform_width_guide_61day.md"
PREVIEW_NOTE="${WB}/portfolio_render_preview_note_61day.md"
COPY_PASTE="${WB}/portfolio_copy_paste_sheet_61day_ko_en.md"
SIGNOFF="${WB}/portfolio_final_signoff_sheet_61day.md"
PUBLIC_PREVIEW="${ROOT}/output/playwright/portfolio_public_page_preview_61day.png"
README_PREVIEW="${ROOT}/output/playwright/portfolio_readme_preview_61day.png"

for f in "$README_MD" "$PUBLIC_PAGE" "$FINAL_PASS" "$WIDTH_GUIDE" "$PREVIEW_NOTE" "$COPY_PASTE" "$SIGNOFF" "$PUBLIC_PREVIEW" "$README_PREVIEW"; do
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
run_cmd "open \"$README_MD\""
run_cmd "open \"$PUBLIC_PAGE\""
run_cmd "open \"$WIDTH_GUIDE\""
run_cmd "open \"$PREVIEW_NOTE\""
run_cmd "open \"$COPY_PASTE\""
run_cmd "open \"$SIGNOFF\""
run_cmd "open \"$PUBLIC_PREVIEW\""
run_cmd "open \"$README_PREVIEW\""
