from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from ais_risk.uncertainty_contour_report import build_uncertainty_contour_report


class UncertaintyContourReportTest(unittest.TestCase):
    def test_build_uncertainty_contour_report_generates_svg(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            projected_cells_path = root / "projected_cells.csv"
            case_summary_path = root / "case_summary.csv"
            config_path = root / "config.toml"
            output_prefix = root / "uncertainty_report"

            config_path.write_text(
                "\n".join(
                    [
                        "[project]",
                        'name = "Report Test"',
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

            with projected_cells_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "case_id",
                        "timestamp",
                        "own_mmsi",
                        "model",
                        "x_m",
                        "y_m",
                        "risk_raw",
                        "risk_lower",
                        "risk_mean",
                        "risk_upper",
                        "label_raw",
                        "label_lower",
                        "label_mean",
                        "label_upper",
                    ],
                )
                writer.writeheader()
                writer.writerows(
                    [
                        {
                            "case_id": "case_a",
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "model": "hgbt",
                            "x_m": "0.00",
                            "y_m": "0.00",
                            "risk_raw": "0.70",
                            "risk_lower": "0.20",
                            "risk_mean": "0.45",
                            "risk_upper": "0.80",
                            "label_raw": "danger",
                            "label_lower": "safe",
                            "label_mean": "caution",
                            "label_upper": "danger",
                        },
                        {
                            "case_id": "case_a",
                            "timestamp": "2026-03-16T09:00:00Z",
                            "own_mmsi": "440000001",
                            "model": "hgbt",
                            "x_m": "100.00",
                            "y_m": "0.00",
                            "risk_raw": "0.30",
                            "risk_lower": "0.10",
                            "risk_mean": "0.25",
                            "risk_upper": "0.50",
                            "label_raw": "safe",
                            "label_lower": "safe",
                            "label_mean": "safe",
                            "label_upper": "caution",
                        },
                    ]
                )

            with case_summary_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "case_id",
                        "timestamp",
                        "own_mmsi",
                        "model",
                        "target_count",
                        "mean_target_band_width",
                        "max_target_band_width",
                        "cell_count",
                        "max_risk_raw",
                        "max_risk_lower",
                        "max_risk_mean",
                        "max_risk_upper",
                        "mean_risk_raw",
                        "mean_risk_lower",
                        "mean_risk_mean",
                        "mean_risk_upper",
                        "max_cell_band_span",
                        "mean_cell_band_span",
                        "warning_area_raw_nm2",
                        "warning_area_lower_nm2",
                        "warning_area_mean_nm2",
                        "warning_area_upper_nm2",
                        "caution_area_raw_nm2",
                        "caution_area_lower_nm2",
                        "caution_area_mean_nm2",
                        "caution_area_upper_nm2",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "case_id": "case_a",
                        "timestamp": "2026-03-16T09:00:00Z",
                        "own_mmsi": "440000001",
                        "model": "hgbt",
                        "target_count": "2",
                        "mean_target_band_width": "0.50",
                        "max_target_band_width": "0.60",
                        "cell_count": "2",
                        "max_risk_raw": "0.70",
                        "max_risk_lower": "0.20",
                        "max_risk_mean": "0.45",
                        "max_risk_upper": "0.80",
                        "mean_risk_raw": "0.50",
                        "mean_risk_lower": "0.15",
                        "mean_risk_mean": "0.35",
                        "mean_risk_upper": "0.65",
                        "max_cell_band_span": "0.60",
                        "mean_cell_band_span": "0.45",
                        "warning_area_raw_nm2": "0.01",
                        "warning_area_lower_nm2": "0.00",
                        "warning_area_mean_nm2": "0.00",
                        "warning_area_upper_nm2": "0.01",
                        "caution_area_raw_nm2": "0.01",
                        "caution_area_lower_nm2": "0.00",
                        "caution_area_mean_nm2": "0.01",
                        "caution_area_upper_nm2": "0.01",
                    }
                )

            summary = build_uncertainty_contour_report(
                projected_cells_csv_path=projected_cells_path,
                case_summary_csv_path=case_summary_path,
                output_prefix=output_prefix,
                config_path=config_path,
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual("case_a", summary["case_id"])
            self.assertTrue(Path(summary["figure_svg_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())

            svg_text = Path(summary["figure_svg_path"]).read_text(encoding="utf-8")
            self.assertIn("Raw Contour", svg_text)
            self.assertIn("Mean Band", svg_text)


if __name__ == "__main__":
    unittest.main()
