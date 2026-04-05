from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ais_risk.dataset_manifest import (
    build_dataset_id,
    build_first_dataset_manifest_markdown,
    parse_first_dataset_manifest,
    save_first_dataset_manifest,
)


class DatasetManifestTest(unittest.TestCase):
    def test_build_dataset_id_and_manifest(self) -> None:
        dataset_id = build_dataset_id(
            source_slug="dma",
            area_slug="corridor_a",
            start_date_text="2023-08-01",
            end_date_text="2023-08-07",
            version="v1",
        )
        self.assertEqual(dataset_id, "dma_corridor_a_2023-08-01_2023-08-07_v1")

        text = build_first_dataset_manifest_markdown(
            dataset_id=dataset_id,
            source_name="DMA historical AIS",
            source_url="https://example.com/source",
            license_url="https://example.com/license",
            area="Corridor A",
            start_date_text="2023-08-01",
            end_date_text="2023-08-07",
            raw_root="data/raw/dma",
        )
        self.assertIn(dataset_id, text)
        self.assertIn("schema probe", text)
        self.assertIn("workflow", text)
        self.assertIn("data/raw/dma", text)

    def test_save_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.md"
            saved = save_first_dataset_manifest(path, "# test\n")
            self.assertEqual(str(path), saved)
            self.assertTrue(path.exists())
            self.assertEqual("# test\n", path.read_text(encoding="utf-8"))

    def test_parse_manifest_extracts_core_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_id = "dma_corridor_a_2023-08-01_2023-08-07_v1"
            path = Path(tmpdir) / f"{dataset_id}.md"
            path.write_text(
                build_first_dataset_manifest_markdown(
                    dataset_id=dataset_id,
                    source_name="DMA historical AIS",
                    source_url="https://example.com/source",
                    license_url="https://example.com/license",
                    area="Corridor A",
                    start_date_text="2023-08-01",
                    end_date_text="2023-08-07",
                    raw_root="data/raw/dma",
                ),
                encoding="utf-8",
            )
            parsed = parse_first_dataset_manifest(path)
            self.assertEqual(dataset_id, parsed["dataset_id"])
            self.assertEqual("Corridor A", parsed["area"])
            self.assertEqual("2023-08-01", parsed["start_date"])
            self.assertEqual("2023-08-07", parsed["end_date"])
            self.assertEqual("dma", parsed["source_slug"])

    def test_parse_manifest_extracts_date_with_status_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.md"
            path.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `dma_case_2023-08-01_2023-08-07_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 해역 | [합리적 가정] Corridor X |",
                        "| 시작 시각 | [합리적 가정] 2023-08-01 |",
                        "| 종료 시각 | [추가 검증 필요] 2023-08-07 |",
                    ]
                ),
                encoding="utf-8",
            )
            parsed = parse_first_dataset_manifest(path)
            self.assertEqual("2023-08-01", parsed["start_date"])
            self.assertEqual("2023-08-07", parsed["end_date"])


if __name__ == "__main__":
    unittest.main()
