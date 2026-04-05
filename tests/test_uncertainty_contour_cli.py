from __future__ import annotations

import csv
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ais_risk.uncertainty_contour_cli import main


class UncertaintyContourCliTest(unittest.TestCase):
    def test_cli_runs_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            predictions_path = root / "predictions.csv"
            bins_path = root / "calibration_bins.csv"
            pairwise_path = root / "pairwise.csv"
            config_path = root / "config.toml"
            output_prefix = root / "uncertainty_cli"

            config_path.write_text(
                "\n".join(
                    [
                        "[project]",
                        'name = "CLI Test"',
                        "",
                        "[grid]",
                        "radius_nm = 0.20",
                        "cell_size_m = 100.0",
                        "kernel_sigma_m = 100.0",
                        "",
                        "[horizon]",
                        "minutes = 15",
                        "time_step_seconds = 30",
                        "",
                        "[thresholds]",
                        "safe = 0.35",
                        "warning = 0.65",
                        "density_radius_nm = 2.0",
                        "density_reference_count = 6.0",
                        "",
                        "[weights]",
                        "distance = 0.15",
                        "dcpa = 0.20",
                        "tcpa = 0.20",
                        "bearing = 0.10",
                        "relspeed = 0.10",
                        "encounter = 0.15",
                        "density = 0.10",
                        "",
                        "[scenarios]",
                        'order = ["current"]',
                        "",
                        "[scenarios.values]",
                        "current = 1.0",
                    ]
                ),
                encoding="utf-8",
            )

            with predictions_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "timestamp",
                        "own_mmsi",
                        "target_mmsi",
                        "label_future_conflict",
                        "hgbt_score",
                        "hgbt_pred",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000101",
                            "label_future_conflict": "1",
                            "hgbt_score": "0.85",
                            "hgbt_pred": "1",
                        },
                        {
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000102",
                            "label_future_conflict": "0",
                            "hgbt_score": "0.15",
                            "hgbt_pred": "0",
                        },
                    ]
                )

            with bins_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "model",
                        "bin_index",
                        "bin_lower",
                        "bin_upper",
                        "count",
                        "avg_score",
                        "empirical_rate",
                        "gap_abs",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "model": "hgbt",
                            "bin_index": "1",
                            "bin_lower": "0.1",
                            "bin_upper": "0.2",
                            "count": "20",
                            "avg_score": "0.15",
                            "empirical_rate": "0.10",
                            "gap_abs": "0.05",
                        },
                        {
                            "model": "hgbt",
                            "bin_index": "8",
                            "bin_lower": "0.8",
                            "bin_upper": "0.9",
                            "count": "20",
                            "avg_score": "0.85",
                            "empirical_rate": "0.75",
                            "gap_abs": "0.10",
                        },
                    ]
                )

            with pairwise_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "timestamp",
                        "own_mmsi",
                        "target_mmsi",
                        "distance_nm",
                        "relative_bearing_deg",
                        "encounter_type",
                        "target_vessel_type",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000101",
                            "distance_nm": "0.05",
                            "relative_bearing_deg": "90",
                            "encounter_type": "crossing",
                            "target_vessel_type": "cargo",
                        },
                        {
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "target_mmsi": "440000102",
                            "distance_nm": "0.05",
                            "relative_bearing_deg": "0",
                            "encounter_type": "head_on",
                            "target_vessel_type": "tanker",
                        },
                    ]
                )

            stdout = io.StringIO()
            argv = [
                "uncertainty_contour_cli",
                "--predictions",
                str(predictions_path),
                "--pairwise",
                str(pairwise_path),
                "--calibration-bins",
                str(bins_path),
                "--output-prefix",
                str(output_prefix),
                "--config",
                str(config_path),
                "--models",
                "hgbt",
                "--case-limit",
                "1",
            ]
            with patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    main()

            output = stdout.getvalue()
            self.assertIn("status=completed", output)
            self.assertIn("figure_svg=", output)
            self.assertTrue((root / "uncertainty_cli_band_summary.json").exists())
            self.assertTrue((root / "uncertainty_cli_projection_summary.json").exists())
            self.assertTrue((root / "uncertainty_cli_report_figure.svg").exists())


if __name__ == "__main__":
    unittest.main()
