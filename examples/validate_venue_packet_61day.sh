#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  validate_venue_packet_61day.sh [--write-report] <packet_dir>

Examples:
  validate_venue_packet_61day.sh /path/to/venue_packet
  validate_venue_packet_61day.sh --write-report /path/to/venue_packet
EOF
}

WRITE_REPORT=0
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --write-report)
      WRITE_REPORT=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

if [[ ${#POSITIONAL[@]} -ne 1 ]]; then
  usage
  exit 1
fi

PACKET_DIR="${POSITIONAL[0]}"

if [[ ! -d "$PACKET_DIR" ]]; then
  echo "Packet directory not found: $PACKET_DIR" >&2
  exit 1
fi

required_files=(
  "SUBMISSION_READY_BUNDLE_MANIFEST.md"
  "VENUE_PACKET_NOTES.md"
  "paper_conference_8page_final_pass_61day_en.md"
  "paper_conference_8page_final_pass_61day.tex"
  "table_final_bundle_61day.md"
  "conference_print_assets_manifest_61day.md"
  "submission_portal_copy_paste_sheet_61day.md"
  "blind_review_compliance_checklist_61day.md"
  "submission_final_qc_checklist_61day.md"
  "blind_submission_final_pass_61day.md"
  "camera_ready_final_pass_61day.md"
  "anonymous_wording_final_pass_61day.md"
  "camera_ready_metadata_fill_pack_61day.md"
  "anonymous_submission_portal_variants_61day.md"
  "camera_ready_front_matter_template_61day.md"
  "camera_ready_metadata_fill_template_61day.json"
  "target_venue_intake_sheet_61day.md"
  "venue_specific_adaptation_runbook_61day.md"
  "venue_packet_build_sheet_61day.md"
  "prepare_venue_packet_61day.sh"
)

missing=()
for rel in "${required_files[@]}"; do
  if [[ ! -e "$PACKET_DIR/$rel" ]]; then
    missing+=("$rel")
  fi
done

asset_dir="$PACKET_DIR/assets"
asset_count=0
if [[ -d "$asset_dir" ]]; then
  asset_count="$(find "$asset_dir" -maxdepth 1 -type f | wc -l | tr -d ' ')"
fi

notes_file="$PACKET_DIR/VENUE_PACKET_NOTES.md"
notes_checks=(
  "Intake status:"
  "Abstract limit:"
  "Page limit:"
  "Supplementary allowed:"
  "Figure format:"
  "Blind review policy:"
  "Camera-ready metadata ready:"
  "Final output file:"
)

missing_notes=()
if [[ -f "$notes_file" ]]; then
  for pattern in "${notes_checks[@]}"; do
    if ! rg -q "^[-] ${pattern}" "$notes_file"; then
      missing_notes+=("$pattern")
    fi
  done
else
  missing_notes+=("VENUE_PACKET_NOTES.md missing")
fi

status="PASS"
if [[ ${#missing[@]} -gt 0 || "$asset_count" -lt 1 || ${#missing_notes[@]} -gt 0 ]]; then
  status="FAIL"
fi

report_path="$PACKET_DIR/VENUE_PACKET_VALIDATION.md"
if [[ "$WRITE_REPORT" -eq 1 ]]; then
  {
    echo "# Venue Packet Validation"
    echo
    echo "- Status: \`$status\`"
    echo "- Packet: \`$PACKET_DIR\`"
    echo "- Asset file count: \`$asset_count\`"
    echo
    echo "## Missing required files"
    if [[ ${#missing[@]} -eq 0 ]]; then
      echo "- none"
    else
      for item in "${missing[@]}"; do
        echo "- $item"
      done
    fi
    echo
    echo "## Missing notes fields"
    if [[ ${#missing_notes[@]} -eq 0 ]]; then
      echo "- none"
    else
      for item in "${missing_notes[@]}"; do
        echo "- $item"
      done
    fi
  } > "$report_path"
fi

echo "Status: $status"
echo "Packet: $PACKET_DIR"
echo "Asset file count: $asset_count"
echo "Missing required files: ${#missing[@]}"
echo "Missing notes fields: ${#missing_notes[@]}"

if [[ "$WRITE_REPORT" -eq 1 ]]; then
  echo "Report: $report_path"
fi

if [[ "$status" != "PASS" ]]; then
  exit 1
fi
