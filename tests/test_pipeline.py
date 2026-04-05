from __future__ import annotations

import unittest
from pathlib import Path

from ais_risk.config import load_config
from ais_risk.io import load_snapshot
from ais_risk.pipeline import run_snapshot


class PipelineTest(unittest.TestCase):
    def test_sample_snapshot_runs_end_to_end(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "configs" / "base.toml")
        snapshot = load_snapshot(root / "examples" / "sample_snapshot.json")

        result = run_snapshot(snapshot, config)

        self.assertEqual(len(result.scenarios), 3)
        self.assertTrue(result.scenarios[0].cells)
        self.assertGreaterEqual(result.scenarios[0].summary.max_risk, 0.0)
        self.assertLessEqual(result.scenarios[0].summary.max_risk, 1.0)
        self.assertTrue(result.scenarios[0].top_vessels)


if __name__ == "__main__":
    unittest.main()
