#!/usr/bin/env python3
"""Verify snapshot integrity and source drift for 61day release snapshots."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
from pathlib import Path


DEFAULT_ROOT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13"
)
DEFAULT_SNAPSHOT_ROOT = DEFAULT_ROOT / "submission_release_snapshots_61day"
DEFAULT_OUTPUT = DEFAULT_ROOT / "submission_release_snapshot_verify_latest_61day.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-dir", help="Snapshot directory to verify.")
    parser.add_argument("--snapshot-root", default=str(DEFAULT_SNAPSHOT_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--strict-source-match",
        action="store_true",
        help="Return non-zero when source files drift from the snapshot hash.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def choose_snapshot_dir(args: argparse.Namespace) -> Path:
    if args.snapshot_dir:
        return Path(args.snapshot_dir)
    root = Path(args.snapshot_root)
    candidates = sorted(
        [
            p
            for p in root.iterdir()
            if p.is_dir() and re.fullmatch(r"\d{8}_\d{6}", p.name)
        ]
    )
    if not candidates:
        raise FileNotFoundError(f"No snapshot directories found under {root}")
    return candidates[-1]


def parse_manifest(manifest: Path) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    lines = manifest.read_text(encoding="utf-8").splitlines()
    for idx, raw in enumerate(lines):
        file_match = re.match(r"- `([^`]+)`: `([0-9a-fA-F]+)`", raw.strip())
        if not file_match:
            continue
        file_name = file_match.group(1)
        expected_hash = file_match.group(2).lower()
        source_path = ""
        if idx + 1 < len(lines):
            src_match = re.match(r"- source: `([^`]+)`", lines[idx + 1].strip())
            if src_match:
                source_path = src_match.group(1)
        entries.append((file_name, expected_hash, source_path))
    return entries


def build_report(
    generated_at: str,
    snapshot_dir: Path,
    manifest: Path,
    output: Path,
    integrity_status: str,
    source_status: str,
    overall_status: str,
    rows: list[tuple[str, str, str, str, str, str]],
) -> str:
    lines = [
        "# Submission Release Snapshot Verification 61day",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Snapshot directory: `{snapshot_dir}`",
        f"- Manifest: `{manifest}`",
        f"- Output: `{output}`",
        f"- Snapshot integrity: `{integrity_status}`",
        f"- Source drift check: `{source_status}`",
        f"- Overall status: `{overall_status}`",
        "",
        "## File Verification",
        "| File | Expected SHA256 | Snapshot hash | Snapshot match | Source hash | Source match |",
        "|---|---|---|---|---|---|",
    ]
    for name, expected, snap_hash, snap_match, source_hash, source_match in rows:
        lines.append(
            f"| `{name}` | `{expected}` | `{snap_hash}` | `{snap_match}` | `{source_hash}` | `{source_match}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "- `Snapshot integrity` checks whether files inside the snapshot directory still match its manifest hashes.",
            "- `Source drift check` compares current source files against the frozen snapshot hashes.",
            "- `PASS` means frozen files are intact and current sources still match.",
            "- `ATTENTION` means frozen files are intact but current sources have changed since the snapshot.",
            "- `FAIL` means the snapshot itself is inconsistent with its manifest and must not be used as a release reference.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    snapshot_dir = choose_snapshot_dir(args)
    output = Path(args.output)
    manifest = snapshot_dir / "SNAPSHOT_MANIFEST_61day.md"
    if not manifest.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest}")

    entries = parse_manifest(manifest)
    if not entries:
        raise RuntimeError(f"No file entries found in manifest: {manifest}")

    rows: list[tuple[str, str, str, str, str, str]] = []
    integrity_ok = True
    source_all_match = True
    source_any_missing = False

    for file_name, expected_hash, source_path in entries:
        snap_file = snapshot_dir / file_name
        if snap_file.exists():
            snap_hash = sha256(snap_file).lower()
            snap_match = "PASS" if snap_hash == expected_hash else "FAIL"
        else:
            snap_hash = "MISSING"
            snap_match = "FAIL"
        if snap_match == "FAIL":
            integrity_ok = False

        source_hash = "UNKNOWN"
        source_match = "UNKNOWN"
        if source_path:
            src = Path(source_path)
            if src.exists():
                source_hash = sha256(src).lower()
                source_match = "PASS" if source_hash == expected_hash else "DRIFT"
                if source_match != "PASS":
                    source_all_match = False
            else:
                source_hash = "MISSING"
                source_match = "MISSING"
                source_any_missing = True
                source_all_match = False

        rows.append((file_name, expected_hash, snap_hash, snap_match, source_hash, source_match))

    integrity_status = "PASS" if integrity_ok else "BROKEN"
    if source_all_match:
        source_status = "MATCH"
    elif source_any_missing:
        source_status = "MISSING_OR_DRIFT"
    else:
        source_status = "DRIFT"

    if not integrity_ok:
        overall = "FAIL"
    elif source_all_match:
        overall = "PASS"
    else:
        overall = "ATTENTION"

    generated_at = dt.datetime.now().isoformat(timespec="seconds")
    report = build_report(
        generated_at=generated_at,
        snapshot_dir=snapshot_dir,
        manifest=manifest,
        output=output,
        integrity_status=integrity_status,
        source_status=source_status,
        overall_status=overall,
        rows=rows,
    )
    output.write_text(report, encoding="utf-8")

    print(f"Snapshot integrity: {integrity_status}")
    print(f"Source drift check: {source_status}")
    print(f"Overall status: {overall}")
    print(f"Report: {output}")

    if overall == "FAIL":
        raise SystemExit(1)
    if args.strict_source_match and overall == "ATTENTION":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
