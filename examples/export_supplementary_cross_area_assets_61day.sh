#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
SRC_ROOT="$ROOT/outputs"
OUT_DIR="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13/supplementary_assets_cross_area_uncertainty_61day"
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
  "$SRC_ROOT/2026-03-16_cross_area_transfer_houston_to_seattle_0809/houston_to_seattle_0809_uncertainty_report_figure.svg" \
  "supplementary_figure_s3a_houston_to_seattle_0809"

convert_asset \
  "$SRC_ROOT/2026-03-16_cross_area_transfer_houston_to_nola_0809/houston_to_nola_0809_uncertainty_report_figure.svg" \
  "supplementary_figure_s3b_houston_to_nola_0809"

convert_asset \
  "$SRC_ROOT/2026-03-16_cross_area_transfer_houston_to_seattle_0811/houston_to_seattle_0811_uncertainty_report_figure.svg" \
  "supplementary_figure_s3c_houston_to_seattle_0811"

convert_asset \
  "$SRC_ROOT/2026-03-16_cross_area_transfer_houston_to_nola_0811/houston_to_nola_0811_uncertainty_report_figure.svg" \
  "supplementary_figure_s3d_houston_to_nola_0811"

echo "Exported cross-area supplementary assets to $OUT_DIR"
