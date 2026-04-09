#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_manifest(manifest_path: Path) -> tuple[dict[str, str], dict[str, str]]:
    header: dict[str, str] = {}
    hashes: dict[str, str] = {}
    in_hash_section = False
    for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == "---":
            in_hash_section = True
            continue
        if not in_hash_section:
            if "=" in line:
                key, value = line.split("=", 1)
                header[key.strip()] = value.strip()
            continue
        parts = line.split()
        if len(parts) < 2:
            raise ValueError(f"Invalid hash line in manifest: {raw_line}")
        hashes[parts[1]] = parts[0]
    if not hashes:
        raise ValueError("Manifest has no hash entries.")
    return header, hashes


def verify_bundle(*, manuscript_dir: Path, bundle_name: str, manifest_name: str) -> int:
    bundle_path = manuscript_dir / bundle_name
    manifest_path = manuscript_dir / manifest_name

    if not bundle_path.exists():
        print(f"ERROR: bundle not found: {bundle_path}")
        return 1
    if not manifest_path.exists():
        print(f"ERROR: manifest not found: {manifest_path}")
        return 1

    header, manifest_hashes = _parse_manifest(manifest_path)
    expected_count_value = header.get("file_count")
    expected_count = int(expected_count_value) if expected_count_value and expected_count_value.isdigit() else None
    if expected_count is not None and expected_count != len(manifest_hashes):
        print(
            "ERROR: manifest file_count mismatch: "
            f"header={expected_count} actual={len(manifest_hashes)}"
        )
        return 1

    with zipfile.ZipFile(bundle_path, "r") as archive:
        zip_entries = set(archive.namelist())
        if manifest_name not in zip_entries:
            print(f"ERROR: zip missing embedded manifest entry: {manifest_name}")
            return 1

        missing_entries = [name for name in manifest_hashes if name not in zip_entries]
        if missing_entries:
            print("ERROR: zip missing files listed in manifest:")
            for name in missing_entries:
                print(f"- {name}")
            return 1

        hash_mismatches: list[tuple[str, str, str]] = []
        for name, expected_hash in manifest_hashes.items():
            zip_hash = _sha256_bytes(archive.read(name))
            if zip_hash != expected_hash:
                hash_mismatches.append((name, expected_hash, zip_hash))
                continue
            local_path = manuscript_dir / name
            if not local_path.exists():
                hash_mismatches.append((name, expected_hash, "missing_local_file"))
                continue
            local_hash = _sha256_file(local_path)
            if local_hash != expected_hash:
                hash_mismatches.append((name, expected_hash, local_hash))

        if hash_mismatches:
            print("ERROR: checksum mismatches detected:")
            for name, expected_hash, observed_hash in hash_mismatches:
                print(f"- {name}: expected={expected_hash} observed={observed_hash}")
            return 1

    zip_sha = _sha256_file(bundle_path)
    print(f"verification_status=PASS")
    print(f"verified_file_count={len(manifest_hashes)}")
    print(f"verified_bundle_zip_sha256={zip_sha}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify submission bundle against manifest checksums.")
    parser.add_argument(
        "--manuscript-dir",
        type=Path,
        default=Path("docs/manuscript/v0.2_2026-04-09"),
        help="Directory that contains bundle zip and manifest.",
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
    args = parser.parse_args()
    sys.exit(
        verify_bundle(
            manuscript_dir=args.manuscript_dir,
            bundle_name=args.bundle_name,
            manifest_name=args.manifest_name,
        )
    )


if __name__ == "__main__":
    main()
