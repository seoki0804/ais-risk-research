#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download NOAA AIS daily zip with resume + parallel range parts."
    )
    parser.add_argument("--date", required=True, help="Target date in YYYY-MM-DD format.")
    parser.add_argument(
        "--output",
        required=False,
        help="Output zip path. Defaults to data/raw/noaa/noaa_us_coastal_all_<date>_<date>_v1/downloads/AIS_<YYYY_MM_DD>.zip",
    )
    parser.add_argument("--parts", type=int, default=12, help="Parallel range part count.")
    parser.add_argument("--max-retries", type=int, default=5, help="Retry count per part.")
    parser.add_argument("--timeout-sec", type=int, default=90, help="HTTP timeout per request.")
    return parser.parse_args()


def default_output_path(date_str: str) -> Path:
    dataset_id = f"noaa_us_coastal_all_{date_str}_{date_str}_v1"
    zip_name = f"AIS_{date_str.replace('-', '_')}.zip"
    return Path("data/raw/noaa") / dataset_id / "downloads" / zip_name


def download(date_str: str, out: Path, parts: int, max_retries: int, timeout_sec: int) -> None:
    url = f"https://coast.noaa.gov/htdata/CMSP/AISDataHandler/2023/AIS_{date_str.replace('-', '_')}.zip"
    out.parent.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        head = session.head(url, timeout=30)
        head.raise_for_status()
        total = int(head.headers.get("Content-Length", "0"))
        if total <= 0:
            raise RuntimeError("Content-Length missing or zero.")

        current = out.stat().st_size if out.exists() else 0
        print(f"url={url}")
        print(f"total_bytes={total}")
        print(f"current_bytes={current}")

        if current >= total:
            print("status=already_complete")
            return

        start = current
        remaining = total - start
        step = math.ceil(remaining / max(parts, 1))
        ranges: list[tuple[int, int, int]] = []
        for idx in range(max(parts, 1)):
            s = start + idx * step
            if s >= total:
                continue
            e = min(total - 1, s + step - 1)
            ranges.append((idx, s, e))

        print(f"part_count={len(ranges)}")
        print(f"part_step_bytes={step}")

        def fetch_part(part_idx: int, s: int, e: int) -> tuple[int, int]:
            part_path = out.with_suffix(out.suffix + f".part{part_idx}")
            if part_path.exists():
                part_path.unlink()

            headers = {"Range": f"bytes={s}-{e}"}
            expected = e - s + 1

            for attempt in range(1, max_retries + 1):
                try:
                    with session.get(url, headers=headers, stream=True, timeout=timeout_sec) as resp:
                        if resp.status_code != 206:
                            raise RuntimeError(f"unexpected_status={resp.status_code}")
                        downloaded = 0
                        with open(part_path, "wb") as fp:
                            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                                if not chunk:
                                    continue
                                fp.write(chunk)
                                downloaded += len(chunk)
                        if downloaded != expected:
                            raise RuntimeError(
                                f"size_mismatch downloaded={downloaded} expected={expected}"
                            )
                        return part_idx, downloaded
                except Exception as ex:  # noqa: BLE001
                    if attempt == max_retries:
                        raise
                    print(f"part={part_idx} retry={attempt} error={type(ex).__name__}:{ex}")
                    time.sleep(2)
            raise RuntimeError("unreachable")

        started_at = time.time()
        results: list[tuple[int, int]] = []

        with ThreadPoolExecutor(max_workers=len(ranges)) as executor:
            futures = [executor.submit(fetch_part, idx, s, e) for idx, s, e in ranges]
            for future in as_completed(futures):
                part_idx, downloaded = future.result()
                print(f"part_done={part_idx} bytes={downloaded}")
                results.append((part_idx, downloaded))

        results.sort(key=lambda row: row[0])
        with open(out, "ab") as dst:
            for part_idx, _ in results:
                part_path = out.with_suffix(out.suffix + f".part{part_idx}")
                with open(part_path, "rb") as src:
                    while True:
                        buf = src.read(1024 * 1024)
                        if not buf:
                            break
                        dst.write(buf)
                part_path.unlink()

        final_size = out.stat().st_size
        elapsed = time.time() - started_at
        print(f"final_bytes={final_size}")
        print(f"elapsed_sec={elapsed:.1f}")
        print("status=completed" if final_size == total else "status=size_mismatch")
        if final_size != total:
            raise RuntimeError("Final size mismatch after merge.")


def main() -> None:
    args = parse_args()
    out = Path(args.output) if args.output else default_output_path(args.date)
    download(
        date_str=args.date,
        out=out,
        parts=args.parts,
        max_retries=args.max_retries,
        timeout_sec=args.timeout_sec,
    )


if __name__ == "__main__":
    main()
