#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  assess_venue_packet_readiness_61day.sh [--write-report] <packet_dir>

Examples:
  assess_venue_packet_readiness_61day.sh /path/to/venue_packet
  assess_venue_packet_readiness_61day.sh --write-report /path/to/venue_packet
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

validation_file="$PACKET_DIR/VENUE_PACKET_VALIDATION.md"
notes_file="$PACKET_DIR/VENUE_PACKET_NOTES.md"

if [[ ! -f "$notes_file" ]]; then
  echo "Notes file not found: $notes_file" >&2
  exit 1
fi

field_labels=(
  "Intake status"
  "Abstract limit"
  "Page limit"
  "Supplementary allowed"
  "Figure format"
  "Blind review policy"
  "Camera-ready metadata ready"
  "Final output file"
)

incomplete_fields=()
for label in "${field_labels[@]}"; do
  line="$(rg -n "^[-] ${label}:" "$notes_file" -N || true)"
  if [[ -z "$line" ]]; then
    incomplete_fields+=("$label (missing line)")
    continue
  fi
  value="${line#*:}"
  value="$(printf '%s' "$value" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')"
  if [[ -z "$value" ]]; then
    incomplete_fields+=("$label")
  fi
done

validation_status="missing"
if [[ -f "$validation_file" ]]; then
  if rg -q '^- Status: `PASS`' "$validation_file"; then
    validation_status="PASS"
  else
    validation_status="FAIL"
  fi
fi

readiness_status="READY"
if [[ "$validation_status" != "PASS" || ${#incomplete_fields[@]} -gt 0 ]]; then
  readiness_status="NOT_READY"
fi

report_path="$PACKET_DIR/VENUE_PACKET_READINESS.md"
if [[ "$WRITE_REPORT" -eq 1 ]]; then
  {
    echo "# Venue Packet Readiness"
    echo
    echo "- Status: \`$readiness_status\`"
    echo "- Packet: \`$PACKET_DIR\`"
    echo "- Validation prerequisite: \`$validation_status\`"
    echo
    echo "## Incomplete notes fields"
    if [[ ${#incomplete_fields[@]} -eq 0 ]]; then
      echo "- none"
    else
      for item in "${incomplete_fields[@]}"; do
        echo "- $item"
      done
    fi
  } > "$report_path"
fi

echo "Status: $readiness_status"
echo "Packet: $PACKET_DIR"
echo "Validation prerequisite: $validation_status"
echo "Incomplete notes fields: ${#incomplete_fields[@]}"

if [[ "$WRITE_REPORT" -eq 1 ]]; then
  echo "Report: $report_path"
fi

if [[ "$readiness_status" != "READY" ]]; then
  exit 1
fi
