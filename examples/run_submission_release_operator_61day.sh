#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"
SNAP_ROOT="$ROOT/submission_release_snapshots_61day"
CERT="$ROOT/submission_readiness_certificate_61day.md"
STRICT="$ROOT/submission_metadata_strict_audit_61day.md"
REAL_VALUE="$ROOT/submission_metadata_real_value_gate_61day.md"
VERIFY="$ROOT/submission_release_snapshot_verify_latest_61day.md"
OPERATOR_OUT="$ROOT/submission_release_operator_latest_61day.md"

STRICT_FLAG=""
REQUIRE_REAL_VALUES=false
RUN_MODE_PARTS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict-source-match)
      STRICT_FLAG="--strict-source-match"
      RUN_MODE_PARTS+=("strict-source-match")
      ;;
    --require-real-values)
      REQUIRE_REAL_VALUES=true
      RUN_MODE_PARTS+=("require-real-values")
      ;;
    *)
      echo "Usage: $0 [--strict-source-match] [--require-real-values]" >&2
      exit 2
      ;;
  esac
  shift
done

RUN_MODE="default"
if [[ "${#RUN_MODE_PARTS[@]}" -gt 0 ]]; then
  RUN_MODE="$(IFS=+; echo "${RUN_MODE_PARTS[*]}")"
fi

echo "Submission release operator run:"
echo "  1) final preflight gate"
echo "  2) release snapshot freeze"
echo "  3) release snapshot verification"
echo

if [[ "$REQUIRE_REAL_VALUES" == "true" ]]; then
  bash /Users/seoki/Desktop/research/examples/run_submission_final_preflight_61day.sh \
    --require-real-values
else
  bash /Users/seoki/Desktop/research/examples/run_submission_final_preflight_61day.sh
fi
bash /Users/seoki/Desktop/research/examples/create_submission_release_snapshot_61day.sh --skip-preflight
bash /Users/seoki/Desktop/research/examples/run_verify_submission_release_snapshot_61day.sh $STRICT_FLAG

latest_snapshot="$(
  find "$SNAP_ROOT" -maxdepth 1 -mindepth 1 -type d -name '20??????_??????' | sort | tail -n 1
)"

if [[ -z "${latest_snapshot:-}" ]]; then
  echo "Unable to locate latest snapshot directory under: $SNAP_ROOT" >&2
  exit 1
fi

latest_zip="${latest_snapshot}.zip"

cert_status="$(sed -n 's/^- Certificate status: `\([^`]*\)`/\1/p' "$CERT" | head -n 1)"
strict_status="$(sed -n 's/^- Status: `\([^`]*\)`/\1/p' "$STRICT" | head -n 1)"
real_value_status="$(sed -n 's/^- Status: `\([^`]*\)`/\1/p' "$REAL_VALUE" | head -n 1)"
verify_integrity="$(sed -n 's/^- Snapshot integrity: `\([^`]*\)`/\1/p' "$VERIFY" | head -n 1)"
verify_drift="$(sed -n 's/^- Source drift check: `\([^`]*\)`/\1/p' "$VERIFY" | head -n 1)"
verify_overall="$(sed -n 's/^- Overall status: `\([^`]*\)`/\1/p' "$VERIFY" | head -n 1)"

echo
echo "Submission release operator summary:"
echo "  certificate: ${cert_status:-UNKNOWN}"
echo "  strict_audit: ${strict_status:-UNKNOWN}"
if [[ "$REQUIRE_REAL_VALUES" == "true" ]]; then
  echo "  real_value_gate: ${real_value_status:-UNKNOWN}"
else
  echo "  real_value_gate: ADVISORY_ONLY"
fi
echo "  snapshot_integrity: ${verify_integrity:-UNKNOWN}"
echo "  source_drift: ${verify_drift:-UNKNOWN}"
echo "  snapshot_verify: ${verify_overall:-UNKNOWN}"
echo
echo "Key artifacts:"
echo "  readiness_certificate: $CERT"
echo "  strict_audit_report:   $STRICT"
echo "  snapshot_dir:          $latest_snapshot"
echo "  snapshot_zip:          $latest_zip"
echo "  snapshot_verify:       $VERIFY"
echo "  operator_report:       $OPERATOR_OUT"

operator_status="HOLD"
if [[ "${cert_status:-}" == "VALID" \
   && "${strict_status:-}" == "PASS" \
   && ( "$REQUIRE_REAL_VALUES" != "true" || "${real_value_status:-}" == "PASS" ) \
   && "${verify_overall:-}" == "PASS" ]]; then
  operator_status="PASS"
fi

{
  echo "# Submission Release Operator Summary 61day"
  echo
  echo "- Generated: \`$(date '+%Y-%m-%dT%H:%M:%S%z')\`"
  echo "- Run mode: \`$RUN_MODE\`"
  echo "- Certificate: \`${cert_status:-UNKNOWN}\`"
  echo "- Strict metadata audit: \`${strict_status:-UNKNOWN}\`"
  if [[ "$REQUIRE_REAL_VALUES" == "true" ]]; then
    echo "- Real-value metadata gate: \`${real_value_status:-UNKNOWN}\`"
  else
    echo "- Real-value metadata gate: \`ADVISORY_ONLY\`"
  fi
  echo "- Snapshot integrity: \`${verify_integrity:-UNKNOWN}\`"
  echo "- Source drift: \`${verify_drift:-UNKNOWN}\`"
  echo "- Snapshot verification: \`${verify_overall:-UNKNOWN}\`"
  echo "- Overall status: \`$operator_status\`"
  echo
  echo "## Key Artifacts"
  echo "- Readiness certificate: \`$CERT\`"
  echo "- Strict audit report: \`$STRICT\`"
  echo "- Real-value gate report: \`$REAL_VALUE\`"
  echo "- Snapshot directory: \`$latest_snapshot\`"
  echo "- Snapshot zip: \`$latest_zip\`"
  echo "- Snapshot verification: \`$VERIFY\`"
  echo "- Operator report: \`$OPERATOR_OUT\`"
} > "$OPERATOR_OUT"

if [[ "$operator_status" == "PASS" ]]; then
  echo "Overall status: PASS"
  exit 0
fi

echo "Overall status: HOLD"
echo "Check status lines above before final submission."
exit 1
