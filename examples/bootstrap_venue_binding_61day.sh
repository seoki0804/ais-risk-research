#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_ROOT="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"
PREPARE="$ROOT/examples/prepare_venue_packet_61day.sh"
VALIDATE="$ROOT/examples/validate_venue_packet_61day.sh"
READY="$ROOT/examples/assess_venue_packet_readiness_61day.sh"
DEFAULT_INTAKE="$OUT_ROOT/target_venue_intake_applied_conference_default_61day.md"
BIND_MANUSCRIPT="$ROOT/examples/bind_packet_manuscript_61day.py"

usage() {
  cat <<'EOF'
Usage:
  bootstrap_venue_binding_61day.sh [--dry-run] <venue_slug> [mode]

Arguments:
  venue_slug   Short venue identifier
  mode         blind | camera-ready | journal | internal

Examples:
  bootstrap_venue_binding_61day.sh maritime_ai_conf blind
  bootstrap_venue_binding_61day.sh ocean_journal journal
  bootstrap_venue_binding_61day.sh --dry-run maritime_ai_conf blind
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
MODE="${POSITIONAL[1]:-blind}"
PACKET_DIR="$OUT_ROOT/venue_packets/${VENUE_SLUG}_${MODE}_61day"

case "$MODE" in
  blind|camera-ready|journal|internal)
    ;;
  *)
    echo "Unsupported mode: $MODE" >&2
    usage
    exit 1
    ;;
esac

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "Dry run only."
  echo "Would create packet:"
  echo "  $PACKET_DIR"
  echo
  echo "Would run:"
  echo "  bash $PREPARE $VENUE_SLUG $MODE"
  echo
  echo "Would write packet-local intake bootstrap:"
  echo "  $PACKET_DIR/TARGET_VENUE_INTAKE_BOOTSTRAP_61day.md"
  echo
  echo "Would fill notes defaults from:"
  echo "  $DEFAULT_INTAKE"
  echo
  echo "Would then run:"
  echo "  bash $VALIDATE --write-report $PACKET_DIR"
  echo "  bash $READY --write-report $PACKET_DIR"
  echo "  python $BIND_MANUSCRIPT $PACKET_DIR $MODE"
  exit 0
fi

bash "$PREPARE" "$VENUE_SLUG" "$MODE" >/dev/null

cat > "$PACKET_DIR/TARGET_VENUE_INTAKE_BOOTSTRAP_61day.md" <<EOF
# Target Venue Intake Bootstrap 61day

This packet was bootstrapped from the default applied-conference assumptions.

Source:
- $DEFAULT_INTAKE

Packet:
- $PACKET_DIR

Mode:
- $MODE

Recommended next step:
1. Replace these defaults with the real venue policy when available.
2. Re-run validation and readiness after any venue-specific edits.
EOF

if [[ "$MODE" == "blind" ]]; then
  perl -0pi -e 's/- Intake status:\n- Abstract limit:\n- Page limit:\n- Supplementary allowed:\n- Figure format:\n- Blind review policy:\n- Camera-ready metadata ready:\n- Final output file:\n/- Intake status: bootstrapped from default applied-conference intake\n- Abstract limit: 250 words\n- Page limit: 8 pages plus references\n- Supplementary allowed: yes, separate upload\n- Figure format: PDF preferred, PNG fallback\n- Blind review policy: double-blind, anonymized self-citation, no repository link in submission\n- Camera-ready metadata ready: not applicable for this blind packet\n- Final output file: '"$VENUE_SLUG"'_'"$MODE"'_61day\n/s' "$PACKET_DIR/VENUE_PACKET_NOTES.md"
else
  perl -0pi -e 's/- Intake status:\n- Abstract limit:\n- Page limit:\n- Supplementary allowed:\n- Figure format:\n- Blind review policy:\n- Camera-ready metadata ready:\n- Final output file:\n/- Intake status: bootstrapped from default applied-conference intake\n- Abstract limit: 250 words\n- Page limit: 8 pages plus references\n- Supplementary allowed: yes, separate upload\n- Figure format: PDF preferred, PNG fallback\n- Blind review policy: follow real venue policy\n- Camera-ready metadata ready: fill with real author, funding, and COI values\n- Final output file: '"$VENUE_SLUG"'_'"$MODE"'_61day\n/s' "$PACKET_DIR/VENUE_PACKET_NOTES.md"
fi

bash "$VALIDATE" --write-report "$PACKET_DIR" >/dev/null
bash "$READY" --write-report "$PACKET_DIR" >/dev/null
python "$BIND_MANUSCRIPT" "$PACKET_DIR" "$MODE" >/dev/null

echo "Bootstrapped packet:"
echo "  $PACKET_DIR"
echo
echo "Validation/readiness reports:"
echo "  $PACKET_DIR/VENUE_PACKET_VALIDATION.md"
echo "  $PACKET_DIR/VENUE_PACKET_READINESS.md"
echo "  $PACKET_DIR/manuscript_bundle_61day"
echo
echo "Next:"
echo "  1. Edit $PACKET_DIR/TARGET_VENUE_INTAKE_BOOTSTRAP_61day.md"
echo "  2. Edit $PACKET_DIR/VENUE_PACKET_NOTES.md"
echo "  3. Edit $PACKET_DIR/manuscript_bundle_61day"
echo "  4. Apply real venue policy and rerun validation/readiness"
