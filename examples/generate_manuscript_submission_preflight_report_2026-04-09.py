#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_manifest_header(path: Path) -> dict[str, str]:
    header: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == "---":
            break
        if "=" in line:
            key, value = line.split("=", 1)
            header[key.strip()] = value.strip()
    return header


def _git_commit(root_dir: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return "unknown"
    return proc.stdout.strip() or "unknown"


def _run_verify_script(
    *,
    root_dir: Path,
    manuscript_dir: Path,
    bundle_name: str,
    manifest_name: str,
) -> subprocess.CompletedProcess[str]:
    verify_script = root_dir / "examples" / "verify_manuscript_submission_bundle_2026-04-09.py"
    return subprocess.run(
        [
            "python",
            str(verify_script),
            "--manuscript-dir",
            str(manuscript_dir),
            "--bundle-name",
            bundle_name,
            "--manifest-name",
            manifest_name,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_completion_scorecard(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "exists": False,
            "completion_score_pct": None,
            "status": "MISSING",
            "consistency": "n/a",
            "bilingual_parity": "n/a",
            "unchecked_todo_count": None,
            "readiness_ok": False,
        }
    text = path.read_text(encoding="utf-8")
    score_match = re.search(r"- Completion score:\s+\*\*(\d+)%\*\*", text)
    status_match = re.search(r"- Status:\s+\*\*([A-Z_]+)\*\*", text)
    consistency_match = re.search(r"- Consistency:\s+`([^`]+)`", text)
    parity_match = re.search(r"- Bilingual parity:\s+`([^`]+)`", text)
    unchecked_match = re.search(r"- Unchecked TODO count:\s+`(\d+)`", text)
    score_value = int(score_match.group(1)) if score_match else None
    status_value = status_match.group(1) if status_match else "UNKNOWN"
    consistency_value = consistency_match.group(1) if consistency_match else "n/a"
    parity_value = parity_match.group(1) if parity_match else "n/a"
    unchecked_value = int(unchecked_match.group(1)) if unchecked_match else None
    readiness_ok = (
        score_value is not None
        and score_value >= 95
        and status_value == "READY_FOR_SUBMISSION"
        and consistency_value == "PASS"
        and parity_value == "PASS"
        and unchecked_value == 0
    )
    return {
        "exists": True,
        "completion_score_pct": score_value,
        "status": status_value,
        "consistency": consistency_value,
        "bilingual_parity": parity_value,
        "unchecked_todo_count": unchecked_value,
        "readiness_ok": readiness_ok,
    }


def _build_report(
    *,
    manuscript_dir: Path,
    bundle_name: str,
    manifest_name: str,
    report_name: str,
    verify_proc: subprocess.CompletedProcess[str],
    root_dir: Path,
) -> tuple[Path, bool]:
    bundle_path = manuscript_dir / bundle_name
    manifest_path = manuscript_dir / manifest_name
    report_path = manuscript_dir / report_name
    completion_scorecard_path = manuscript_dir / "manuscript_completion_scorecard_v0.2_2026-04-09.md"
    scorecard = _parse_completion_scorecard(completion_scorecard_path)

    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    readiness_ok = bool(scorecard["readiness_ok"])
    verify_ok = verify_proc.returncode == 0
    status = "PASS" if verify_ok and readiness_ok else "FAIL"
    bundle_sha = _sha256_file(bundle_path) if bundle_path.exists() else "missing"
    bundle_size = bundle_path.stat().st_size if bundle_path.exists() else 0
    manifest_header = _parse_manifest_header(manifest_path) if manifest_path.exists() else {}
    zip_count = 0
    if bundle_path.exists():
        with zipfile.ZipFile(bundle_path, "r") as archive:
            zip_count = len(archive.namelist())

    report_lines = [
        "# Manuscript Submission Preflight Report v0.2 (2026-04-09)",
        "",
        f"- status: **{status}**",
        f"- generated_at_utc: `{generated_at_utc}`",
        f"- git_commit: `{_git_commit(root_dir)}`",
        "",
        "## Bundle Metadata",
        f"- bundle_path: `{bundle_path}`",
        f"- bundle_size_bytes: `{bundle_size}`",
        f"- bundle_sha256: `{bundle_sha}`",
        f"- zip_entry_count: `{zip_count}`",
        "",
        "## Manifest Metadata",
        f"- manifest_path: `{manifest_path}`",
        f"- manifest_bundle_name: `{manifest_header.get('bundle_name', 'n/a')}`",
        f"- manifest_generated_at_utc: `{manifest_header.get('generated_at_utc', 'n/a')}`",
        f"- manifest_file_count: `{manifest_header.get('file_count', 'n/a')}`",
        "",
        "## Completion Scorecard Gate",
        f"- scorecard_path: `{completion_scorecard_path}`",
        f"- scorecard_exists: `{scorecard['exists']}`",
        f"- completion_score_pct: `{scorecard['completion_score_pct']}`",
        f"- scorecard_status: `{scorecard['status']}`",
        f"- scorecard_consistency: `{scorecard['consistency']}`",
        f"- scorecard_bilingual_parity: `{scorecard['bilingual_parity']}`",
        f"- scorecard_unchecked_todo_count: `{scorecard['unchecked_todo_count']}`",
        f"- readiness_gate: `{'PASS' if readiness_ok else 'FAIL'}`",
        "",
        "## Verification Output",
        "```text",
        verify_proc.stdout.strip(),
        verify_proc.stderr.strip(),
        "```",
        "",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return report_path, status == "PASS"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate submission preflight report from bundle + manifest.")
    parser.add_argument(
        "--root-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root path.",
    )
    parser.add_argument(
        "--manuscript-dir",
        type=Path,
        default=Path("docs/manuscript/v0.2_2026-04-09"),
        help="Directory that contains bundle and manifest.",
    )
    parser.add_argument(
        "--bundle-name",
        type=str,
        default="submission_bundle_v0.2_2026-04-09.zip",
        help="Bundle zip filename.",
    )
    parser.add_argument(
        "--manifest-name",
        type=str,
        default="submission_bundle_manifest_v0.2_2026-04-09.txt",
        help="Manifest filename.",
    )
    parser.add_argument(
        "--report-name",
        type=str,
        default="manuscript_submission_preflight_report_v0.2_2026-04-09.md",
        help="Output markdown report filename.",
    )
    args = parser.parse_args()

    root_dir = args.root_dir.resolve()
    manuscript_dir = args.manuscript_dir
    if not manuscript_dir.is_absolute():
        manuscript_dir = (root_dir / manuscript_dir).resolve()

    verify_proc = _run_verify_script(
        root_dir=root_dir,
        manuscript_dir=manuscript_dir,
        bundle_name=args.bundle_name,
        manifest_name=args.manifest_name,
    )
    if verify_proc.stdout:
        print(verify_proc.stdout.rstrip())
    if verify_proc.stderr:
        print(verify_proc.stderr.rstrip(), file=sys.stderr)

    report_path, overall_ok = _build_report(
        manuscript_dir=manuscript_dir,
        bundle_name=args.bundle_name,
        manifest_name=args.manifest_name,
        report_name=args.report_name,
        verify_proc=verify_proc,
        root_dir=root_dir,
    )
    print(f"preflight_report_path={report_path}")
    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
