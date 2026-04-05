#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_DIR="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13/supplementary_assets_same_area_uncertainty_61day"
CAIRO_LIB="/opt/homebrew/opt/cairo/lib"

mkdir -p "$OUT_DIR"

convert_asset() {
  local src="$1"
  local stem="$2"
  magick -density 300 "$src" "$OUT_DIR/${stem}.png"
  rm -f "$OUT_DIR/${stem}.pdf"
  if DYLD_FALLBACK_LIBRARY_PATH="$CAIRO_LIB" python - <<'PY' >/dev/null 2>&1
import cairosvg
PY
  then
    DYLD_FALLBACK_LIBRARY_PATH="$CAIRO_LIB" python - <<PY
import cairosvg
cairosvg.svg2pdf(url=r"$src", write_to=r"$OUT_DIR/${stem}.pdf")
PY
  else
    magick -density 300 "$src" "$OUT_DIR/${stem}.pdf"
  fi
}

convert_asset \
  "$ROOT/outputs/2026-03-16_uncertainty_contour_houston_base/houston_base_uncertainty_contour_figure.svg" \
  "supplementary_figure_s2a_houston_base_uncertainty"

convert_asset \
  "$ROOT/outputs/2026-03-16_uncertainty_contour_houston_holdout/houston_holdout_uncertainty_contour_figure.svg" \
  "supplementary_figure_s2b_houston_holdout_uncertainty"

echo "Exported same-area supplementary assets to $OUT_DIR"
