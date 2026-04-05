from __future__ import annotations

import argparse
from pathlib import Path

from .paper_assets import build_paper_assets_from_manifest_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate paper-ready tables and captions from a demo package manifest.")
    parser.add_argument("--manifest", required=True, help="Path to demo package manifest.json.")
    parser.add_argument("--output-dir", help="Optional output directory. Defaults to the manifest output_dir.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = build_paper_assets_from_manifest_path(
        manifest_path=Path(args.manifest),
        output_dir=None if not args.output_dir else Path(args.output_dir),
    )
    print(f"saved={payload['paper_assets_manifest_path']}")
    print(f"case_table={payload['paper_case_csv_path']}")
    print(f"scenario_table={payload['paper_scenario_csv_path']}")
    print(f"ablation_table={payload['paper_ablation_csv_path']}")
    print(f"captions={payload['paper_figure_captions_path']}")
    print(f"summary={payload['paper_summary_note_path']}")
    print(f"appendix_md={payload['paper_appendix_md_path']}")
    print(f"appendix_tex={payload['paper_appendix_tex_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
