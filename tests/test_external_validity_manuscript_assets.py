from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ais_risk.external_validity_manuscript_assets import (
    _parse_region_json_map,
    run_external_validity_manuscript_assets,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class ExternalValidityManuscriptAssetsTest(unittest.TestCase):
    def test_parse_region_json_map(self) -> None:
        mapping = _parse_region_json_map("houston:/tmp/a.json,nola:/tmp/b.json")
        self.assertEqual({"houston", "nola"}, set(mapping.keys()))
        self.assertTrue(str(mapping["houston"]).endswith("/tmp/a.json"))

    def test_builds_transfer_table_and_scenario_panels(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            transfer_detail_csv = root / "transfer_detail.csv"
            recommendation_csv = root / "recommendation.csv"
            reliability_csv = root / "reliability.csv"
            taxonomy_csv = root / "taxonomy.csv"
            contour_houston_json = root / "houston_report.json"
            contour_nola_json = root / "nola_report.json"
            contour_seattle_json = root / "seattle_report.json"

            _write_csv(
                transfer_detail_csv,
                [
                    {
                        "source_region": "houston",
                        "target_region": "nola",
                        "model_name": "hgbt",
                        "status": "completed",
                        "transfer_threshold": 0.38,
                        "delta_f1_fixed_threshold": -0.13,
                        "delta_f1_bootstrap_ci_low": -0.16,
                        "delta_f1_bootstrap_ci_high": 0.88,
                        "target_retune_gain_f1": 0.01,
                        "target_best_threshold": 0.45,
                        "delta_f1_if_target_retuned": -0.12,
                        "delta_f1_ci_excludes_zero_negative": False,
                    },
                    {
                        "source_region": "nola",
                        "target_region": "seattle",
                        "model_name": "hgbt",
                        "status": "completed",
                        "transfer_threshold": 0.16,
                        "delta_f1_fixed_threshold": 0.44,
                        "delta_f1_bootstrap_ci_low": 0.30,
                        "delta_f1_bootstrap_ci_high": 0.59,
                        "target_retune_gain_f1": 0.02,
                        "target_best_threshold": 0.42,
                        "delta_f1_if_target_retuned": 0.46,
                        "delta_f1_ci_excludes_zero_negative": False,
                    },
                ],
            )
            _write_csv(
                recommendation_csv,
                [
                    {"dataset": "houston_pooled_pairwise", "model_name": "hgbt", "f1_mean": 0.82, "ece_mean": 0.02},
                    {"dataset": "nola_pooled_pairwise", "model_name": "hgbt", "f1_mean": 0.60, "ece_mean": 0.02},
                    {"dataset": "seattle_pooled_pairwise", "model_name": "extra_trees", "f1_mean": 0.81, "ece_mean": 0.03},
                ],
            )
            _write_csv(
                reliability_csv,
                [
                    {"region": "houston", "ece": 0.023, "figure_path": "/tmp/h_reliability.png"},
                    {"region": "nola", "ece": 0.024, "figure_path": "/tmp/n_reliability.png"},
                    {"region": "seattle", "ece": 0.029, "figure_path": "/tmp/s_reliability.png"},
                ],
            )
            _write_csv(
                taxonomy_csv,
                [
                    {"region": "houston", "fp": 1, "fn": 11, "fp_rate": 0.003, "fn_rate": 0.27},
                    {"region": "nola", "fp": 43, "fn": 10, "fp_rate": 0.03, "fn_rate": 0.20},
                    {"region": "seattle", "fp": 5, "fn": 15, "fp_rate": 0.014, "fn_rate": 0.25},
                ],
            )

            for path, region, model in [
                (contour_houston_json, "houston", "hgbt"),
                (contour_nola_json, "nola", "hgbt"),
                (contour_seattle_json, "seattle", "extra_trees"),
            ]:
                path.write_text(
                    json.dumps(
                        {
                            "region": region,
                            "model": model,
                            "figure_svg_path": f"/tmp/{region}_figure.svg",
                            "case_id": f"{region}_case",
                            "timestamp": "2023-08-08T00:00:00Z",
                            "own_mmsi": "123456789",
                            "target_count": 2,
                            "max_risk_mean": 0.9,
                        }
                    ),
                    encoding="utf-8",
                )

            summary = run_external_validity_manuscript_assets(
                transfer_gap_detail_csv_path=transfer_detail_csv,
                recommendation_csv_path=recommendation_csv,
                reliability_region_summary_csv_path=reliability_csv,
                taxonomy_region_summary_csv_path=taxonomy_csv,
                contour_report_summary_json_by_region={
                    "houston": contour_houston_json,
                    "nola": contour_nola_json,
                    "seattle": contour_seattle_json,
                },
                output_prefix=root / "manuscript_assets",
            )

            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, int(summary["transfer_direction_count"]))
            self.assertEqual(3, int(summary["scenario_panel_count"]))
            self.assertTrue(Path(summary["transfer_uncertainty_table_md_path"]).exists())
            self.assertTrue(Path(summary["scenario_panels_md_path"]).exists())

            transfer_md = Path(summary["transfer_uncertainty_table_md_path"]).read_text(encoding="utf-8")
            self.assertIn("Supplementary Table S-Transfer-1", transfer_md)
            panel_md = Path(summary["scenario_panels_md_path"]).read_text(encoding="utf-8")
            self.assertIn("Panel: houston", panel_md)
            self.assertIn("Panel: nola", panel_md)
            self.assertIn("Panel: seattle", panel_md)


if __name__ == "__main__":
    unittest.main()
