#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
PAIR_BOOTSTRAP="$ROOT/examples/bootstrap_venue_pair_61day.sh"
PAIR_OPEN="$ROOT/examples/open_venue_pair_packet_61day.sh"
PAIR_OPEN_BUNDLE="$ROOT/examples/open_venue_pair_manuscript_bundle_61day.sh"
RUNBOOK="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13/final_operator_runbook_61day.md"

usage() {
  cat <<'EOF'
Usage:
  start_venue_pair_workflow_61day.sh [--dry-run] <venue_slug>

Examples:
  start_venue_pair_workflow_61day.sh maritime_ai_conf
  start_venue_pair_workflow_61day.sh --dry-run maritime_ai_conf
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
  echo "Would run:"
  echo "  bash $PAIR_BOOTSTRAP --dry-run $VENUE_SLUG"
  echo
  echo "Would then open:"
  echo "  bash $PAIR_OPEN $VENUE_SLUG"
  echo "  bash $PAIR_OPEN_BUNDLE $VENUE_SLUG"
  echo
  echo "Operator runbook:"
  echo "  $RUNBOOK"
  exit 0
fi

bash "$PAIR_BOOTSTRAP" "$VENUE_SLUG"
echo
bash "$PAIR_OPEN" "$VENUE_SLUG"
echo
bash "$PAIR_OPEN_BUNDLE" "$VENUE_SLUG"
echo
echo "Operator runbook:"
echo "  $RUNBOOK"
