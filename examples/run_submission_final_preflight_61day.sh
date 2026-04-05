#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"
CERT="$ROOT/submission_readiness_certificate_61day.md"
STRICT="$ROOT/submission_metadata_strict_audit_61day.md"
REAL_VALUE="$ROOT/submission_metadata_real_value_gate_61day.md"

REQUIRE_REAL_VALUES=false
if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [--require-real-values]" >&2
  exit 2
fi
if [[ $# -eq 1 ]]; then
  if [[ "$1" == "--require-real-values" ]]; then
    REQUIRE_REAL_VALUES=true
  else
    echo "Usage: $0 [--require-real-values]" >&2
    exit 2
  fi
fi

bash /Users/seoki/Desktop/research/examples/run_submission_readiness_certificate_61day.sh
bash /Users/seoki/Desktop/research/examples/run_submission_metadata_strict_audit_61day.sh

real_value_status="ADVISORY_ONLY"
if [[ "$REQUIRE_REAL_VALUES" == "true" ]]; then
  if bash /Users/seoki/Desktop/research/examples/run_submission_metadata_real_value_gate_61day.sh; then
    :
  fi
  real_value_status="$(sed -n 's/^- Status: `\([^`]*\)`/\1/p' "$REAL_VALUE" | head -n 1)"
fi

cert_status="$(sed -n 's/^- Certificate status: `\([^`]*\)`/\1/p' "$CERT" | head -n 1)"
strict_status="$(sed -n 's/^- Status: `\([^`]*\)`/\1/p' "$STRICT" | head -n 1)"

echo
echo "Final preflight summary:"
echo "  certificate: ${cert_status:-UNKNOWN}"
echo "  strict_audit: ${strict_status:-UNKNOWN}"
if [[ "$REQUIRE_REAL_VALUES" == "true" ]]; then
  echo "  real_value_gate: ${real_value_status:-UNKNOWN}"
else
  echo "  real_value_gate: ADVISORY_ONLY (use --require-real-values to enforce)"
fi

if [[ "${cert_status:-}" == "VALID" && "${strict_status:-}" == "PASS" \
   && ( "$REQUIRE_REAL_VALUES" != "true" || "${real_value_status:-}" == "PASS" ) ]]; then
  echo "Overall status: PASS"
  exit 0
fi

echo "Overall status: HOLD"
echo "Fix remaining issues before final submission."
exit 1
