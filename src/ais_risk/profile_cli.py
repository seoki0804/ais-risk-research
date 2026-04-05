from __future__ import annotations

import argparse
from pathlib import Path

from .profile import profile_curated_csv, save_profile_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Profile curated or reconstructed AIS CSV and save JSON/Markdown summaries.")
    parser.add_argument("--input", required=True, help="Path to curated or reconstructed AIS CSV.")
    parser.add_argument("--output-prefix", required=True, help="Prefix for profile outputs.")
    parser.add_argument("--top-n", type=int, default=10, help="Top vessels to include by row count.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    profile = profile_curated_csv(Path(args.input), top_n=int(args.top_n))
    json_path, md_path = save_profile_outputs(Path(args.output_prefix), profile)
    print(f"saved_json={json_path}")
    print(f"saved_markdown={md_path}")
    print(f"row_count={profile['row_count']}")
    print(f"unique_vessels={profile['unique_vessels']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
