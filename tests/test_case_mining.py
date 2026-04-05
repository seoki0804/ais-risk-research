from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.case_mining import mine_cases_from_curated_csv, save_case_candidates


class CaseMiningTest(unittest.TestCase):
    def test_case_candidates_are_ranked_and_saved(self) -> None:
        root = Path(__file__).resolve().parents[1]
        input_path = root / "examples" / "sample_ais.csv"
        config_path = root / "configs" / "base.toml"

        with tempfile.TemporaryDirectory() as temp_dir:
            curated_path = Path(temp_dir) / "curated.csv"
            output_path = Path(temp_dir) / "cases.csv"
            from ais_risk.csv_tools import preprocess_ais_csv

            preprocess_ais_csv(input_path, curated_path)
            candidates = mine_cases_from_curated_csv(
                input_path=curated_path,
                own_mmsi="440000001",
                config_path=config_path,
                radius_nm=6.0,
                top_n=5,
            )
            self.assertTrue(candidates)
            save_case_candidates(output_path, candidates)

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertTrue(rows)
            self.assertIn("max_risk", rows[0])
            self.assertGreaterEqual(float(rows[0]["max_risk"]), float(rows[-1]["max_risk"]))


if __name__ == "__main__":
    unittest.main()
