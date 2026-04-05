#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
PAIR_WORKFLOW="$ROOT/examples/start_venue_pair_workflow_61day.sh"
PAIR_COMPILE="$ROOT/examples/compile_venue_pair_manuscript_bundle_61day.sh"
RUNBOOK="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13/final_operator_runbook_61day.md"

usage() {
  cat <<'EOF'
Usage:
  run_venue_pair_preflight_61day.sh [--dry-run] [--reuse-existing] <venue_slug>

Examples:
  run_venue_pair_preflight_61day.sh maritime_ai_conf
  run_venue_pair_preflight_61day.sh --reuse-existing applied_conf_default
  run_venue_pair_preflight_61day.sh --dry-run maritime_ai_conf
EOF
}

DRY_RUN=0
REUSE_EXISTING=0
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --reuse-existing)
      REUSE_EXISTING=1
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
  if [[ "$REUSE_EXISTING" -eq 1 ]]; then
    echo "Would reuse existing venue packets for:"
    echo "  $VENUE_SLUG"
  else
    echo "Would run:"
    echo "  bash $PAIR_WORKFLOW --dry-run $VENUE_SLUG"
  fi
  echo
  echo "Would then compile:"
  echo "  bash $PAIR_COMPILE --dry-run $VENUE_SLUG"
  echo
  echo "Operator runbook:"
  echo "  $RUNBOOK"
  exit 0
fi

if [[ "$REUSE_EXISTING" -eq 1 ]]; then
  echo "Reusing existing venue packet pair:"
  echo "  ${VENUE_SLUG}_blind_61day"
  echo "  ${VENUE_SLUG}_camera-ready_61day"
else
  bash "$PAIR_WORKFLOW" "$VENUE_SLUG"
fi
echo
bash "$PAIR_COMPILE" "$VENUE_SLUG"
echo
echo "Operator runbook:"
echo "  $RUNBOOK"
