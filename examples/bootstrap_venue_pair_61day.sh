#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
BOOTSTRAP="$ROOT/examples/bootstrap_venue_binding_61day.sh"

usage() {
  cat <<'EOF'
Usage:
  bootstrap_venue_pair_61day.sh [--dry-run] <venue_slug>

Arguments:
  venue_slug   Short venue identifier

Examples:
  bootstrap_venue_pair_61day.sh maritime_ai_conf
  bootstrap_venue_pair_61day.sh --dry-run maritime_ai_conf
EOF
}

DRY_RUN=0
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
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

if [[ ${#POSITIONAL[@]} -lt 1 ]]; then
  usage
  exit 1
fi

VENUE_SLUG="${POSITIONAL[0]}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run only."
  echo "Would bootstrap blind packet:"
  echo "  bash $BOOTSTRAP --dry-run $VENUE_SLUG blind"
  echo
  echo "Would bootstrap camera-ready packet:"
  echo "  bash $BOOTSTRAP --dry-run $VENUE_SLUG camera-ready"
  exit 0
fi

bash "$BOOTSTRAP" "$VENUE_SLUG" blind
echo
bash "$BOOTSTRAP" "$VENUE_SLUG" camera-ready
echo
echo "Venue pair bootstrapped:"
echo "  ${VENUE_SLUG}_blind_61day"
echo "  ${VENUE_SLUG}_camera-ready_61day"
