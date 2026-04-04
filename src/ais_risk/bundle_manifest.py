from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256_of_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _git_metadata(probe_dir: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "available": False,
        "commit": None,
        "dirty": None,
    }
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(probe_dir), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        dirty_status = subprocess.check_output(
            ["git", "-C", str(probe_dir), "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        metadata["available"] = True
        metadata["commit"] = commit
        metadata["dirty"] = bool(dirty_status)
    except Exception:
        pass
    return metadata


def _normalize_copied_file_names(copied_files: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in copied_files:
        name = str(item).strip()
        if not name:
            continue
        if name not in normalized:
            normalized.append(name)
    return normalized


def _build_file_entry(path: Path, label: str) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "label": label,
        "path": str(resolved),
        "exists": resolved.exists(),
        "bytes": resolved.stat().st_size if resolved.exists() else None,
        "sha256": _sha256_of_file(resolved) if resolved.exists() else None,
    }


def build_bundle_manifest(
    bundle_date: str,
    bundle_dir: str | Path,
    copied_files: list[str],
    source_dirs: dict[str, str | Path],
    input_files: list[str | Path] | None = None,
    command_logs: list[str | Path] | None = None,
    manifest_txt_path: str | Path | None = None,
    manifest_json_path: str | Path | None = None,
) -> dict[str, Any]:
    bundle_root = Path(bundle_dir).resolve()
    bundle_root.mkdir(parents=True, exist_ok=True)

    normalized_copied = _normalize_copied_file_names(copied_files)
    if not normalized_copied:
        raise ValueError("At least one copied file is required.")

    copied_entries: list[dict[str, Any]] = []
    for file_name in normalized_copied:
        file_path = (bundle_root / file_name).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Copied file does not exist in bundle directory: {file_path}")
        copied_entries.append(
            {
                "name": file_name,
                "path": str(file_path),
                "bytes": file_path.stat().st_size,
                "sha256": _sha256_of_file(file_path),
            }
        )

    source_entries: list[dict[str, Any]] = []
    for label in sorted(source_dirs.keys()):
        source_path = Path(source_dirs[label]).resolve()
        source_entries.append(
            {
                "label": label,
                "path": str(source_path),
                "exists": source_path.exists(),
            }
        )

    input_entries: list[dict[str, Any]] = []
    for item in input_files or []:
        item_path = Path(item).resolve()
        if not item_path.exists():
            raise FileNotFoundError(f"Input file for manifest does not exist: {item_path}")
        input_entries.append(_build_file_entry(item_path, label=item_path.name))

    command_log_entries: list[dict[str, Any]] = []
    for item in command_logs or []:
        item_path = Path(item).resolve()
        command_log_entries.append(_build_file_entry(item_path, label=item_path.name))

    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    git_info = _git_metadata(bundle_root)

    payload: dict[str, Any] = {
        "bundle_date": str(bundle_date),
        "generated_at_utc": generated_at_utc,
        "bundle_dir": str(bundle_root),
        "git": git_info,
        "source_dirs": source_entries,
        "input_files": input_entries,
        "command_logs": command_log_entries,
        "copied_files": copied_entries,
    }

    txt_path = Path(manifest_txt_path).resolve() if manifest_txt_path else bundle_root / f"bundle_manifest_{bundle_date}.txt"
    json_path = Path(manifest_json_path).resolve() if manifest_json_path else bundle_root / f"bundle_manifest_{bundle_date}.json"
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        f"bundle_date={payload['bundle_date']}",
        f"generated_at_utc={payload['generated_at_utc']}",
        f"bundle_dir={payload['bundle_dir']}",
        f"git_available={git_info['available']}",
        f"git_commit={git_info['commit'] or 'n/a'}",
        f"git_dirty={git_info['dirty'] if git_info['dirty'] is not None else 'n/a'}",
        "source_dirs=",
    ]
    for item in source_entries:
        lines.append(f"  - {item['label']}={item['path']} | exists={item['exists']}")

    lines.append("input_files=")
    for item in input_entries:
        lines.append(f"  - {item['path']} | sha256={item['sha256']} | bytes={item['bytes']}")

    lines.append("command_logs=")
    for item in command_log_entries:
        if item["exists"]:
            lines.append(f"  - {item['path']} | sha256={item['sha256']} | bytes={item['bytes']}")
        else:
            lines.append(f"  - {item['path']} | exists=false")

    lines.append("copied_files=")
    for item in copied_entries:
        lines.append(f"  - {item['name']} | sha256={item['sha256']} | bytes={item['bytes']}")

    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "status": "completed",
        "bundle_date": str(bundle_date),
        "bundle_dir": str(bundle_root),
        "manifest_txt_path": str(txt_path),
        "manifest_json_path": str(json_path),
        "copied_file_count": len(copied_entries),
        "input_file_count": len(input_entries),
        "command_log_count": len(command_log_entries),
    }
