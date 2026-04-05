from __future__ import annotations

import argparse
from pathlib import Path

from .dataset_manifest import (
    build_dataset_id,
    build_first_dataset_manifest_markdown,
    save_first_dataset_manifest,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a first public AIS dataset manifest markdown for reproducible ingestion."
    )
    parser.add_argument("--source-slug", default="dma", help="Short source slug used in dataset_id.")
    parser.add_argument("--area-slug", required=True, help="Short area slug used in dataset_id.")
    parser.add_argument("--start-date", required=True, help="Start date in YYYY-MM-DD.")
    parser.add_argument("--end-date", required=True, help="End date in YYYY-MM-DD.")
    parser.add_argument("--version", default="v1", help="Dataset version suffix.")
    parser.add_argument("--dataset-id", help="Optional explicit dataset_id. If omitted, it is auto-generated.")

    parser.add_argument("--source-name", required=True, help="Human-readable source name.")
    parser.add_argument("--source-url", required=True, help="Source URL.")
    parser.add_argument("--license-url", required=True, help="License/terms URL.")
    parser.add_argument("--area", required=True, help="Human-readable area name.")
    parser.add_argument("--source-type", default="historical CSV", help="Source type text.")
    parser.add_argument("--status-tag", default="[합리적 가정]", help="Status tag line.")
    parser.add_argument("--author", default="Codex", help="Manifest author.")
    parser.add_argument("--created-date", help="Optional created date override in YYYY-MM-DD.")
    parser.add_argument("--notes", default="", help="Optional risk/note line.")
    parser.add_argument("--source-preset", default="auto", help="Default source preset.")
    parser.add_argument("--vessel-type-filter", default="cargo,tanker,tug,passenger", help="Default vessel-type filter.")
    parser.add_argument("--split-gap-min", type=int, default=10, help="Split gap minutes.")
    parser.add_argument("--max-interp-gap-min", type=int, default=2, help="Max interpolation gap minutes.")
    parser.add_argument("--step-sec", type=int, default=30, help="Interpolation step seconds.")
    parser.add_argument("--raw-root", help="Raw data root. Defaults to data/raw/{source-slug}.")
    parser.add_argument("--curated-root", default="data/curated", help="Curated data root path.")
    parser.add_argument("--outputs-root", default="outputs", help="Outputs root path.")
    parser.add_argument("--output", help="Output path for markdown. Defaults to data/manifests/{dataset_id}.md")
    args = parser.parse_args()

    dataset_id = args.dataset_id or build_dataset_id(
        source_slug=args.source_slug,
        area_slug=args.area_slug,
        start_date_text=args.start_date,
        end_date_text=args.end_date,
        version=args.version,
    )
    raw_root = args.raw_root or str(Path("data/raw") / args.source_slug)

    text = build_first_dataset_manifest_markdown(
        dataset_id=dataset_id,
        source_name=args.source_name,
        source_url=args.source_url,
        license_url=args.license_url,
        area=args.area,
        start_date_text=args.start_date,
        end_date_text=args.end_date,
        source_type=args.source_type,
        status_tag=args.status_tag,
        author=args.author,
        created_date=args.created_date,
        notes=args.notes,
        source_preset=args.source_preset,
        vessel_type_filter=args.vessel_type_filter,
        split_gap_min=args.split_gap_min,
        max_interp_gap_min=args.max_interp_gap_min,
        step_sec=args.step_sec,
        raw_root=raw_root,
        curated_root=args.curated_root,
        outputs_root=args.outputs_root,
    )
    output_path = args.output or str(Path("data/manifests") / f"{dataset_id}.md")
    saved = save_first_dataset_manifest(output_path, text)
    print(f"dataset_id={dataset_id}")
    print(f"manifest={saved}")


if __name__ == "__main__":
    main()
