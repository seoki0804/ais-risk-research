from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ais_risk.focus_seed_compare import run_focus_seed_compare_bundle


class FocusSeedCompareTest(unittest.TestCase):
    def test_run_focus_seed_compare_bundle_generates_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_seed_compare_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Seed Compare Area |",
                    ]
                ),
                encoding="utf-8",
            )

            summary = run_focus_seed_compare_bundle(
                manifest_path=manifest,
                raw_input_path="examples/sample_ais.csv",
                output_prefix=root / "focus_seed_compare",
                focus_own_ship_mmsis=["440000102", "440000103"],
                seed_values=[42, 43],
                benchmark_modelsets=[["rule_score", "logreg"]],
                output_root=root / "outputs",
                run_calibration_eval=False,
                run_own_ship_loo=False,
                run_own_ship_case_eval=True,
                own_ship_case_eval_min_rows=5,
                own_ship_case_eval_repeat_count=2,
                torch_device="cpu",
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, int(summary["run_count"]))
            self.assertEqual([42, 43], summary.get("seed_values"))
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertTrue(Path(summary["seed_rows_csv_path"]).exists())
            self.assertTrue(Path(summary["modelset_seed_rows_csv_path"]).exists())
            self.assertTrue(Path(summary["aggregate_csv_path"]).exists())
            self.assertEqual(1, len(summary.get("aggregate_by_modelset", [])))

    def test_focus_seed_compare_cli_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `sample_focus_seed_compare_cli_case_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | Sample Focus Seed Compare CLI Area |",
                    ]
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "ais_risk.focus_seed_compare_cli",
                    "--manifest",
                    str(manifest),
                    "--raw-input",
                    "examples/sample_ais.csv",
                    "--output-prefix",
                    str(root / "focus_seed_compare_cli"),
                    "--output-root",
                    str(root / "outputs"),
                    "--focus-own-ship-mmsis",
                    "440000102,440000103",
                    "--seed-values",
                    "42,43",
                    "--benchmark-modelsets",
                    "rule_score,logreg",
                    "--no-run-calibration-eval",
                    "--no-run-own-ship-loo",
                    "--run-own-ship-case-eval",
                    "--own-ship-case-eval-min-rows",
                    "5",
                    "--own-ship-case-eval-repeat-count",
                    "2",
                    "--torch-device",
                    "cpu",
                ],
                env={**os.environ, "PYTHONPATH": "src"},
                cwd="/Users/seoki/Desktop/research",
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("summary_json=", result.stdout)
            summary_json = root / "focus_seed_compare_cli_summary.json"
            self.assertTrue(summary_json.exists())
            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual([42, 43], payload["seed_values"])
            self.assertEqual(2, payload["run_count"])


if __name__ == "__main__":
    unittest.main()
