#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_ROOT="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"
PACK="$OUT_ROOT/external_binding_handoff_pack_61day"

REPORT="$OUT_ROOT/submission_release_regression_suite_61day.md"

ROOT_OPERATOR="$OUT_ROOT/submission_release_operator_latest_61day.md"
ROOT_SNAPSHOT="$OUT_ROOT/submission_release_snapshot_verify_latest_61day.md"
REAL_VALUE_GATE="$OUT_ROOT/submission_metadata_real_value_gate_61day.md"
PACK_OPERATOR="$PACK/submission_release_operator_latest_61day.md"
PACK_SNAPSHOT="$PACK/submission_release_snapshot_verify_latest_61day.md"

STRICT_REAL_VALUES=false
if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [--strict-real-values]" >&2
  exit 2
fi
if [[ $# -eq 1 ]]; then
  if [[ "$1" == "--strict-real-values" ]]; then
    STRICT_REAL_VALUES=true
  else
    echo "Usage: $0 [--strict-real-values]" >&2
    exit 2
  fi
fi

status_refresh="FAIL"
status_pack_verify="FAIL"
status_real_value_refresh="FAIL"

if bash "$ROOT/examples/run_submission_metadata_real_value_gate_61day.sh"; then
  status_real_value_refresh="PASS"
else
  status_real_value_refresh="HOLD"
fi

if bash "$ROOT/examples/refresh_external_binding_handoff_pack_61day.sh"; then
  status_refresh="PASS"
fi

if bash "$PACK/VERIFY_PACK_61day.sh"; then
  status_pack_verify="PASS"
fi

operator_overall="$(sed -n 's/^- Overall status: `\([^`]*\)`/\1/p' "$ROOT_OPERATOR" | head -n 1)"
snapshot_integrity="$(sed -n 's/^- Snapshot integrity: `\([^`]*\)`/\1/p' "$ROOT_SNAPSHOT" | head -n 1)"
snapshot_drift="$(sed -n 's/^- Source drift check: `\([^`]*\)`/\1/p' "$ROOT_SNAPSHOT" | head -n 1)"
snapshot_overall="$(sed -n 's/^- Overall status: `\([^`]*\)`/\1/p' "$ROOT_SNAPSHOT" | head -n 1)"
real_value_status="$(sed -n 's/^- Status: `\([^`]*\)`/\1/p' "$REAL_VALUE_GATE" | head -n 1)"
real_value_blockers="$(sed -n 's/^- Blocker count: `\([^`]*\)`/\1/p' "$REAL_VALUE_GATE" | head -n 1)"

root_operator_hash="$(shasum -a 256 "$ROOT_OPERATOR" | awk '{print $1}')"
pack_operator_hash="$(shasum -a 256 "$PACK_OPERATOR" | awk '{print $1}')"
root_snapshot_hash="$(shasum -a 256 "$ROOT_SNAPSHOT" | awk '{print $1}')"
pack_snapshot_hash="$(shasum -a 256 "$PACK_SNAPSHOT" | awk '{print $1}')"

status_operator_copy="FAIL"
status_snapshot_copy="FAIL"
if [[ "$root_operator_hash" == "$pack_operator_hash" ]]; then
  status_operator_copy="PASS"
fi
if [[ "$root_snapshot_hash" == "$pack_snapshot_hash" ]]; then
  status_snapshot_copy="PASS"
fi

overall="PASS"
if [[ "$status_refresh" != "PASS" ]]; then
  overall="HOLD"
fi
if [[ "$status_pack_verify" != "PASS" ]]; then
  overall="HOLD"
fi
if [[ "${operator_overall:-}" != "PASS" ]]; then
  overall="HOLD"
fi
if [[ "${snapshot_integrity:-}" != "PASS" ]]; then
  overall="HOLD"
fi
if [[ "${snapshot_drift:-}" != "MATCH" ]]; then
  overall="HOLD"
fi
if [[ "${snapshot_overall:-}" != "PASS" ]]; then
  overall="HOLD"
fi
if [[ "$status_operator_copy" != "PASS" ]]; then
  overall="HOLD"
fi
if [[ "$status_snapshot_copy" != "PASS" ]]; then
  overall="HOLD"
fi
if [[ "$STRICT_REAL_VALUES" == "true" && "${real_value_status:-}" != "PASS" ]]; then
  overall="HOLD"
fi

strict_real_value_result="ADVISORY_ONLY"
if [[ "$STRICT_REAL_VALUES" == "true" ]]; then
  if [[ "${real_value_status:-}" == "PASS" ]]; then
    strict_real_value_result="PASS"
  else
    strict_real_value_result="HOLD"
  fi
fi

{
  echo "# Submission Release Regression Suite 61day"
  echo
  echo "- Generated: \`$(date '+%Y-%m-%dT%H:%M:%S%z')\`"
  if [[ "$STRICT_REAL_VALUES" == "true" ]]; then
    echo "- Run mode: \`strict-real-values\`"
  else
    echo "- Run mode: \`default\`"
  fi
  echo "- Overall status: \`$overall\`"
  echo
  echo "## Suite Checks"
  echo "| Check | Result | Note |"
  echo "|---|---|---|"
  echo "| real-value gate refresh | \`$status_real_value_refresh\` | \`run_submission_metadata_real_value_gate_61day.sh\` |"
  echo "| refresh external handoff pack | \`$status_refresh\` | \`refresh_external_binding_handoff_pack_61day.sh\` |"
  echo "| pack-local verifier | \`$status_pack_verify\` | \`external_binding_handoff_pack_61day/VERIFY_PACK_61day.sh\` |"
  echo "| root operator report status | \`${operator_overall:-UNKNOWN}\` | \`submission_release_operator_latest_61day.md\` |"
  echo "| root snapshot integrity | \`${snapshot_integrity:-UNKNOWN}\` | \`submission_release_snapshot_verify_latest_61day.md\` |"
  echo "| root snapshot drift | \`${snapshot_drift:-UNKNOWN}\` | expected \`MATCH\` |"
  echo "| root snapshot overall | \`${snapshot_overall:-UNKNOWN}\` | \`submission_release_snapshot_verify_latest_61day.md\` |"
  echo "| real-value gate (advisory) | \`${real_value_status:-NOT_RUN}\` | blockers=\`${real_value_blockers:-UNKNOWN}\` |"
  if [[ "$STRICT_REAL_VALUES" == "true" ]]; then
    echo "| strict real-value requirement | \`$strict_real_value_result\` | real-value gate must be \`PASS\` |"
  else
    echo "| strict real-value requirement | \`ADVISORY_ONLY\` | run with \`--strict-real-values\` to enforce |"
  fi
  echo "| root/pack operator report hash match | \`$status_operator_copy\` | \`$root_operator_hash == $pack_operator_hash\` |"
  echo "| root/pack snapshot report hash match | \`$status_snapshot_copy\` | \`$root_snapshot_hash == $pack_snapshot_hash\` |"
  echo
  echo "## Artifact Paths"
  echo "- Root operator report: \`$ROOT_OPERATOR\`"
  echo "- Root snapshot verify: \`$ROOT_SNAPSHOT\`"
  echo "- Real-value gate report: \`$REAL_VALUE_GATE\`"
  echo "- Pack operator report: \`$PACK_OPERATOR\`"
  echo "- Pack snapshot verify: \`$PACK_SNAPSHOT\`"
  echo "- Handoff pack directory: \`$PACK\`"
  echo "- Handoff pack zip: \`$OUT_ROOT/external_binding_handoff_pack_61day.zip\`"
} > "$REPORT"

echo "Submission release regression suite report:"
echo "  $REPORT"
echo "Overall status: $overall"

if [[ "$overall" == "PASS" ]]; then
  exit 0
fi

exit 1
