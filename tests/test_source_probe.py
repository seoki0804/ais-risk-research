from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from urllib import error

from ais_risk.source_probe import list_public_source_ids, resolve_public_source_ids, run_public_source_probe


class _FakeResponse:
    def __init__(self, status: int, url: str) -> None:
        self.status = int(status)
        self._url = url

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def getcode(self) -> int:
        return self.status

    def geturl(self) -> str:
        return self._url


class SourceProbeTest(unittest.TestCase):
    def test_list_and_resolve_source_ids(self) -> None:
        source_ids = list_public_source_ids()
        self.assertIn("dma_ais", source_ids)
        self.assertIn("noaa_accessais", source_ids)
        self.assertEqual(source_ids, resolve_public_source_ids(None))
        self.assertEqual(["dma_ais"], resolve_public_source_ids(["dma_ais"]))
        with self.assertRaises(ValueError):
            resolve_public_source_ids(["unknown_source"])

    def test_run_public_source_probe_handles_head_405_fallback_and_restricted(self) -> None:
        def opener(req, timeout=0):
            if "dma.dk" in req.full_url:
                if req.method == "HEAD":
                    raise error.HTTPError(req.full_url, 405, "Method Not Allowed", hdrs=None, fp=None)
                return _FakeResponse(200, req.full_url)
            if "aishub.net" in req.full_url:
                raise error.HTTPError(req.full_url, 403, "Forbidden", hdrs=None, fp=None)
            return _FakeResponse(200, req.full_url)

        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_public_source_probe(
                output_prefix=Path(tmpdir) / "source_probe",
                source_ids=["dma_ais", "aishub_api"],
                timeout_seconds=1.0,
                retries=0,
                opener=opener,
            )
            self.assertEqual("completed", summary["status"])
            self.assertEqual(2, summary["row_count"])
            self.assertEqual(1, summary["ok_count"])
            self.assertEqual(1, summary["restricted_count"])
            self.assertEqual(0, summary["failed_count"])
            self.assertTrue(Path(summary["summary_json_path"]).exists())
            self.assertTrue(Path(summary["summary_md_path"]).exists())

            rows = {row["source_id"]: row for row in summary["rows"]}
            self.assertEqual("GET", rows["dma_ais"]["method"])
            self.assertEqual("ok", rows["dma_ais"]["availability"])
            self.assertEqual("restricted", rows["aishub_api"]["availability"])

    def test_run_public_source_probe_marks_network_failure(self) -> None:
        def opener(req, timeout=0):
            raise error.URLError("network down")

        with tempfile.TemporaryDirectory() as tmpdir:
            summary = run_public_source_probe(
                output_prefix=Path(tmpdir) / "source_probe",
                source_ids=["dma_ais"],
                timeout_seconds=1.0,
                retries=0,
                opener=opener,
            )
            self.assertEqual(1, summary["failed_count"])
            self.assertEqual("network_error", summary["rows"][0]["availability"])


if __name__ == "__main__":
    unittest.main()
