from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ais_risk.noaa_fetch import build_noaa_zip_url, fetch_noaa_archives, iter_date_range
from ais_risk.noaa_fetch_cli import resolve_noaa_fetch_plan


class NoaaFetchTest(unittest.TestCase):
    def test_iter_date_range(self) -> None:
        days = iter_date_range("2023-08-01", "2023-08-03")
        self.assertEqual(["2023-08-01", "2023-08-02", "2023-08-03"], days)

    def test_build_noaa_zip_url(self) -> None:
        url = build_noaa_zip_url("2023-08-01")
        self.assertEqual(
            "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2023/AIS_2023_08_01.zip",
            url,
        )

    def test_fetch_noaa_archives_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = fetch_noaa_archives(
                start_date="2023-08-01",
                end_date="2023-08-02",
                output_dir=Path(tmpdir),
                dry_run=True,
            )
            self.assertEqual("dry_run", summary["status"])
            self.assertEqual(2, summary["planned_count"])
            self.assertEqual(0, summary["downloaded_count"])
            self.assertEqual(2, len(summary["planned_urls"]))
            self.assertEqual(2, len(summary["attempted_urls"]))

    def test_fetch_noaa_archives_uses_fallback_url_when_primary_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            def fake_download(
                url: str,
                destination: Path,
                timeout_sec: int = 90,
                max_attempts: int = 3,
            ) -> int:
                del timeout_sec
                del max_attempts
                if "primary.example" in url:
                    raise OSError("primary failed")
                destination.write_bytes(b"ok")
                return 2

            with patch("ais_risk.noaa_fetch._download_url_to_file", side_effect=fake_download):
                summary = fetch_noaa_archives(
                    start_date="2023-08-01",
                    end_date="2023-08-01",
                    output_dir=output_dir,
                    base_url="https://primary.example/ais",
                    fallback_base_urls=["https://backup.example/ais"],
                    dry_run=False,
                    extract=False,
                    skip_existing=False,
                )

            self.assertEqual(1, summary["downloaded_count"])
            self.assertEqual(0, summary["failed_count"])
            self.assertEqual(["https://backup.example/ais"], summary["fallback_base_urls"])

    def test_resolve_noaa_fetch_plan_from_manifest_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manifest = root / "manifest.md"
            manifest.write_text(
                "\n".join(
                    [
                        "# manifest",
                        "- dataset_id: `noaa_harbor_a_2023-08-01_2023-08-07_v1`",
                        "| 항목 | 값 |",
                        "|---|---|",
                        "| 시작 시각 | 2023-08-01 |",
                        "| 종료 시각 | 2023-08-07 |",
                    ]
                ),
                encoding="utf-8",
            )
            plan = resolve_noaa_fetch_plan(
                start_date=None,
                end_date=None,
                output_dir=None,
                manifest_path=str(manifest),
                dataset_id=None,
            )
            self.assertEqual("2023-08-01", plan["start_date"])
            self.assertEqual("2023-08-07", plan["end_date"])
            self.assertEqual("noaa_harbor_a_2023-08-01_2023-08-07_v1", plan["dataset_id"])
            self.assertTrue(
                plan["output_dir"].endswith(
                    "data/raw/noaa/noaa_harbor_a_2023-08-01_2023-08-07_v1/downloads"
                )
            )


if __name__ == "__main__":
    unittest.main()
