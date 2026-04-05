from __future__ import annotations

import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from ais_risk.config import load_config
from ais_risk.io import load_snapshot
from ais_risk.pipeline import run_snapshot
from ais_risk.report import (
    build_all_scenario_svg_texts,
    build_html_report,
    build_html_report_text,
    build_scenario_svg_text,
    save_all_scenario_svgs,
    save_scenario_svg,
)


class ReportTest(unittest.TestCase):
    def test_html_report_is_generated(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "configs" / "base.toml")
        snapshot = load_snapshot(root / "examples" / "sample_snapshot.json")
        result = run_snapshot(snapshot, config)

        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = Path(temp_dir) / "result.json"
            html_path = Path(temp_dir) / "report.html"
            from ais_risk.io import save_result

            save_result(result_path, result)
            build_html_report(
                snapshot=snapshot,
                result_path=result_path,
                output_path=html_path,
                radius_nm=config.grid.radius_nm,
                cell_size_m=config.grid.cell_size_m,
                safe_threshold=config.thresholds.safe,
                warning_threshold=config.thresholds.warning,
            )

            html_text = html_path.read_text(encoding="utf-8")
            self.assertIn("Own-ship-centric spatial risk report", html_text)
            self.assertIn("current", html_text)
            self.assertIn("slowdown", html_text)
            self.assertIn("speedup", html_text)

    def test_html_report_text_can_be_built_from_result_dict(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "configs" / "base.toml")
        snapshot = load_snapshot(root / "examples" / "sample_snapshot.json")
        result = run_snapshot(snapshot, config)

        html_text = build_html_report_text(
            snapshot=snapshot,
            result=asdict(result),
            radius_nm=config.grid.radius_nm,
            cell_size_m=config.grid.cell_size_m,
            safe_threshold=config.thresholds.safe,
            warning_threshold=config.thresholds.warning,
        )

        self.assertIn("AIS Risk Mapping Starter", html_text)
        self.assertIn("Warning Area", html_text)
        self.assertIn("Own-ship-centric spatial risk report", html_text)

    def test_scenario_svg_can_be_built_and_saved(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "configs" / "base.toml")
        snapshot = load_snapshot(root / "examples" / "sample_snapshot.json")
        result = run_snapshot(snapshot, config)
        current = next((scenario for scenario in result.scenarios if scenario.summary.scenario_name == "current"), result.scenarios[0])

        svg_text = build_scenario_svg_text(
            snapshot=snapshot,
            scenario=asdict(current),
            radius_nm=config.grid.radius_nm,
            cell_size_m=config.grid.cell_size_m,
            safe_threshold=config.thresholds.safe,
            warning_threshold=config.thresholds.warning,
        )
        self.assertIn("<svg", svg_text)
        self.assertIn("scenario-svg", svg_text)
        self.assertIn("caption-title", svg_text)
        self.assertIn("top vessel", svg_text)

        with tempfile.TemporaryDirectory() as temp_dir:
            svg_path = Path(temp_dir) / "current.svg"
            save_scenario_svg(
                output_path=svg_path,
                snapshot=snapshot,
                scenario=asdict(current),
                radius_nm=config.grid.radius_nm,
                cell_size_m=config.grid.cell_size_m,
                safe_threshold=config.thresholds.safe,
                warning_threshold=config.thresholds.warning,
            )
            self.assertTrue(svg_path.exists())

    def test_all_scenario_svgs_can_be_built_and_saved(self) -> None:
        root = Path(__file__).resolve().parents[1]
        config = load_config(root / "configs" / "base.toml")
        snapshot = load_snapshot(root / "examples" / "sample_snapshot.json")
        result = run_snapshot(snapshot, config)

        svg_map = build_all_scenario_svg_texts(
            snapshot=snapshot,
            result=asdict(result),
            radius_nm=config.grid.radius_nm,
            cell_size_m=config.grid.cell_size_m,
            safe_threshold=config.thresholds.safe,
            warning_threshold=config.thresholds.warning,
        )
        self.assertEqual(set(svg_map.keys()), {"slowdown", "current", "speedup"})

        with tempfile.TemporaryDirectory() as temp_dir:
            saved_paths = save_all_scenario_svgs(
                output_dir=temp_dir,
                snapshot=snapshot,
                result=asdict(result),
                radius_nm=config.grid.radius_nm,
                cell_size_m=config.grid.cell_size_m,
                safe_threshold=config.thresholds.safe,
                warning_threshold=config.thresholds.warning,
            )
            self.assertEqual(set(saved_paths.keys()), {"slowdown", "current", "speedup"})
            self.assertTrue((Path(temp_dir) / "slowdown_scenario.svg").exists())
            self.assertTrue((Path(temp_dir) / "current_scenario.svg").exists())
            self.assertTrue((Path(temp_dir) / "speedup_scenario.svg").exists())


if __name__ == "__main__":
    unittest.main()
