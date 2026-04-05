#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
OUT_BASE="$ROOT/outputs/presentation_deck_outline_61day_2026-03-13"

RECOMMENDED_DOC="$OUT_BASE/recommended_submission_lane_61day.md"
RESET_DOC="$OUT_BASE/hard_reset_reassessment_61day.md"
REDUCTION_DOC="$OUT_BASE/paper_main_story_reduction_map_61day.md"
PROFILE_DOC="$OUT_BASE/target_venue_default_applied_conference_profile_61day.md"
INTAKE_DOC="$OUT_BASE/target_venue_intake_applied_conference_default_61day.md"
PACKET_NOTE="$OUT_BASE/applied_conference_default_packet_note_61day.md"
QUICKSTART_DOC="$OUT_BASE/submission_run_me_first_61day.md"
PACKET_DIR="$OUT_BASE/venue_packets/applied_conf_default_blind_61day"
VALIDATION_DOC="$PACKET_DIR/VENUE_PACKET_VALIDATION.md"
READINESS_DOC="$PACKET_DIR/VENUE_PACKET_READINESS.md"

echo "Recommended submission lane launcher"
echo "  lane: applied conference blind"
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
echo "Open in this order:"
echo "  1. $QUICKSTART_DOC"
echo "  2. $RECOMMENDED_DOC"
echo "  3. $RESET_DOC"
echo "  4. $REDUCTION_DOC"
echo "  5. $PROFILE_DOC"
echo "  6. $INTAKE_DOC"
echo "  7. $PACKET_NOTE"
echo "  8. $VALIDATION_DOC"
echo "  9. $READINESS_DOC"
echo " 10. $PACKET_DIR"
echo
echo "Fastest command:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_intake_interactive_61day.sh"
echo
echo "Objective score refresh:"
echo "  bash /Users/seoki/Desktop/research/examples/run_completion_scorecard_61day.sh"
echo "  (includes claim consistency audit)"
echo
echo "Hard gate refresh:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_hard_gate_61day.sh"
echo
echo "Default prefill + hard gate:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_default_prefill_61day.sh"
echo
echo "Readiness certificate:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_readiness_certificate_61day.sh"
echo
echo "Strict metadata advisory audit:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_metadata_strict_audit_61day.sh"
echo
echo "Real-value metadata gate (final venue-binding check):"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_metadata_real_value_gate_61day.sh"
echo "If blockers remain, apply venue-value binding helper:"
echo "  bash /Users/seoki/Desktop/research/examples/run_apply_submission_real_value_binding_61day.sh \"<venue_name>\" \"<venue_round_or_deadline>\""
echo "One-command strict closure after setting real venue values:"
echo "  bash /Users/seoki/Desktop/research/examples/run_strict_real_value_closure_61day.sh \"<venue_name>\" \"<venue_round_or_deadline>\""
echo
echo "Final preflight gate:"
echo "  bash /Users/seoki/Desktop/research/examples/run_submission_final_preflight_61day.sh"
echo "  (strict venue-value enforcement: --require-real-values)"
echo
echo "Release snapshot freeze:"
echo "  bash /Users/seoki/Desktop/research/examples/create_submission_release_snapshot_61day.sh"
echo
echo "Release snapshot verification:"
echo "  bash /Users/seoki/Desktop/research/examples/run_verify_submission_release_snapshot_61day.sh"
