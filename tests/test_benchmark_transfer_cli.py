from __future__ import annotations

import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.benchmark_transfer_cli import main


def _base_row(
    timestamp: str,
    own_mmsi: str,
    target_mmsi: str,
    positive: bool,
) -> dict[str, str]:
    return {
        "timestamp": timestamp,
        "own_mmsi": own_mmsi,
        "target_mmsi": target_mmsi,
        "own_segment_id": f"{own_mmsi}-0001",
        "target_segment_id": f"{target_mmsi}-0001",
        "own_vessel_type": "cargo",
        "target_vessel_type": "cargo" if positive else "tanker",
        "own_is_interpolated": "0",
        "target_is_interpolated": "0",
        "local_target_count": "3",
        "distance_nm": "0.250000" if positive else "2.800000",
        "dcpa_nm": "0.150000" if positive else "2.300000",
        "tcpa_min": "4.000000" if positive else "18.000000",
        "relative_speed_knots": "11.000000" if positive else "4.500000",
        "relative_bearing_deg": "15.000000" if positive else "135.000000",
        "bearing_abs_deg": "15.000000" if positive else "135.000000",
        "course_difference_deg": "165.000000" if positive else "25.000000",
        "encounter_type": "head_on" if positive else "diverging",
        "rule_score": "0.900000" if positive else "0.120000",
        "rule_component_distance": "0.200000",
        "rule_component_dcpa": "0.200000",
        "rule_component_tcpa": "0.200000",
        "rule_component_bearing": "0.100000",
        "rule_component_relspeed": "0.070000",
        "rule_component_encounter": "0.100000",
        "rule_component_density": "0.050000",
        "future_min_distance_nm": "0.150000" if positive else "2.200000",
        "future_time_to_min_min": "3.000000" if positive else "9.000000",
        "future_points_used": "4",
        "label_future_conflict": "1" if positive else "0",
    }


class BenchmarkTransferCliTest(unittest.TestCase):
    def test_cli_exports_source_validation_and_target_predictions(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_path = root / "source.csv"
            target_path = root / "target.csv"
            output_prefix = root / "transfer"

            fieldnames = [
                "timestamp",
                "own_mmsi",
                "target_mmsi",
                "own_segment_id",
                "target_segment_id",
                "own_vessel_type",
                "target_vessel_type",
                "own_is_interpolated",
                "target_is_interpolated",
                "local_target_count",
                "distance_nm",
                "dcpa_nm",
                "tcpa_min",
                "relative_speed_knots",
                "relative_bearing_deg",
                "bearing_abs_deg",
                "course_difference_deg",
                "encounter_type",
                "rule_score",
                "rule_component_distance",
                "rule_component_dcpa",
                "rule_component_tcpa",
                "rule_component_bearing",
                "rule_component_relspeed",
                "rule_component_encounter",
                "rule_component_density",
                "future_min_distance_nm",
                "future_time_to_min_min",
                "future_points_used",
                "label_future_conflict",
            ]

            source_rows = []
            own_ships = ["440000001", "440000002", "440000003"]
            for ship_index, own_mmsi in enumerate(own_ships):
                for index in range(6):
                    positive = index % 2 == 0
                    source_rows.append(
                        _base_row(
                            timestamp=f"2026-03-16T0{ship_index}:{index:02d}:00Z",
                            own_mmsi=own_mmsi,
                            target_mmsi=f"55000{ship_index}{index:03d}",
                            positive=positive,
                        )
                    )

            target_rows = []
            target_own_ships = ["540000001", "540000002"]
            for ship_index, own_mmsi in enumerate(target_own_ships):
                for index in range(4):
                    positive = index % 2 == 0
                    target_rows.append(
                        _base_row(
                            timestamp=f"2026-03-17T0{ship_index}:{index:02d}:00Z",
                            own_mmsi=own_mmsi,
                            target_mmsi=f"66000{ship_index}{index:03d}",
                            positive=positive,
                        )
                    )

            with source_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(source_rows)

            with target_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(target_rows)

            stdout = io.StringIO()
            argv = [
                "benchmark_transfer_cli",
                "--train-input",
                str(source_path),
                "--target-input",
                str(target_path),
                "--output-prefix",
                str(output_prefix),
                "--models",
                "rule_score,logreg",
                "--split-strategy",
                "own_ship",
            ]
            with patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            output = stdout.getvalue()
            self.assertIn("source_summary_json=", output)
            self.assertIn("source_val_predictions_csv=", output)
            self.assertIn("target_predictions_csv=", output)
            self.assertTrue((root / "transfer_source_summary.json").exists())
            self.assertTrue((root / "transfer_source_summary.md").exists())
            self.assertTrue((root / "transfer_source_test_predictions.csv").exists())
            self.assertTrue((root / "transfer_source_val_predictions.csv").exists())
            self.assertTrue((root / "transfer_target_predictions.csv").exists())
            self.assertTrue((root / "transfer_transfer_summary.json").exists())
            self.assertTrue((root / "transfer_transfer_summary.md").exists())

            with (root / "transfer_target_predictions.csv").open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
            self.assertEqual(len(target_rows), len(rows))
            self.assertIn("logreg_score", rows[0])
            self.assertIn("logreg_pred", rows[0])


if __name__ == "__main__":
    unittest.main()
