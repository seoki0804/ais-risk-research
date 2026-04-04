from __future__ import annotations

import argparse

from .bundle_manifest import build_bundle_manifest


def _parse_label_path_pairs(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values:
        raw = str(item).strip()
        if not raw:
            continue
        if "=" not in raw:
            raise ValueError(f"--source-dir must be label=path format. got: {raw}")
        label, path = raw.split("=", 1)
        label = label.strip()
        path = path.strip()
        if not label or not path:
            raise ValueError(f"--source-dir must include non-empty label and path. got: {raw}")
        parsed[label] = path
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bundle manifest with hashes and command provenance.")
    parser.add_argument("--bundle-date", required=True, help="Bundle date identifier (e.g., 2026-04-04-expanded).")
    parser.add_argument("--bundle-dir", required=True, help="Bundle directory where copied artifacts exist.")
    parser.add_argument(
        "--copied-file",
        action="append",
        required=True,
        help="Copied file name relative to --bundle-dir. Repeat for each file.",
    )
    parser.add_argument(
        "--source-dir",
        action="append",
        default=[],
        help="Source directory in label=path format. Repeat for each source category.",
    )
    parser.add_argument(
        "--input-file",
        action="append",
        default=[],
        help="Input file to hash for reproducibility. Repeat for each file.",
    )
    parser.add_argument(
        "--command-log",
        action="append",
        default=[],
        help="Command log path to include in provenance section. Repeat if needed.",
    )
    parser.add_argument("--manifest-txt", default="", help="Optional output path for text manifest.")
    parser.add_argument("--manifest-json", default="", help="Optional output path for JSON manifest.")
    args = parser.parse_args()

    source_dirs = _parse_label_path_pairs(list(args.source_dir))
    summary = build_bundle_manifest(
        bundle_date=args.bundle_date,
        bundle_dir=args.bundle_dir,
        copied_files=list(args.copied_file),
        source_dirs=source_dirs,
        input_files=list(args.input_file),
        command_logs=list(args.command_log),
        manifest_txt_path=(args.manifest_txt or None),
        manifest_json_path=(args.manifest_json or None),
    )
    print(f"manifest_txt={summary['manifest_txt_path']}")
    print(f"manifest_json={summary['manifest_json_path']}")
    print(f"copied_file_count={summary['copied_file_count']}")
    print(f"input_file_count={summary['input_file_count']}")
    print(f"command_log_count={summary['command_log_count']}")


if __name__ == "__main__":
    main()
