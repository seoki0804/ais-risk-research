#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
WB="${ROOT}/outputs/presentation_deck_outline_61day_2026-03-13/workbenches/portfolio_workbench_main_61day"
OUT="${WB}/portfolio_png_fallbacks_61day"

mkdir -p "$OUT"

/opt/homebrew/bin/magick -background white -density 200 \
  "${ROOT}/outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/houston_24h_20231015/houston_24h_20231015_current_threshold_shortlist_compare.svg" \
  -trim +repage -bordercolor white -border 20 -resize 2200x2200\> "${OUT}/houston_current_threshold_shortlist_compare.png"

# Public portfolio pages benefit from a denser Houston hero crop than the
# full three-column comparison figure used in papers and slide decks.
/opt/homebrew/bin/magick \
  "${OUT}/houston_current_threshold_shortlist_compare.png" \
  -gravity northwest -crop 760x730+0+150 +repage \
  -bordercolor white -border 18 -resize 1800x1800\> \
  "${OUT}/houston_current_threshold_shortlist_compare_hero.png"

/opt/homebrew/bin/magick -background white -density 200 \
  "${ROOT}/outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/nola_24h_20231015/nola_24h_20231015_current_threshold_shortlist_compare.svg" \
  -trim +repage -bordercolor white -border 20 -resize 2200x2200\> "${OUT}/nola_current_threshold_shortlist_compare.png"

/opt/homebrew/bin/magick -background white -density 200 \
  "${ROOT}/outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/seattle_24h_20231015/seattle_24h_20231015_current_threshold_shortlist_compare.svg" \
  -trim +repage -bordercolor white -border 20 -resize 2200x2200\> "${OUT}/seattle_current_threshold_shortlist_compare.png"

identify "${OUT}"/*.png
