#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"

echo "Submission quickstart launcher"
echo
echo "One-command final lock path:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_release_operator_61day.sh"
echo "  (optional strict source drift gate: --strict-source-match)"
echo "  (optional strict venue-value gate: --require-real-values)"
echo "No-compromise regression suite:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_release_regression_suite_61day.sh"
echo "  (strict venue-value enforcement: --strict-real-values)"
echo "Control tower (single-page status board):"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_release_control_tower_61day.sh"
echo "  (strict venue-value enforcement: --require-real-values)"
echo
echo "Start here:"
echo "  1. $ROOT/submission_run_me_first_61day.md"
echo "  2. bash /Users/seoki/Desktop/research/examples/run_submission_intake_interactive_61day.sh"
echo "  3. (optional) bash /Users/seoki/Desktop/research/examples/run_submission_default_prefill_61day.sh"
echo
echo "After running the interactive intake, check these files:"
echo "  - $ROOT/submission_intake_validation_61day.md"
echo "  - $ROOT/submission_portal_copy_paste_filled_61day.md"
echo "  - $ROOT/submission_intake_handoff_61day.md"
echo "  - $ROOT/submission_portal_metadata_filled_61day.json"
echo "  - $ROOT/submission_completion_scorecard_61day.md"
echo "  - $ROOT/claim_consistency_audit_61day.md"
echo "  - $ROOT/submission_hard_gate_61day.md"
echo "  - $ROOT/submission_metadata_strict_audit_61day.md"
echo "  - $ROOT/submission_metadata_real_value_gate_61day.md"
echo "  - $ROOT/submission_release_snapshot_verify_latest_61day.md"
echo "  - $ROOT/submission_release_operator_latest_61day.md"
echo "  - $ROOT/submission_release_regression_suite_61day.md"
echo "  - $ROOT/submission_release_control_tower_61day.md"
echo
echo "If status stays BLOCKED, fill the remaining items listed in:"
echo "  - $ROOT/submission_intake_fill_queue_61day.md"
echo
echo "Refresh objective completion scores:"
echo "  bash /Users/seoki/Desktop/research/examples/run_completion_scorecard_61day.sh"
echo
echo "Run hard gate decision:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_hard_gate_61day.sh"
echo
echo "Generate final readiness certificate:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_readiness_certificate_61day.sh"
echo
echo "Run strict metadata advisory audit:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_metadata_strict_audit_61day.sh"
echo
echo "Run real-value metadata gate (final venue binding check):"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_metadata_real_value_gate_61day.sh"
echo "If blockers remain, apply venue-value binding helper:"
echo "  bash /Users/seoki/Desktop/research/examples/run_apply_submission_real_value_binding_61day.sh \"<venue_name>\" \"<venue_round_or_deadline>\""
echo "One-command strict closure after setting real venue values:"
echo "  bash /Users/seoki/Desktop/research/examples/run_strict_real_value_closure_61day.sh \"<venue_name>\" \"<venue_round_or_deadline>\""
echo
echo "Run final preflight gate (certificate + strict audit):"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_final_preflight_61day.sh"
echo "  (strict venue-value enforcement: --require-real-values)"
echo
echo "Freeze a release snapshot (copies + hashes + zip):"
echo "  bash /Users/seoki/Desktop/research/examples/create_submission_release_snapshot_61day.sh"
echo
echo "Verify latest release snapshot integrity/drift:"
echo "  bash /Users/seoki/Desktop/research/examples/run_verify_submission_release_snapshot_61day.sh"
echo
echo "Auto-fill safe venue defaults first (leaves author fields for manual input):"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_default_prefill_61day.sh"
