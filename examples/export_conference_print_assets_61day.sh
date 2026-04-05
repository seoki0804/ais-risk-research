#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
SRC_DIR="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"
OUT_DIR="$SRC_DIR/conference_print_assets_61day"

mkdir -p "$OUT_DIR"

convert_asset() {
  local src="$1"
  local stem="$2"
  magick -density 300 "$src" "$OUT_DIR/${stem}.png"
  magick -density 300 "$src" "$OUT_DIR/${stem}.pdf"
}

convert_asset "$ROOT/outputs/threshold_shortlist_holdout_compare_61day_2026-03-13/houston_24h_20231015/houston_24h_20231015_current_threshold_shortlist_compare.svg" "figure1_holdout_compare_houston"
convert_asset "$SRC_DIR/scenario_aware_contour_compare_61day.svg" "figure2_scenario_aware_contour_compare"
convert_asset "$SRC_DIR/scenario_aware_contour_compare_61day_single_column.svg" "figure2_scenario_aware_contour_compare_single_column"
convert_asset "$SRC_DIR/regional_failure_mode_schematic_61day.svg" "figure3_regional_failure_mode_schematic"
convert_asset "$SRC_DIR/regional_failure_mode_schematic_61day_single_column.svg" "figure3_regional_failure_mode_schematic_single_column"
convert_asset "$SRC_DIR/supplementary_assets_nola_20230812/nola_20230812_tradeoff_figure.svg" "supplementary_figure_s1_nola_tradeoff"
convert_asset "$SRC_DIR/supplementary_assets_nola_20230812/nola_20230812_tradeoff_figure_single_column.svg" "supplementary_figure_s1_nola_tradeoff_single_column"

echo "Exported assets to $OUT_DIR"
