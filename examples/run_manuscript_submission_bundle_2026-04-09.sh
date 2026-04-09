#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANUSCRIPT_DIR="$ROOT_DIR/docs/manuscript/v0.2_2026-04-09"
BUNDLE_NAME="submission_bundle_v0.2_2026-04-09.zip"
BUNDLE_PATH="$MANUSCRIPT_DIR/$BUNDLE_NAME"

"$ROOT_DIR/examples/run_manuscript_enhancement_pack_2026-04-09.sh"
"$ROOT_DIR/examples/run_manuscript_docx_export_2026-04-09.sh"

if ! command -v zip >/dev/null 2>&1; then
  echo "zip command is required to build submission bundle."
  exit 1
fi

(
  cd "$MANUSCRIPT_DIR"
  rm -f "$BUNDLE_NAME"
  zip -q "$BUNDLE_NAME" \
    manuscript_draft_v0.2_2026-04-09_en.md \
    manuscript_draft_v0.2_2026-04-09_ko.md \
    manuscript_draft_v0.2_2026-04-09_en.docx \
    manuscript_draft_v0.2_2026-04-09_ko.docx \
    manuscript_submission_template_v0.2_2026-04-09.tex \
    manuscript_todo_v0.2_2026-04-09.md \
    manuscript_consistency_report_v0.2_2026-04-09.md \
    manuscript_consistency_report_v0.2_2026-04-09.docx \
    terminology_mapping_v0.2_2026-04-09.md \
    figure_captions_bilingual_v0.2_2026-04-09.md \
    figure_index.md \
    figure_1_model_family_comparison.svg \
    figure_2_transfer_delta_f1_heatmap.svg \
    figure_3_pipeline_overview.svg \
    recommended_models_summary.csv \
    best_family_by_region_summary.csv \
    transfer_core_summary.csv \
    transfer_uncertainty_summary.csv \
    ablation_tabular_vs_cnn_summary.csv
)

echo "submission_bundle_zip_path=docs/manuscript/v0.2_2026-04-09/$BUNDLE_NAME"
