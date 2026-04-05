#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  summarize_venue_packets_61day.sh [--write-report] [venue_packets_root]

Examples:
  summarize_venue_packets_61day.sh
  summarize_venue_packets_61day.sh --write-report
  summarize_venue_packets_61day.sh --write-report /path/to/venue_packets
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

ROOT_DEFAULT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/venue_packets"
PACKETS_ROOT="${POSITIONAL[0]:-$ROOT_DEFAULT}"

if [[ ! -d "$PACKETS_ROOT" ]]; then
  echo "Venue packets root not found: $PACKETS_ROOT" >&2
  exit 1
fi

VALIDATOR="/Users/seoki/Desktop/research/examples/validate_venue_packet_61day.sh"
READINESS="/Users/seoki/Desktop/research/examples/assess_venue_packet_readiness_61day.sh"

packet_dirs=()
while IFS= read -r dir; do
  packet_dirs+=("$dir")
done < <(find "$PACKETS_ROOT" -maxdepth 1 -mindepth 1 -type d | sort)

report_lines=()
report_lines+=("# Venue Packet Dashboard")
report_lines+=("")
report_lines+=("- Root: \`$PACKETS_ROOT\`")
report_lines+=("- Packet count: \`${#packet_dirs[@]}\`")
report_lines+=("")
report_lines+=("| packet | mode | validation | readiness | assets | bundle | notes |")
report_lines+=("|---|---|---|---|---:|---|---|")

for packet_dir in "${packet_dirs[@]}"; do
  packet_name="$(basename "$packet_dir")"
  notes_file="$packet_dir/VENUE_PACKET_NOTES.md"

  mode="unknown"
  if [[ -f "$notes_file" ]]; then
    mode_line="$(rg -N "^- Mode:" "$notes_file" || true)"
    if [[ -n "$mode_line" ]]; then
      mode="${mode_line#*: }"
      mode="${mode//\`/}"
    fi
  fi

  validation_output="$("$VALIDATOR" "$packet_dir" 2>/dev/null || true)"
  validation_status="$(printf '%s\n' "$validation_output" | awk -F': ' '/^Status:/ {print $2; exit}')"
  [[ -n "$validation_status" ]] || validation_status="UNKNOWN"

  readiness_output="$("$READINESS" "$packet_dir" 2>/dev/null || true)"
  readiness_status="$(printf '%s\n' "$readiness_output" | awk -F': ' '/^Status:/ {print $2; exit}')"
  [[ -n "$readiness_status" ]] || readiness_status="UNKNOWN"

  asset_count="0"
  if [[ -d "$packet_dir/assets" ]]; then
    asset_count="$(find "$packet_dir/assets" -maxdepth 1 -type f | wc -l | tr -d ' ')"
  fi

  bundle_state="missing"
  if [[ -d "$packet_dir/manuscript_bundle_61day" ]]; then
    bundle_state="ready"
  fi

  notes_state="missing"
  if [[ -f "$notes_file" ]]; then
    if [[ "$readiness_status" == "READY" ]]; then
      notes_state="ready"
    elif rg -q "^[-] Intake status:[[:space:]]*$" "$notes_file"; then
      notes_state="blank"
    else
      notes_state="started"
    fi
  fi

  report_lines+=("| \`$packet_name\` | \`$mode\` | \`$validation_status\` | \`$readiness_status\` | $asset_count | \`$bundle_state\` | \`$notes_state\` |")
done

report_content="$(printf '%s\n' "${report_lines[@]}")"
printf '%s\n' "$report_content"

if [[ "$WRITE_REPORT" -eq 1 ]]; then
  report_path="$PACKETS_ROOT/venue_packet_dashboard_61day.md"
  printf '%s\n' "$report_content" > "$report_path"
  echo
  echo "Report: $report_path"
fi
