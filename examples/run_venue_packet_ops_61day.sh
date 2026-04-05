#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_venue_packet_ops_61day.sh [--packets-root <dir>] [--no-dashboard] <packet_dir>

Examples:
  run_venue_packet_ops_61day.sh /path/to/venue_packet
  run_venue_packet_ops_61day.sh --packets-root /path/to/venue_packets /path/to/venue_packet
  run_venue_packet_ops_61day.sh --no-dashboard /path/to/venue_packet

Exit codes:
  0  validation PASS and readiness READY
  1  validation FAIL
  2  validation PASS but readiness NOT_READY
EOF
}

ROOT="/Users/seoki/Desktop/research"
VALIDATOR="$ROOT/examples/validate_venue_packet_61day.sh"
READINESS="$ROOT/examples/assess_venue_packet_readiness_61day.sh"
DASHBOARD="$ROOT/examples/summarize_venue_packets_61day.sh"

PACKETS_ROOT=""
NO_DASHBOARD=0
POSITIONAL=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --packets-root)
      PACKETS_ROOT="$2"
      shift 2
      ;;
    --no-dashboard)
      NO_DASHBOARD=1
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

if [[ -z "$PACKETS_ROOT" ]]; then
  PACKETS_ROOT="$(dirname "$PACKET_DIR")"
fi

if [[ ! -d "$PACKETS_ROOT" ]]; then
  echo "Packets root not found: $PACKETS_ROOT" >&2
  exit 1
fi

validation_status="UNKNOWN"
readiness_status="UNKNOWN"
dashboard_report_path=""

set +e
validation_output="$("$VALIDATOR" --write-report "$PACKET_DIR" 2>&1)"
validation_exit=$?
set -e
validation_status="$(printf '%s\n' "$validation_output" | awk -F': ' '/^Status:/ {print $2; exit}')"
[[ -n "$validation_status" ]] || validation_status="UNKNOWN"

set +e
readiness_output="$("$READINESS" --write-report "$PACKET_DIR" 2>&1)"
readiness_exit=$?
set -e
readiness_status="$(printf '%s\n' "$readiness_output" | awk -F': ' '/^Status:/ {print $2; exit}')"
[[ -n "$readiness_status" ]] || readiness_status="UNKNOWN"

if [[ "$NO_DASHBOARD" -eq 0 ]]; then
  dashboard_output="$("$DASHBOARD" --write-report "$PACKETS_ROOT")"
  dashboard_report_path="$(printf '%s\n' "$dashboard_output" | awk -F': ' '/^Report:/ {print $2; exit}')"
fi

packet_name="$(basename "$PACKET_DIR")"
validation_report="$PACKET_DIR/VENUE_PACKET_VALIDATION.md"
readiness_report="$PACKET_DIR/VENUE_PACKET_READINESS.md"

echo "Packet: $packet_name"
echo "Validation: $validation_status"
echo "Readiness: $readiness_status"
echo "Validation report: $validation_report"
echo "Readiness report: $readiness_report"
if [[ -n "$dashboard_report_path" ]]; then
  echo "Dashboard report: $dashboard_report_path"
fi

if [[ "$validation_exit" -ne 0 ]]; then
  exit 1
fi

if [[ "$readiness_exit" -ne 0 ]]; then
  exit 2
fi

exit 0
