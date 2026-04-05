from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import load_config
from .csv_tools import preprocess_ais_csv
from .pairwise_dataset import build_pairwise_learning_dataset_from_csv
from .source_presets import resolve_source_preset
from .trajectory import reconstruct_trajectory_csv


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def build_noaa_focus_pairwise_bundle_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# NOAA Focus Pairwise Bundle Summary",
        "",
        f"- raw_input: `{summary.get('raw_input_path', '')}`",
        f"- source_preset: `{summary.get('source_preset', '')}`",
        f"- vessel_types: `{', '.join(summary.get('vessel_types', []))}`",
        f"- run_count: `{summary.get('run_count', 0)}`",
        "",
        "| label | focus_rows | unique_vessels | track_rows | pairwise_rows | positive_rate | own_mmsis |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("runs", []):
        lines.append(
            "| {label} | {focus_rows} | {vessels} | {track_rows} | {pairwise_rows} | {positive_rate} | {own_mmsis} |".format(
                label=row.get("label", ""),
                focus_rows=row.get("focus_output_rows", 0),
                vessels=row.get("focus_unique_vessels", 0),
                track_rows=row.get("trajectory_output_rows", 0),
                pairwise_rows=row.get("pairwise_row_count", 0),
                positive_rate=_fmt(row.get("pairwise_positive_rate")),
                own_mmsis=",".join(row.get("own_mmsis", [])),
            )
        )
    lines.append("")
    return "\n".join(lines)


def run_noaa_focus_pairwise_bundle(
    raw_input_path: str | Path,
    output_prefix: str | Path,
    region_specs: list[dict[str, Any]],
    config_path: str | Path = "configs/base.toml",
    focus_output_dir: str | Path | None = None,
    source_preset: str = "noaa_accessais",
    vessel_types: list[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    time_label: str = "0000_2359",
    split_gap_minutes: float = 10.0,
    max_interp_gap_minutes: float = 2.0,
    step_seconds: int = 30,
    pairwise_label_distance_nm: float = 1.6,
    pairwise_sample_every: int = 5,
    pairwise_min_future_points: int = 2,
    pairwise_min_targets: int = 1,
    pairwise_max_timestamps_per_ship: int | None = 120,
) -> dict[str, Any]:
    if not region_specs:
        raise ValueError("region_specs must not be empty.")

    default_vessel_types = ["cargo", "tanker", "passenger", "tug", "service"]
    selected_vessel_types = [str(item).strip().lower() for item in (vessel_types or default_vessel_types) if str(item).strip()]
    config = load_config(Path(config_path))
    column_overrides = resolve_source_preset(name=source_preset, manual_override_text=None)

    raw_input = Path(raw_input_path)
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    bundle_dir = prefix.parent / prefix.name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    focus_dir = Path(focus_output_dir) if focus_output_dir else raw_input.parent
    focus_dir.mkdir(parents=True, exist_ok=True)

    run_rows: list[dict[str, Any]] = []
    for spec in region_specs:
        label = str(spec.get("label") or "").strip()
        if not label:
            raise ValueError("Each region spec requires 'label'.")
        own_mmsis = [str(item).strip() for item in (spec.get("own_mmsis") or []) if str(item).strip()]
        if not own_mmsis:
            raise ValueError(f"Region spec '{label}' has empty own_mmsis.")

        min_lat = float(spec["min_lat"])
        max_lat = float(spec["max_lat"])
        min_lon = float(spec["min_lon"])
        max_lon = float(spec["max_lon"])

        focus_csv = focus_dir / f"raw_focus_{label}_{time_label}.csv"
        tracks_csv = bundle_dir / f"{label}_tracks.csv"
        pairwise_csv = bundle_dir / f"{label}_pairwise_dataset.csv"
        pairwise_stats_json = bundle_dir / f"{label}_pairwise_dataset_stats.json"

        focus_stats = preprocess_ais_csv(
            input_path=raw_input,
            output_path=focus_csv,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            start_time=start_time,
            end_time=end_time,
            allowed_vessel_types=set(selected_vessel_types),
            column_overrides=column_overrides,
        )
        trajectory_stats = reconstruct_trajectory_csv(
            input_path=focus_csv,
            output_path=tracks_csv,
            split_gap_minutes=float(split_gap_minutes),
            max_interp_gap_minutes=float(max_interp_gap_minutes),
            step_seconds=int(step_seconds),
        )
        pairwise_payload = build_pairwise_learning_dataset_from_csv(
            input_path=tracks_csv,
            output_path=pairwise_csv,
            config=config,
            own_mmsis=set(own_mmsis),
            label_distance_nm=float(pairwise_label_distance_nm),
            sample_every_nth_timestamp=max(1, int(pairwise_sample_every)),
            min_future_points=max(1, int(pairwise_min_future_points)),
            min_targets=max(1, int(pairwise_min_targets)),
            max_timestamps_per_ship=pairwise_max_timestamps_per_ship,
            stats_output_path=pairwise_stats_json,
        )

        run_rows.append(
            {
                "label": label,
                "bbox": {
                    "min_lat": min_lat,
                    "max_lat": max_lat,
                    "min_lon": min_lon,
                    "max_lon": max_lon,
                },
                "own_mmsis": own_mmsis,
                "focus_csv_path": str(focus_csv),
                "focus_output_rows": int(focus_stats.get("output_rows", 0)),
                "focus_unique_vessels": int(focus_stats.get("unique_vessels", 0)),
                "focus_stats": focus_stats,
                "tracks_csv_path": str(tracks_csv),
                "trajectory_output_rows": int(trajectory_stats.get("output_rows", 0)),
                "trajectory_stats": trajectory_stats,
                "pairwise_csv_path": str(pairwise_csv),
                "pairwise_stats_json_path": str(pairwise_stats_json),
                "pairwise_row_count": int(pairwise_payload.get("row_count", 0)),
                "pairwise_positive_rate": _safe_float(pairwise_payload.get("positive_rate")),
            }
        )

    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    summary: dict[str, Any] = {
        "status": "completed",
        "raw_input_path": str(raw_input),
        "config_path": str(config_path),
        "source_preset": source_preset,
        "vessel_types": selected_vessel_types,
        "start_time": start_time,
        "end_time": end_time,
        "time_label": time_label,
        "run_count": len(run_rows),
        "runs": run_rows,
        "bundle_dir": str(bundle_dir),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_noaa_focus_pairwise_bundle_markdown(summary), encoding="utf-8")
    return summary
