from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dataset_manifest import infer_source_slug_from_dataset_id, parse_first_dataset_manifest
from .noaa_fetch import fetch_noaa_archives


def resolve_noaa_fetch_plan(
    start_date: str | None,
    end_date: str | None,
    output_dir: str | None,
    manifest_path: str | None = None,
    dataset_id: str | None = None,
) -> dict[str, str]:
    manifest_info: dict[str, str | None] = {}
    if manifest_path:
        parsed = parse_first_dataset_manifest(manifest_path)
        manifest_info = {
            "dataset_id": str(parsed["dataset_id"]),
            "start_date": parsed.get("start_date"),
            "end_date": parsed.get("end_date"),
        }

    resolved_dataset_id = dataset_id or manifest_info.get("dataset_id")
    resolved_start_date = start_date or manifest_info.get("start_date")
    resolved_end_date = end_date or manifest_info.get("end_date")
    if not resolved_start_date or not resolved_end_date:
        raise ValueError(
            "start-date and end-date are required. "
            "Provide them directly or pass a manifest that includes 시작 시각/종료 시각."
        )

    if output_dir:
        resolved_output_dir = Path(output_dir)
    else:
        if not resolved_dataset_id:
            raise ValueError(
                "output-dir is required when dataset_id cannot be resolved. "
                "Pass --output-dir or provide --manifest/--dataset-id."
            )
        source_slug = infer_source_slug_from_dataset_id(resolved_dataset_id)
        resolved_output_dir = Path("data/raw") / source_slug / resolved_dataset_id / "downloads"

    return {
        "start_date": resolved_start_date,
        "end_date": resolved_end_date,
        "dataset_id": str(resolved_dataset_id) if resolved_dataset_id else "",
        "output_dir": str(resolved_output_dir),
        "manifest_path": manifest_path or "",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download NOAA MarineCadastre AIS zip archives by date range. "
            "Date range/output can be inferred from a dataset manifest."
        )
    )
    parser.add_argument("--manifest", help="Optional dataset manifest markdown path.")
    parser.add_argument("--dataset-id", help="Optional dataset_id override used for default output-dir.")
    parser.add_argument("--start-date", help="Start date in YYYY-MM-DD.")
    parser.add_argument("--end-date", help="End date in YYYY-MM-DD.")
    parser.add_argument(
        "--output-dir",
        help="Directory to store downloaded files. If omitted, defaults to data/raw/{source}/{dataset_id}/downloads.",
    )
    parser.add_argument(
        "--base-url",
        default="https://coast.noaa.gov/htdata/CMSP/AISDataHandler",
        help="Base URL root for NOAA AIS archives.",
    )
    parser.add_argument(
        "--fallback-base-urls",
        help="Optional comma-separated fallback base URLs tried when primary base-url fails.",
    )
    parser.add_argument(
        "--year-dir-template",
        default="{year}",
        help="Directory template under base-url. Supports {year},{month},{day},{date},{date_dash}.",
    )
    parser.add_argument(
        "--filename-template",
        default="AIS_{year}_{month}_{day}.zip",
        help="Filename template. Supports {year},{month},{day},{date},{date_dash}.",
    )
    parser.add_argument("--timeout-sec", type=int, default=90, help="Network timeout seconds per download attempt.")
    parser.add_argument("--max-attempts", type=int, default=3, help="Maximum retry attempts per candidate URL.")
    parser.add_argument("--extract", action="store_true", help="Extract zip files after download.")
    parser.add_argument("--dry-run", action="store_true", help="Only print planned URLs without downloading.")
    parser.add_argument("--no-skip-existing", action="store_true", help="Re-download files even if they already exist.")
    parser.add_argument("--summary-json", help="Optional path to save fetch summary as JSON.")
    args = parser.parse_args()

    plan = resolve_noaa_fetch_plan(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        dataset_id=args.dataset_id,
    )
    fallback_base_urls = []
    if args.fallback_base_urls:
        fallback_base_urls = [item.strip() for item in args.fallback_base_urls.split(",") if item.strip()]

    summary = fetch_noaa_archives(
        start_date=plan["start_date"],
        end_date=plan["end_date"],
        output_dir=plan["output_dir"],
        base_url=args.base_url,
        fallback_base_urls=fallback_base_urls,
        year_dir_template=args.year_dir_template,
        filename_template=args.filename_template,
        extract=bool(args.extract),
        dry_run=bool(args.dry_run),
        skip_existing=not bool(args.no_skip_existing),
        timeout_sec=max(1, int(args.timeout_sec)),
        max_attempts=max(1, int(args.max_attempts)),
    )
    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"summary_json={summary_path}")
    if plan["manifest_path"]:
        print(f"manifest={plan['manifest_path']}")
    if plan["dataset_id"]:
        print(f"dataset_id={plan['dataset_id']}")
    print(f"start_date={plan['start_date']}")
    print(f"end_date={plan['end_date']}")
    print(f"output_dir={plan['output_dir']}")
    print(f"timeout_sec={max(1, int(args.timeout_sec))}")
    print(f"max_attempts={max(1, int(args.max_attempts))}")
    if fallback_base_urls:
        print(f"fallback_base_urls={','.join(fallback_base_urls)}")
    print(f"status={summary['status']}")
    print(f"planned={summary['planned_count']}")
    print(f"downloaded={summary['downloaded_count']}")
    print(f"skipped={summary['skipped_count']}")
    print(f"failed={summary['failed_count']}")


if __name__ == "__main__":
    main()
