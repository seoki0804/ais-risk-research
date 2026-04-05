from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ais_risk.csv_tools import preprocess_ais_csv
from ais_risk.own_ship_candidates import rank_own_ship_candidates_csv, save_own_ship_candidates
from ais_risk.own_ship_quality_gate import (
    apply_own_ship_quality_gate,
    build_own_ship_quality_gate_summary,
    load_own_ship_candidate_rows,
    save_own_ship_quality_gate_outputs,
)
from ais_risk.trajectory import reconstruct_trajectory_csv


class OwnShipQualityGateTest(unittest.TestCase):
    def test_quality_gate_filters_low_interaction_candidates(self) -> None:
        root = Path(__file__).resolve().parents[1]
        input_path = root / "examples" / "sample_ais.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            tracks_path = Path(temp_dir) / "tracks.csv"
            preprocess_ais_csv(input_path, curated_path)
            reconstruct_trajectory_csv(curated_path, tracks_path)
            candidates = rank_own_ship_candidates_csv(tracks_path, radius_nm=6.0, top_n=5)

            gated = apply_own_ship_quality_gate(
                candidates,
                min_row_count=2,
                min_observed_row_count=2,
                max_interpolation_ratio=0.9,
                min_heading_coverage_ratio=0.5,
                min_movement_ratio=0.1,
                min_active_window_ratio=0.1,
                min_average_nearby_targets=0.1,
                max_segment_break_count=10,
                min_candidate_score=0.0,
                min_recommended_target_count=0,
            )

            self.assertTrue(any(bool(row["gate_passed"]) for row in gated))
            rejected = next(row for row in gated if row["mmsi"] == "440000104")
            self.assertFalse(bool(rejected["gate_passed"]))
            self.assertIn("active_window_ratio<0.10", rejected["fail_reason_text"])

    def test_quality_gate_outputs_are_saved(self) -> None:
        rows = [
            {
                "rank": "1",
                "mmsi": "111",
                "candidate_score": "0.9",
                "row_count": "100",
                "observed_row_count": "80",
                "segment_break_count": "2",
                "heading_coverage_ratio": "0.9",
                "movement_ratio": "0.8",
                "active_window_ratio": "0.7",
                "average_nearby_targets": "1.5",
                "recommended_target_count": "3",
            }
        ]
        gated = apply_own_ship_quality_gate(rows)
        summary = build_own_ship_quality_gate_summary(
            gated,
            input_path="dummy.csv",
            min_row_count=80,
            min_observed_row_count=40,
            max_interpolation_ratio=0.70,
            min_heading_coverage_ratio=0.50,
            min_movement_ratio=0.30,
            min_active_window_ratio=0.10,
            min_average_nearby_targets=0.50,
            max_segment_break_count=50,
            min_candidate_score=0.20,
            min_recommended_target_count=1,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            prefix = Path(temp_dir) / "gate"
            summary_json_path, summary_md_path, rows_csv_path = save_own_ship_quality_gate_outputs(prefix, summary, gated)
            loaded_rows = load_own_ship_candidate_rows(rows_csv_path)

            self.assertTrue(summary_json_path.exists())
            self.assertTrue(summary_md_path.exists())
            self.assertTrue(rows_csv_path.exists())
            self.assertEqual(summary["passed_count"], 1)
            self.assertEqual(len(loaded_rows), 1)


if __name__ == "__main__":
    unittest.main()
