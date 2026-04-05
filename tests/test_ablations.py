from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.config import load_config
from ais_risk.csv_tools import load_curated_csv_rows, preprocess_ais_csv
from ais_risk.experiments import run_ablation_experiment, save_ablation_outputs


class AblationTest(unittest.TestCase):
    def test_ablation_outputs_include_baseline_and_requested_variants(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "configs" / "base.toml")
        sample_input = root / "examples" / "sample_ais.csv"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            preprocess_ais_csv(sample_input, curated_path)
            rows = load_curated_csv_rows(curated_path)
            case_rows, aggregate = run_ablation_experiment(
                rows=rows,
                own_mmsi="440000001",
                config=config,
                radius_nm=6.0,
                ablation_names=["bearing", "density", "time_decay"],
                top_n=2,
            )
            prefix = Path(temp_dir) / "ablation"
            csv_path, json_path = save_ablation_outputs(prefix, case_rows, aggregate)

            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                written_rows = list(csv.DictReader(handle))
            payload = json.loads(json_path.read_text(encoding="utf-8"))

            labels = {row["ablation_label"] for row in written_rows}
            self.assertEqual(labels, {"baseline", "drop_bearing", "drop_density", "drop_time_decay"})
            self.assertEqual(payload["case_count"], 2)
            self.assertIn("baseline", payload["ablations"])
            self.assertIn("drop_bearing", payload["ablations"])
            self.assertEqual(len(written_rows), 2 * 4 * 3)


if __name__ == "__main__":
    unittest.main()
