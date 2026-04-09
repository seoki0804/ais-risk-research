#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANUSCRIPT_DIR="$ROOT_DIR/docs/manuscript/v0.2_2026-04-09"
BUNDLE_NAME="submission_bundle_v0.2_2026-04-09.zip"
BUNDLE_PATH="$MANUSCRIPT_DIR/$BUNDLE_NAME"
MANIFEST_NAME="submission_bundle_manifest_v0.2_2026-04-09.txt"
MANIFEST_PATH="$MANUSCRIPT_DIR/$MANIFEST_NAME"
PREFLIGHT_REPORT_NAME="manuscript_submission_preflight_report_v0.2_2026-04-09.md"

FILES=(
  manuscript_draft_v0.2_2026-04-09_en.md
  manuscript_draft_v0.2_2026-04-09_ko.md
  manuscript_draft_v0.2_2026-04-09_en.docx
  manuscript_draft_v0.2_2026-04-09_ko.docx
  manuscript_submission_template_v0.2_2026-04-09.tex
  manuscript_todo_v0.2_2026-04-09.md
  bilingual_parity_report_v0.2_2026-04-09.md
  prior_work_evidence_matrix_v0.2_2026-04-09.md
  examiner_critical_todo_v0.2_2026-04-09.md
  manuscript_consistency_report_v0.2_2026-04-09.md
  manuscript_consistency_report_v0.2_2026-04-09.docx
  terminology_mapping_v0.2_2026-04-09.md
  figure_captions_bilingual_v0.2_2026-04-09.md
  figure_index.md
  figure_1_model_family_comparison.svg
  figure_2_transfer_delta_f1_heatmap.svg
  figure_3_pipeline_overview.svg
  figure_4_threshold_utility_curve.svg
  recommended_models_summary.csv
  best_family_by_region_summary.csv
  transfer_core_summary.csv
  transfer_uncertainty_summary.csv
  transfer_route_significance_summary.csv
  transfer_route_repeated_randomization_significance_summary.csv
  out_of_domain_validation_detail_summary.csv
  out_of_domain_validation_summary.csv
  threshold_utility_curve_summary.csv
  threshold_utility_operating_points.csv
  ablation_tabular_vs_cnn_summary.csv
  model_family_significance_summary.csv
  statistical_significance_appendix_v0.2_2026-04-09.md
  transfer_route_significance_appendix_v0.2_2026-04-09.md
  transfer_route_repeated_randomization_appendix_v0.2_2026-04-09.md
  threshold_utility_appendix_v0.2_2026-04-09.md
  out_of_domain_validation_appendix_v0.2_2026-04-09.md
)

"$ROOT_DIR/examples/run_manuscript_enhancement_pack_2026-04-09.sh"
"$ROOT_DIR/examples/run_manuscript_docx_export_2026-04-09.sh"

if ! command -v zip >/dev/null 2>&1; then
  echo "zip command is required to build submission bundle."
  exit 1
fi

if command -v shasum >/dev/null 2>&1; then
  SHA256_CMD=(shasum -a 256)
elif command -v sha256sum >/dev/null 2>&1; then
  SHA256_CMD=(sha256sum)
else
  echo "A SHA-256 tool is required (shasum or sha256sum)."
  exit 1
fi

(
  cd "$MANUSCRIPT_DIR"
  for file in "${FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
      echo "Missing required artifact: $file"
      exit 1
    fi
  done

  rm -f "$MANIFEST_NAME"
  {
    echo "bundle_name=$BUNDLE_NAME"
    echo "generated_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "file_count=${#FILES[@]}"
    echo "---"
    for file in "${FILES[@]}"; do
      "${SHA256_CMD[@]}" "$file"
    done
  } > "$MANIFEST_NAME"

  rm -f "$BUNDLE_NAME"
  zip -q "$BUNDLE_NAME" "${FILES[@]}" "$MANIFEST_NAME"
)

echo "submission_bundle_zip_path=docs/manuscript/v0.2_2026-04-09/$BUNDLE_NAME"
echo "submission_bundle_manifest_path=docs/manuscript/v0.2_2026-04-09/$MANIFEST_NAME"

BUNDLE_SHA="$("${SHA256_CMD[@]}" "$BUNDLE_PATH" | awk '{print $1}')"
echo "submission_bundle_zip_sha256=$BUNDLE_SHA"

python "$ROOT_DIR/examples/verify_manuscript_submission_bundle_2026-04-09.py" \
  --manuscript-dir "$MANUSCRIPT_DIR" \
  --bundle-name "$BUNDLE_NAME" \
  --manifest-name "$MANIFEST_NAME"

python "$ROOT_DIR/examples/generate_manuscript_submission_preflight_report_2026-04-09.py" \
  --root-dir "$ROOT_DIR" \
  --manuscript-dir "$MANUSCRIPT_DIR" \
  --bundle-name "$BUNDLE_NAME" \
  --manifest-name "$MANIFEST_NAME" \
  --report-name "$PREFLIGHT_REPORT_NAME"

echo "submission_preflight_report_path=docs/manuscript/v0.2_2026-04-09/$PREFLIGHT_REPORT_NAME"
