from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SubmissionPreflightReportScriptTest(unittest.TestCase):
    def test_preflight_report_script_generates_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manuscript_dir = root / "manuscript"
            manuscript_dir.mkdir(parents=True, exist_ok=True)

            file_a = manuscript_dir / "a.txt"
            file_b = manuscript_dir / "b.txt"
            file_a.write_text("alpha\n", encoding="utf-8")
            file_b.write_text("beta\n", encoding="utf-8")

            manifest = manuscript_dir / "manifest.txt"
            manifest.write_text(
                "\n".join(
                    [
                        "bundle_name=bundle.zip",
                        "generated_at_utc=2026-04-09T00:00:00Z",
                        "file_count=2",
                        "---",
                        f"{_sha256(file_a)}  a.txt",
                        f"{_sha256(file_b)}  b.txt",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            bundle = manuscript_dir / "bundle.zip"
            with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(file_a, arcname="a.txt")
                archive.write(file_b, arcname="b.txt")
                archive.write(manifest, arcname="manifest.txt")

            scorecard = manuscript_dir / "manuscript_completion_scorecard_v0.2_2026-04-09.md"
            scorecard.write_text(
                "\n".join(
                    [
                        "# Manuscript Completion Scorecard v0.2 (2026-04-09)",
                        "",
                        "- Completion score: **100%** (9/9)",
                        "- Status: **READY_FOR_SUBMISSION**",
                        "- Consistency: `PASS`",
                        "- Bilingual parity: `PASS`",
                        "- Unchecked TODO count: `0`",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            preflight_script = (
                Path(__file__).resolve().parent.parent
                / "examples"
                / "generate_manuscript_submission_preflight_report_2026-04-09.py"
            )
            proc = subprocess.run(
                [
                    "python",
                    str(preflight_script),
                    "--root-dir",
                    str(Path(__file__).resolve().parent.parent),
                    "--manuscript-dir",
                    str(manuscript_dir),
                    "--bundle-name",
                    "bundle.zip",
                    "--manifest-name",
                    "manifest.txt",
                    "--report-name",
                    "preflight.md",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)
            self.assertIn("verification_status=PASS", proc.stdout)
            self.assertIn("preflight_report_path=", proc.stdout)

            report = manuscript_dir / "preflight.md"
            self.assertTrue(report.exists())
            text = report.read_text(encoding="utf-8")
            self.assertIn("status: **PASS**", text)
            self.assertIn("bundle_sha256", text)
            self.assertIn("Completion Scorecard Gate", text)
            self.assertIn("readiness_gate: `PASS`", text)

    def test_preflight_report_script_fails_without_completion_scorecard(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            manuscript_dir = root / "manuscript"
            manuscript_dir.mkdir(parents=True, exist_ok=True)

            file_a = manuscript_dir / "a.txt"
            file_b = manuscript_dir / "b.txt"
            file_a.write_text("alpha\n", encoding="utf-8")
            file_b.write_text("beta\n", encoding="utf-8")

            manifest = manuscript_dir / "manifest.txt"
            manifest.write_text(
                "\n".join(
                    [
                        "bundle_name=bundle.zip",
                        "generated_at_utc=2026-04-09T00:00:00Z",
                        "file_count=2",
                        "---",
                        f"{_sha256(file_a)}  a.txt",
                        f"{_sha256(file_b)}  b.txt",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            bundle = manuscript_dir / "bundle.zip"
            with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(file_a, arcname="a.txt")
                archive.write(file_b, arcname="b.txt")
                archive.write(manifest, arcname="manifest.txt")

            preflight_script = (
                Path(__file__).resolve().parent.parent
                / "examples"
                / "generate_manuscript_submission_preflight_report_2026-04-09.py"
            )
            proc = subprocess.run(
                [
                    "python",
                    str(preflight_script),
                    "--root-dir",
                    str(Path(__file__).resolve().parent.parent),
                    "--manuscript-dir",
                    str(manuscript_dir),
                    "--bundle-name",
                    "bundle.zip",
                    "--manifest-name",
                    "manifest.txt",
                    "--report-name",
                    "preflight.md",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)
            self.assertIn("verification_status=PASS", proc.stdout)
            self.assertIn("preflight_report_path=", proc.stdout)

            report = manuscript_dir / "preflight.md"
            self.assertTrue(report.exists())
            text = report.read_text(encoding="utf-8")
            self.assertIn("status: **FAIL**", text)
            self.assertIn("scorecard_exists: `False`", text)
            self.assertIn("readiness_gate: `FAIL`", text)


if __name__ == "__main__":
    unittest.main()
