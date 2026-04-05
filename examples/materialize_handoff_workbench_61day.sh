#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  materialize_handoff_workbench_61day.sh <track> [workbench_name] [--dry-run] [--print-path]

Tracks:
  paper | presentation | portfolio | venue | delivery

Description:
  Create an editable workbench by copying one of the 61-day handoff kits/bundles
  into outputs/presentation_deck_outline_61day_2026-03-13/workbenches/.

Examples:
  materialize_handoff_workbench_61day.sh paper
  materialize_handoff_workbench_61day.sh presentation deck_v1
  materialize_handoff_workbench_61day.sh venue venue_icra_blind --dry-run
EOF
}

ROOT_DIR="/Users/seoki/Desktop/research"
OUTPUT_ROOT="${ROOT_DIR}/outputs/presentation_deck_outline_61day_2026-03-13"
WORKBENCH_ROOT="${OUTPUT_ROOT}/workbenches"

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 1
fi

TRACK="$1"
shift

WORKBENCH_NAME=""
DRY_RUN=0
PRINT_PATH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --print-path)
      PRINT_PATH=1
      shift
      ;;
    *)
      if [[ -z "${WORKBENCH_NAME}" ]]; then
        WORKBENCH_NAME="$1"
        shift
      else
        echo "Unexpected argument: $1" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

case "${TRACK}" in
  paper)
    SRC_DIR="${OUTPUT_ROOT}/paper_source_kit_61day"
    DEFAULT_NAME="paper_workbench_main_61day"
    ;;
  presentation)
    SRC_DIR="${OUTPUT_ROOT}/presentation_source_kit_61day"
    DEFAULT_NAME="presentation_workbench_main_61day"
    ;;
  portfolio)
    SRC_DIR="${OUTPUT_ROOT}/portfolio_source_kit_61day"
    DEFAULT_NAME="portfolio_workbench_main_61day"
    ;;
  venue)
    SRC_DIR="${OUTPUT_ROOT}/venue_ops_kit_61day"
    DEFAULT_NAME="venue_workbench_main_61day"
    ;;
  delivery)
    SRC_DIR="${OUTPUT_ROOT}/delivery_handoff_bundle_61day"
    DEFAULT_NAME="delivery_workbench_main_61day"
    ;;
  *)
    echo "Unsupported track: ${TRACK}" >&2
    usage >&2
    exit 1
    ;;
esac

WORKBENCH_NAME="${WORKBENCH_NAME:-$DEFAULT_NAME}"
DEST_DIR="${WORKBENCH_ROOT}/${WORKBENCH_NAME}"
NOTES_FILE="${DEST_DIR}/WORKBENCH_NOTES.md"

if [[ "${PRINT_PATH}" -eq 1 ]]; then
  echo "${DEST_DIR}"
  if [[ "${DRY_RUN}" -eq 0 ]]; then
    exit 0
  fi
fi

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "Source kit not found: ${SRC_DIR}" >&2
  exit 1
fi

if [[ -e "${DEST_DIR}" ]]; then
  echo "Workbench already exists: ${DEST_DIR}" >&2
  exit 1
fi

echo "Track: ${TRACK}"
echo "Source: ${SRC_DIR}"
echo "Destination: ${DEST_DIR}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  exit 0
fi

mkdir -p "${WORKBENCH_ROOT}"
cp -R "${SRC_DIR}" "${DEST_DIR}"

cat > "${NOTES_FILE}" <<EOF
# Workbench Notes

- Track: ${TRACK}
- Source kit: ${SRC_DIR}
- Workbench path: ${DEST_DIR}
- Created on: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Next Steps

1. Open the relevant runbook inside this workbench.
2. Make actual edits in this workbench, not in the archived source kit.
3. Keep reviewer-safe messaging from \`message_lock_sheet_61day.md\`.
EOF

echo "Created workbench: ${DEST_DIR}"
