#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  launch_reviewer_rebuttal_pass_61day.sh [--dry-run]
EOF
}

ROOT="/Users/seoki/Desktop/research"
BASE="${ROOT}/outputs/presentation_deck_outline_61day_2026-03-13"

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

FINAL_PASS="${BASE}/reviewer_rebuttal_final_pass_61day.md"
SHORT_PACK="${BASE}/reviewer_rebuttal_short_pack_61day_ko_en.md"
SECTION_PACK="${BASE}/reviewer_rebuttal_section_pack_61day_ko_en.md"
CONF_TONE="${BASE}/reviewer_rebuttal_conference_tone_61day_ko_en.md"
JOURNAL_TONE="${BASE}/reviewer_rebuttal_journal_tone_61day_ko_en.md"
ONEPAGE_MD="${BASE}/evaluation_rebuttal_onepage_table_61day.md"
ONEPAGE_CSV="${BASE}/evaluation_rebuttal_onepage_table_61day.csv"
COMMENT_TEMPL="${BASE}/reviewer_comment_template_pack_61day_ko_en.md"
FIGURE_TEMPL="${BASE}/reviewer_figure_table_stats_template_pack_61day_ko_en.md"
SIGNOFF="${BASE}/reviewer_rebuttal_signoff_sheet_61day.md"

for f in "$FINAL_PASS" "$SHORT_PACK" "$SECTION_PACK" "$CONF_TONE" "$JOURNAL_TONE" "$ONEPAGE_MD" "$ONEPAGE_CSV" "$COMMENT_TEMPL" "$FIGURE_TEMPL" "$SIGNOFF"; do
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
run_cmd "open \"$SHORT_PACK\""
run_cmd "open \"$SECTION_PACK\""
run_cmd "open \"$CONF_TONE\""
run_cmd "open \"$JOURNAL_TONE\""
run_cmd "open \"$ONEPAGE_MD\""
run_cmd "open \"$ONEPAGE_CSV\""
run_cmd "open \"$COMMENT_TEMPL\""
run_cmd "open \"$FIGURE_TEMPL\""
run_cmd "open \"$SIGNOFF\""
