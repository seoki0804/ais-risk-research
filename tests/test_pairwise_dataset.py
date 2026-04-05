from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ais_risk.config import load_config
from ais_risk.csv_tools import preprocess_ais_csv
from ais_risk.pairwise_dataset import build_pairwise_learning_dataset_from_csv
from ais_risk.trajectory import reconstruct_trajectory_csv


class PairwiseDatasetTest(unittest.TestCase):
    def test_pairwise_learning_dataset_builds_from_tracks(self) -> None:
        config = load_config("configs/base.toml")
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            curated_path = tmp_path / "curated.csv"
            tracks_path = tmp_path / "tracks.csv"
            dataset_path = tmp_path / "pairwise.csv"
            stats_path = tmp_path / "pairwise_stats.json"

            preprocess_ais_csv("examples/sample_ais.csv", curated_path)
            reconstruct_trajectory_csv(curated_path, tracks_path, step_seconds=60)

            payload = build_pairwise_learning_dataset_from_csv(
                input_path=tracks_path,
                output_path=dataset_path,
                config=config,
                own_mmsis={"440000001"},
                radius_nm=6.0,
                label_distance_nm=5.0,
                sample_every_nth_timestamp=1,
                min_future_points=1,
                stats_output_path=stats_path,
            )

            self.assertGreater(payload["row_count"], 0)
            self.assertTrue(dataset_path.exists())
            self.assertTrue(stats_path.exists())
            text = dataset_path.read_text(encoding="utf-8")
            self.assertIn("label_future_conflict", text)
            self.assertIn("rule_score", text)


if __name__ == "__main__":
    unittest.main()
