#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANUSCRIPT_DIR="$ROOT_DIR/docs/manuscript/v0.2_2026-04-09"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "pandoc is required for DOCX export."
  exit 1
fi

pandoc "$MANUSCRIPT_DIR/manuscript_draft_v0.2_2026-04-09_en.md" \
  --resource-path "$MANUSCRIPT_DIR" \
  -o "$MANUSCRIPT_DIR/manuscript_draft_v0.2_2026-04-09_en.docx"

pandoc "$MANUSCRIPT_DIR/manuscript_draft_v0.2_2026-04-09_ko.md" \
  --resource-path "$MANUSCRIPT_DIR" \
  -o "$MANUSCRIPT_DIR/manuscript_draft_v0.2_2026-04-09_ko.docx"

pandoc "$MANUSCRIPT_DIR/manuscript_consistency_report_v0.2_2026-04-09.md" \
  -o "$MANUSCRIPT_DIR/manuscript_consistency_report_v0.2_2026-04-09.docx"

echo "manuscript_en_docx_path=docs/manuscript/v0.2_2026-04-09/manuscript_draft_v0.2_2026-04-09_en.docx"
echo "manuscript_ko_docx_path=docs/manuscript/v0.2_2026-04-09/manuscript_draft_v0.2_2026-04-09_ko.docx"
echo "consistency_report_docx_path=docs/manuscript/v0.2_2026-04-09/manuscript_consistency_report_v0.2_2026-04-09.docx"
