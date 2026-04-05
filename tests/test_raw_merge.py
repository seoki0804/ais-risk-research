from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ais_risk.raw_merge import merge_raw_csv_files


class RawMergeTest(unittest.TestCase):
    def test_merge_raw_csv_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            a = root / "a.csv"
            b = root / "b.csv"
            merged = root / "raw.csv"
            a.write_text("MMSI,BaseDateTime,LAT,LON,SOG,COG\n1,2023-08-01T00:00:00Z,1,2,3,4\n", encoding="utf-8")
            b.write_text("MMSI,BaseDateTime,LAT,LON,SOG,COG\n2,2023-08-01T00:01:00Z,5,6,7,8\n", encoding="utf-8")

            summary = merge_raw_csv_files(str(root / "*.csv"), merged)

            self.assertEqual(2, summary["output_rows"])
            self.assertTrue(merged.exists())
            text = merged.read_text(encoding="utf-8")
            self.assertIn("MMSI,BaseDateTime,LAT,LON,SOG,COG", text)
            self.assertIn("1,2023-08-01T00:00:00Z,1,2,3,4", text)
            self.assertIn("2,2023-08-01T00:01:00Z,5,6,7,8", text)


if __name__ == "__main__":
    unittest.main()
