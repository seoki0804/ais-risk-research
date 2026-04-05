from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
import time
import zipfile


def parse_date(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def iter_date_range(start_date_text: str, end_date_text: str) -> list[str]:
    start_date = parse_date(start_date_text)
    end_date = parse_date(end_date_text)
    if end_date < start_date:
        raise ValueError("end-date must be greater than or equal to start-date")
    days: list[str] = []
    current = start_date
    while current <= end_date:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def build_noaa_zip_url(
    day_text: str,
    base_url: str = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler",
    year_dir_template: str = "{year}",
    filename_template: str = "AIS_{year}_{month}_{day}.zip",
) -> str:
    day = parse_date(day_text)
    year = f"{day.year:04d}"
    month = f"{day.month:02d}"
    month_compact = f"{day.month:02d}"
    day_of_month = f"{day.day:02d}"
    day_compact = f"{day.day:02d}"
    date_compact = day.strftime("%Y%m%d")
    date_dash = day.strftime("%Y-%m-%d")
    year_dir = year_dir_template.format(
        year=year,
        month=month,
        day=day_of_month,
        month_compact=month_compact,
        day_compact=day_compact,
        date=date_compact,
        date_dash=date_dash,
    )
    filename = filename_template.format(
        year=year,
        month=month,
        day=day_of_month,
        month_compact=month_compact,
        day_compact=day_compact,
        date=date_compact,
        date_dash=date_dash,
    )
    return f"{base_url.rstrip('/')}/{year_dir.strip('/')}/{filename}"


def _download_url_to_file(url: str, destination: Path, timeout_sec: int = 90, max_attempts: int = 3) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AISRiskBot/1.0; +https://github.com/openai/codex)",
            "Accept": "*/*",
        },
    )
    attempts = max(1, int(max_attempts))
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout_sec) as response:  # nosec B310 (user-controlled URL by intent)
                total_bytes = 0
                chunk_size = 1024 * 1024
                with destination.open("wb") as handle:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        handle.write(chunk)
                        total_bytes += len(chunk)
            return total_bytes
        except Exception as exc:
            last_error = exc
            if destination.exists():
                destination.unlink(missing_ok=True)
            if attempt + 1 >= attempts:
                break
            time.sleep(1.5 * (2**attempt))
    raise RuntimeError(f"download failed after {attempts} attempts: {last_error!r}")


def _extract_zip(zip_path: Path, output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[str] = []
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.namelist():
            archive.extract(member, output_dir)
            extracted.append(str(output_dir / member))
    return extracted


def fetch_noaa_archives(
    start_date: str,
    end_date: str,
    output_dir: str | Path,
    base_url: str = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler",
    fallback_base_urls: list[str] | None = None,
    year_dir_template: str = "{year}",
    filename_template: str = "AIS_{year}_{month}_{day}.zip",
    extract: bool = False,
    dry_run: bool = False,
    skip_existing: bool = True,
    timeout_sec: int = 90,
    max_attempts: int = 3,
) -> dict[str, Any]:
    destination_root = Path(output_dir)
    destination_root.mkdir(parents=True, exist_ok=True)
    day_list = iter_date_range(start_date, end_date)

    downloaded_files: list[str] = []
    extracted_files: list[str] = []
    skipped_files: list[str] = []
    failures: list[dict[str, str]] = []
    planned_urls: list[str] = []
    attempted_urls: list[dict[str, Any]] = []
    total_bytes = 0

    fallback_urls = [url for url in (fallback_base_urls or []) if url]

    for day_text in day_list:
        primary_url = build_noaa_zip_url(
            day_text,
            base_url=base_url,
            year_dir_template=year_dir_template,
            filename_template=filename_template,
        )
        candidate_urls = [primary_url]
        for fallback_base in fallback_urls:
            fallback_url = build_noaa_zip_url(
                day_text,
                base_url=fallback_base,
                year_dir_template=year_dir_template,
                filename_template=filename_template,
            )
            if fallback_url not in candidate_urls:
                candidate_urls.append(fallback_url)
        planned_urls.append(primary_url)
        attempted_urls.append({"date": day_text, "candidate_urls": candidate_urls})

        day = parse_date(day_text)
        zip_name = filename_template.format(
            year=f"{day.year:04d}",
            month=f"{day.month:02d}",
            day=f"{day.day:02d}",
            month_compact=f"{day.month:02d}",
            day_compact=f"{day.day:02d}",
            date=day.strftime("%Y%m%d"),
            date_dash=day.strftime("%Y-%m-%d"),
        )
        zip_path = destination_root / zip_name

        if dry_run:
            continue

        used_url = primary_url
        if skip_existing and zip_path.exists():
            skipped_files.append(str(zip_path))
        else:
            downloaded = False
            last_error: Exception | None = None
            for candidate_url in candidate_urls:
                used_url = candidate_url
                try:
                    bytes_count = _download_url_to_file(
                        candidate_url,
                        zip_path,
                        timeout_sec=int(timeout_sec),
                        max_attempts=max(1, int(max_attempts)),
                    )
                    total_bytes += bytes_count
                    downloaded_files.append(str(zip_path))
                    downloaded = True
                    break
                except Exception as exc:  # pragma: no cover - network-dependent branch
                    last_error = exc
            if not downloaded:
                failures.append(
                    {
                        "date": day_text,
                        "url": primary_url,
                        "attempted_urls": ",".join(candidate_urls),
                        "error": repr(last_error),
                    }
                )
                continue

        if extract and zip_path.exists():
            try:
                extracted_files.extend(_extract_zip(zip_path, destination_root / day_text))
            except Exception as exc:  # pragma: no cover - zip content dependent
                failures.append({"date": day_text, "url": used_url, "error": f"extract failed: {exc!r}"})

    return {
        "status": "dry_run" if dry_run else "completed",
        "start_date": start_date,
        "end_date": end_date,
        "output_dir": str(destination_root),
        "base_url": base_url,
        "fallback_base_urls": fallback_urls,
        "year_dir_template": year_dir_template,
        "filename_template": filename_template,
        "timeout_sec": int(timeout_sec),
        "max_attempts": max(1, int(max_attempts)),
        "planned_count": len(day_list),
        "planned_urls": planned_urls,
        "attempted_urls": attempted_urls,
        "downloaded_count": len(downloaded_files),
        "downloaded_files": downloaded_files,
        "skipped_count": len(skipped_files),
        "skipped_files": skipped_files,
        "extracted_count": len(extracted_files),
        "extracted_files": extracted_files,
        "failed_count": len(failures),
        "failures": failures,
        "total_bytes": total_bytes,
    }
