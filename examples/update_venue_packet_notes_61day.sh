#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  update_venue_packet_notes_61day.sh <packet_dir> [options]

Options:
  --intake-status <value>
  --abstract-limit <value>
  --page-limit <value>
  --supplementary-allowed <value>
  --figure-format <value>
  --blind-review-policy <value>
  --camera-ready-metadata-ready <value>
  --final-output-file <value>

Examples:
  update_venue_packet_notes_61day.sh /path/to/packet \
    --intake-status "filled" \
    --abstract-limit "150 words" \
    --page-limit "8 pages"
EOF
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

PACKET_DIR="$1"
shift

NOTES_FILE="$PACKET_DIR/VENUE_PACKET_NOTES.md"
if [[ ! -f "$NOTES_FILE" ]]; then
  echo "Notes file not found: $NOTES_FILE" >&2
  exit 1
fi

keys=()
values=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --intake-status)
      keys+=("Intake status")
      values+=("$2")
      shift 2
      ;;
    --abstract-limit)
      keys+=("Abstract limit")
      values+=("$2")
      shift 2
      ;;
    --page-limit)
      keys+=("Page limit")
      values+=("$2")
      shift 2
      ;;
    --supplementary-allowed)
      keys+=("Supplementary allowed")
      values+=("$2")
      shift 2
      ;;
    --figure-format)
      keys+=("Figure format")
      values+=("$2")
      shift 2
      ;;
    --blind-review-policy)
      keys+=("Blind review policy")
      values+=("$2")
      shift 2
      ;;
    --camera-ready-metadata-ready)
      keys+=("Camera-ready metadata ready")
      values+=("$2")
      shift 2
      ;;
    --final-output-file)
      keys+=("Final output file")
      values+=("$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ${#keys[@]} -eq 0 ]]; then
  echo "No updates provided." >&2
  usage
  exit 1
fi

i=0
while [[ $i -lt ${#keys[@]} ]]; do
  key="${keys[$i]}"
  value="${values[$i]}"
  perl -0pi -e "s/^\\- \\Q${key}\\E:\\s*\$/- ${key}: ${value}/m" "$NOTES_FILE"
  i=$((i + 1))
done

echo "Updated notes:"
echo "  $NOTES_FILE"
