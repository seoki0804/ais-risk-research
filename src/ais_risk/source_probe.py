from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable
from urllib import error, request


PUBLIC_AIS_SOURCES: dict[str, dict[str, str]] = {
    "dma_ais": {
        "name": "Danish Maritime Authority AIS data page",
        "url": "https://www.dma.dk/safety-at-sea/navigational-information/ais-data",
    },
    "dma_conditions": {
        "name": "Danish Maritime Authority AIS data management policy page",
        "url": "https://www.dma.dk/safety-at-sea/navigational-information/ais-data/ais-data-management-policy-",
    },
    "noaa_accessais": {
        "name": "NOAA Digital Coast AccessAIS",
        "url": "https://coast.noaa.gov/digitalcoast/tools/ais.html",
    },
    "korea_data_go_ais": {
        "name": "Korea Public Data Portal AIS dynamic data page",
        "url": "https://www.data.go.kr/data/15129186/fileData.do",
    },
    "aishub_api": {
        "name": "AISHub AIS data API page",
        "url": "https://www.aishub.net/api",
    },
}

DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; ais-risk-source-probe/1.0)"
OpenFunction = Callable[..., Any]


def list_public_source_ids() -> list[str]:
    return sorted(PUBLIC_AIS_SOURCES.keys())


def resolve_public_source_ids(source_ids: list[str] | None = None) -> list[str]:
    if not source_ids:
        return list_public_source_ids()
    resolved: list[str] = []
    for item in source_ids:
        source_id = str(item).strip()
        if not source_id:
            continue
        if source_id not in PUBLIC_AIS_SOURCES:
            raise ValueError(f"Unsupported source id: {source_id}")
        resolved.append(source_id)
    if not resolved:
        raise ValueError("No valid source ids were provided.")
    return resolved


def _availability_from_status(status_code: int | None) -> str:
    if status_code is None:
        return "network_error"
    if 200 <= status_code < 400:
        return "ok"
    if status_code in {401, 403}:
        return "restricted"
    if status_code == 404:
        return "not_found"
    if status_code == 429:
        return "rate_limited"
    if status_code >= 500:
        return "server_error"
    return "http_error"


def _open_request(
    url: str,
    method: str,
    timeout_seconds: float,
    opener: OpenFunction,
    user_agent: str,
) -> dict[str, Any]:
    req = request.Request(url=url, method=method, headers={"User-Agent": user_agent})
    started = time.perf_counter()
    try:
        with opener(req, timeout=float(timeout_seconds)) as response:
            status_code = getattr(response, "status", None)
            if status_code is None:
                status_code = response.getcode()
            final_url = response.geturl()
            return {
                "status_code": int(status_code) if status_code is not None else None,
                "final_url": str(final_url),
                "error": "",
                "latency_seconds": float(time.perf_counter() - started),
            }
    except error.HTTPError as exc:
        status_code = int(exc.code) if exc.code is not None else None
        final_url = str(exc.geturl() or url)
        return {
            "status_code": status_code,
            "final_url": final_url,
            "error": repr(exc),
            "latency_seconds": float(time.perf_counter() - started),
        }
    except Exception as exc:
        return {
            "status_code": None,
            "final_url": str(url),
            "error": repr(exc),
            "latency_seconds": float(time.perf_counter() - started),
        }


def _probe_single_source(
    source_id: str,
    timeout_seconds: float,
    retries: int,
    opener: OpenFunction,
    user_agent: str,
) -> dict[str, Any]:
    source = PUBLIC_AIS_SOURCES[source_id]
    url = source["url"]

    attempts = 0
    last_result: dict[str, Any] = {
        "status_code": None,
        "final_url": url,
        "error": "unreachable",
        "latency_seconds": 0.0,
    }
    method_used = "HEAD"

    for attempt in range(max(1, int(retries) + 1)):
        attempts += 1
        head_result = _open_request(
            url=url,
            method="HEAD",
            timeout_seconds=timeout_seconds,
            opener=opener,
            user_agent=user_agent,
        )
        status_code = head_result.get("status_code")
        if status_code == 405:
            method_used = "GET"
            get_result = _open_request(
                url=url,
                method="GET",
                timeout_seconds=timeout_seconds,
                opener=opener,
                user_agent=user_agent,
            )
            last_result = get_result
            if get_result.get("status_code") is not None:
                break
        else:
            method_used = "HEAD"
            last_result = head_result
            if status_code is not None:
                break

        if attempt < int(retries):
            time.sleep(0.2 * (attempt + 1))

    status_code = last_result.get("status_code")
    availability = _availability_from_status(status_code)
    return {
        "source_id": source_id,
        "source_name": source["name"],
        "url": url,
        "final_url": str(last_result.get("final_url") or url),
        "http_status": status_code,
        "availability": availability,
        "reachable": bool(status_code is not None),
        "method": method_used,
        "attempts": attempts,
        "latency_seconds": float(last_result.get("latency_seconds") or 0.0),
        "error": str(last_result.get("error") or ""),
    }


def build_source_probe_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Public AIS Source Connectivity Probe",
        "",
        "## Inputs",
        "",
        f"- source_ids: `{', '.join(summary.get('source_ids', []))}`",
        f"- timeout_seconds: `{summary.get('timeout_seconds')}`",
        f"- retries: `{summary.get('retries')}`",
        "",
        "## Results",
        "",
        f"- row_count: `{summary.get('row_count')}`",
        f"- ok_count: `{summary.get('ok_count')}`",
        f"- restricted_count: `{summary.get('restricted_count')}`",
        f"- failed_count: `{summary.get('failed_count')}`",
        "",
        "| Source ID | HTTP Status | Availability | Method | Attempts | Latency (sec) | URL |",
        "|---|---:|---|---|---:|---:|---|",
    ]
    for row in summary.get("rows", []):
        lines.append(
            "| `{source_id}` | {status} | {availability} | {method} | {attempts} | {latency} | `{url}` |".format(
                source_id=row.get("source_id", "n/a"),
                status=row.get("http_status", "n/a"),
                availability=row.get("availability", "n/a"),
                method=row.get("method", "n/a"),
                attempts=row.get("attempts", 0),
                latency=f"{float(row.get('latency_seconds', 0.0)):.3f}",
                url=row.get("url", "n/a"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def run_public_source_probe(
    output_prefix: str | Path,
    source_ids: list[str] | None = None,
    timeout_seconds: float = 8.0,
    retries: int = 1,
    user_agent: str = DEFAULT_USER_AGENT,
    opener: OpenFunction | None = None,
) -> dict[str, Any]:
    selected_source_ids = resolve_public_source_ids(source_ids)
    open_fn = opener or request.urlopen
    rows = [
        _probe_single_source(
            source_id=source_id,
            timeout_seconds=float(timeout_seconds),
            retries=int(retries),
            opener=open_fn,
            user_agent=user_agent,
        )
        for source_id in selected_source_ids
    ]
    ok_count = sum(1 for row in rows if row.get("availability") == "ok")
    restricted_count = sum(1 for row in rows if row.get("availability") == "restricted")
    failed_count = sum(1 for row in rows if row.get("availability") not in {"ok", "restricted"})

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    summary: dict[str, Any] = {
        "status": "completed",
        "source_ids": selected_source_ids,
        "timeout_seconds": float(timeout_seconds),
        "retries": int(retries),
        "row_count": len(rows),
        "ok_count": ok_count,
        "restricted_count": restricted_count,
        "failed_count": failed_count,
        "rows": rows,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_source_probe_summary_markdown(summary), encoding="utf-8")
    return summary
