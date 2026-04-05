from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.config import load_config
from ais_risk.csv_tools import load_curated_csv_rows, preprocess_ais_csv
from ais_risk.experiments import run_baseline_experiment, save_experiment_outputs


class ExperimentTest(unittest.TestCase):
    def test_batch_experiment_outputs_case_and_aggregate_files(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "configs" / "base.toml")
        sample_input = root / "examples" / "sample_ais.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            preprocess_ais_csv(sample_input, curated_path)
            rows = load_curated_csv_rows(curated_path)
            case_rows, aggregate = run_baseline_experiment(
                rows=rows,
                own_mmsi="440000001",
                config=config,
                radius_nm=6.0,
                top_n=3,
            )
            prefix = Path(temp_dir) / "experiment"
            csv_path, json_path = save_experiment_outputs(prefix, case_rows, aggregate)

            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                written_rows = list(csv.DictReader(handle))
            written_aggregate = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertTrue(written_rows)
            self.assertEqual(written_aggregate["case_count"], 3)
            self.assertIn("current", written_aggregate["scenario_averages"])
            self.assertEqual(len(written_rows), 9)


if __name__ == "__main__":
    unittest.main()
