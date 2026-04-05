from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.csv_tools import preprocess_ais_csv
from ais_risk.own_ship_candidates import (
    rank_own_ship_candidates_csv,
    recommend_own_ship_candidates_csv,
    save_own_ship_candidates,
)
from ais_risk.trajectory import reconstruct_trajectory_csv


class OwnShipCandidatesTest(unittest.TestCase):
    def test_rank_own_ship_candidates_prefers_interactive_tracks(self) -> None:
        root = Path(__file__).resolve().parents[1]
        input_path = root / "examples" / "sample_ais.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            tracks_path = Path(temp_dir) / "tracks.csv"
            preprocess_ais_csv(input_path, curated_path)
            reconstruct_trajectory_csv(curated_path, tracks_path)

            candidates = rank_own_ship_candidates_csv(tracks_path, radius_nm=6.0, top_n=5)

            self.assertEqual(len(candidates), 5)
            self.assertGreaterEqual(float(candidates[0]["candidate_score"]), float(candidates[-1]["candidate_score"]))
            self.assertEqual(candidates[-1]["mmsi"], "440000104")
            self.assertEqual(int(candidates[-1]["active_window_count"]), 0)
            self.assertGreater(int(candidates[0]["active_window_count"]), 0)

    def test_recommend_own_ship_candidates_attach_timestamp_context(self) -> None:
        root = Path(__file__).resolve().parents[1]
        input_path = root / "examples" / "sample_ais.csv"
        config_path = root / "configs" / "base.toml"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            tracks_path = Path(temp_dir) / "tracks.csv"
            preprocess_ais_csv(input_path, curated_path)
            reconstruct_trajectory_csv(curated_path, tracks_path)

            candidates = recommend_own_ship_candidates_csv(
                input_path=tracks_path,
                config_path=config_path,
                radius_nm=6.0,
                top_n=5,
            )

            self.assertEqual(len(candidates), 5)
            self.assertTrue(candidates[0]["recommended_timestamp"])
            self.assertIn(candidates[0]["recommendation_source"], {"risk_peak", "first_observation_fallback"})
            self.assertEqual(candidates[-1]["mmsi"], "440000104")
            self.assertEqual(candidates[-1]["recommendation_source"], "first_observation_fallback")

    def test_save_own_ship_candidates_outputs_csv(self) -> None:
        root = Path(__file__).resolve().parents[1]
        input_path = root / "examples" / "sample_ais.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            output_path = Path(temp_dir) / "own_ship_candidates.csv"
            preprocess_ais_csv(input_path, curated_path)
            candidates = rank_own_ship_candidates_csv(curated_path, radius_nm=6.0, top_n=3)
            save_own_ship_candidates(output_path, candidates)

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertIn("candidate_score", rows[0])
            self.assertIn("reason_summary", rows[0])


if __name__ == "__main__":
    unittest.main()
