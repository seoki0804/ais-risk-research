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


class SubmissionBundleVerifyScriptTest(unittest.TestCase):
    def test_verify_script_passes_for_valid_bundle(self) -> None:
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

            verify_script = (
                Path(__file__).resolve().parent.parent
                / "examples"
                / "verify_manuscript_submission_bundle_2026-04-09.py"
            )
            proc = subprocess.run(
                [
                    "python",
                    str(verify_script),
                    "--manuscript-dir",
                    str(manuscript_dir),
                    "--bundle-name",
                    "bundle.zip",
                    "--manifest-name",
                    "manifest.txt",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)
            self.assertIn("verification_status=PASS", proc.stdout)

    def test_verify_script_fails_when_local_file_is_modified(self) -> None:
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

            file_b.write_text("tampered\n", encoding="utf-8")

            verify_script = (
                Path(__file__).resolve().parent.parent
                / "examples"
                / "verify_manuscript_submission_bundle_2026-04-09.py"
            )
            proc = subprocess.run(
                [
                    "python",
                    str(verify_script),
                    "--manuscript-dir",
                    str(manuscript_dir),
                    "--bundle-name",
                    "bundle.zip",
                    "--manifest-name",
                    "manifest.txt",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(proc.returncode, 0, msg=proc.stdout + "\n" + proc.stderr)
            self.assertIn("checksum mismatches", proc.stdout)


if __name__ == "__main__":
    unittest.main()
