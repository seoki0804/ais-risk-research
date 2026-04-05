from __future__ import annotations

import argparse
from pathlib import Path

from .ingestion_bundles import (
    get_ingestion_bundle,
    list_ingestion_bundle_names,
    render_ingestion_bundle_toml,
    write_ingestion_bundle_template,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or export ingestion preset bundle templates.")
    parser.add_argument("--list", action="store_true", help="List available ingestion bundles.")
    parser.add_argument("--name", help="Bundle name to inspect or export.")
    parser.add_argument("--output", help="Optional output path to write the selected bundle TOML template.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.list:
        for name in list_ingestion_bundle_names():
            bundle = get_ingestion_bundle(name)
            print(f"{bundle.name}: {bundle.description}")
        return 0

    if not args.name:
        raise SystemExit("--name is required unless --list is used.")

    bundle = get_ingestion_bundle(args.name)
    if args.output:
        path = write_ingestion_bundle_template(bundle.name, Path(args.output))
        print(f"saved={path}")
        return 0

    print(render_ingestion_bundle_toml(bundle))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
