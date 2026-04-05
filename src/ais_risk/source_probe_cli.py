from __future__ import annotations

import argparse

from .source_probe import list_public_source_ids, run_public_source_probe


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe connectivity of public AIS source pages before data ingestion."
    )
    parser.add_argument("--output-prefix", help="Output prefix for probe summary files.")
    parser.add_argument(
        "--source-ids",
        help="Optional comma-separated source ids. If omitted, probes all known sources.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=8.0,
        help="Timeout per request in seconds.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Retry count for network-level failures.",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List supported source ids and exit.",
    )
    args = parser.parse_args()

    if args.list_sources:
        for source_id in list_public_source_ids():
            print(source_id)
        return

    if not args.output_prefix:
        raise SystemExit("--output-prefix is required unless --list-sources is used.")

    source_ids = None
    if args.source_ids:
        source_ids = [item.strip() for item in args.source_ids.split(",") if item.strip()]

    summary = run_public_source_probe(
        output_prefix=args.output_prefix,
        source_ids=source_ids,
        timeout_seconds=float(args.timeout_seconds),
        retries=max(0, int(args.retries)),
    )
    print(f"status={summary['status']}")
    print(f"row_count={summary['row_count']}")
    print(f"ok_count={summary['ok_count']}")
    print(f"restricted_count={summary['restricted_count']}")
    print(f"failed_count={summary['failed_count']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")


if __name__ == "__main__":
    main()
