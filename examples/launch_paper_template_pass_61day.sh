#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  launch_paper_template_pass_61day.sh [--dry-run]
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
TEX="${WB}/paper_conference_8page_asset_locked_61day.tex"
TEMPLATE_PASS="${WB}/paper_template_insertion_final_pass_61day.md"
SIGNOFF="${WB}/paper_final_signoff_sheet_61day.md"
INSERTION_PACK="${WB}/paper_conference_template_insertion_pack_61day.md"
COMPILE_NOTE="${WB}/paper_compile_result_note_61day.md"
LAYOUT_MAP="${WB}/paper_page_layout_map_61day.md"
CUT_MAP="${WB}/paper_conference_cut_map_61day.md"
DELIVERY_MANIFEST="${WB}/paper_delivery_bundle_manifest_61day.md"

for f in "$PDF" "$TEX" "$TEMPLATE_PASS" "$SIGNOFF" "$INSERTION_PACK" "$COMPILE_NOTE" "$LAYOUT_MAP" "$CUT_MAP" "$DELIVERY_MANIFEST"; do
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
echo "Paper TeX: $TEX"

run_cmd "open \"$PDF\""
run_cmd "open \"$TEX\""
run_cmd "open \"$TEMPLATE_PASS\""
run_cmd "open \"$SIGNOFF\""
run_cmd "open \"$INSERTION_PACK\""
run_cmd "open \"$COMPILE_NOTE\""
run_cmd "open \"$LAYOUT_MAP\""
run_cmd "open \"$CUT_MAP\""
run_cmd "open \"$DELIVERY_MANIFEST\""
