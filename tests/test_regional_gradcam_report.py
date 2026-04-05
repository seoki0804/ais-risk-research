from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from ais_risk.regional_gradcam_report import run_regional_gradcam_report
from ais_risk.regional_raster_cnn import RegionalRiskCNN


class RegionalGradcamReportTest(unittest.TestCase):
    def test_report_builds_from_saved_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            model = RegionalRiskCNN(in_channels=5, scalar_dim=5)
            checkpoint_path = root / "regional_checkpoint.pt"
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "in_channels": 5,
                    "scalar_dim": 5,
                },
                checkpoint_path,
            )

            candidate_npz_path = root / "regional_candidates.npz"
            images = np.random.default_rng(42).random((3, 5, 16, 16), dtype=np.float32)
            scalars = np.random.default_rng(7).random((3, 5), dtype=np.float32)
            labels = np.array([1, 0, 1], dtype=np.int64)
            scores = np.array([0.91, 0.88, 0.12], dtype=np.float32)
            preds = np.array([1, 1, 0], dtype=np.int64)
            np.savez_compressed(
                candidate_npz_path,
                images=images,
                scalar_features=scalars,
                labels=labels,
                scores=scores,
                preds=preds,
                threshold=np.array([0.5], dtype=np.float32),
            )

            metadata_jsonl_path = root / "regional_candidates.jsonl"
            metadata_rows = [
                {
                    "bucket": "tp",
                    "timestamp": "2026-03-16T09:00:00Z",
                    "own_mmsi": "440000001",
                    "target_mmsi": "440000101",
                },
                {
                    "bucket": "fp",
                    "timestamp": "2026-03-16T09:05:00Z",
                    "own_mmsi": "440000001",
                    "target_mmsi": "440000102",
                },
                {
                    "bucket": "fn",
                    "timestamp": "2026-03-16T09:10:00Z",
                    "own_mmsi": "440000001",
                    "target_mmsi": "440000103",
                },
            ]
            metadata_jsonl_path.write_text(
                "".join(json.dumps(row) + "\n" for row in metadata_rows),
                encoding="utf-8",
            )

            benchmark_summary_json = root / "regional_summary.json"
            benchmark_summary_json.write_text(
                json.dumps(
                    {
                        "checkpoint_path": str(checkpoint_path),
                        "gradcam_candidates_npz_path": str(candidate_npz_path),
                        "gradcam_candidates_jsonl_path": str(metadata_jsonl_path),
                        "metrics": {"threshold": 0.5},
                    }
                ),
                encoding="utf-8",
            )

            output_prefix = root / "regional_gradcam"
            summary = run_regional_gradcam_report(
                benchmark_summary_json_path=benchmark_summary_json,
                output_prefix=output_prefix,
                torch_device="cpu",
            )

            self.assertEqual(summary["status"], "completed")
            self.assertTrue(Path(summary["figure_png_path"]).exists())
            self.assertTrue(Path(summary["figure_svg_path"]).exists())
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())
            self.assertGreaterEqual(len(summary["selected_cases"]), 1)


if __name__ == "__main__":
    unittest.main()
