from __future__ import annotations

import csv
from pathlib import Path

from .config import load_config
from .csv_tools import build_snapshot_from_curated_rows, load_curated_csv_rows
from .models import ProjectConfig
from .pipeline import run_snapshot


def mine_cases_from_curated_rows(
    rows: list[dict[str, str]],
    own_mmsi: str,
    config: ProjectConfig,
    radius_nm: float,
    top_n: int = 10,
    max_age_minutes: float = 5.0,
    min_targets: int = 1,
) -> list[dict[str, str]]:
    candidate_times = sorted({row["timestamp"] for row in rows if row["mmsi"] == own_mmsi})
    cases: list[dict[str, str]] = []
    for timestamp in candidate_times:
        snapshot = build_snapshot_from_curated_rows(
            rows=rows,
            own_mmsi=own_mmsi,
            timestamp=timestamp,
            radius_nm=radius_nm,
            max_age_minutes=max_age_minutes,
        )
        if len(snapshot.targets) < min_targets:
            continue
        result = run_snapshot(snapshot, config)
        current = next((scenario for scenario in result.scenarios if scenario.summary.scenario_name == "current"), result.scenarios[0])
        top_vessel = current.top_vessels[0] if current.top_vessels else None
        cases.append(
            {
                "timestamp": result.timestamp,
                "target_count": str(current.summary.target_count),
                "max_risk": f"{current.summary.max_risk:.6f}",
                "mean_risk": f"{current.summary.mean_risk:.6f}",
                "warning_area_nm2": f"{current.summary.warning_area_nm2:.6f}",
                "caution_area_nm2": f"{current.summary.caution_area_nm2:.6f}",
                "dominant_sector": current.summary.dominant_sector,
                "top_vessel_mmsi": "" if top_vessel is None else top_vessel.mmsi,
                "top_vessel_score": "" if top_vessel is None else f"{top_vessel.score:.6f}",
                "top_vessel_encounter": "" if top_vessel is None else top_vessel.encounter_type,
            }
        )

    cases.sort(
        key=lambda item: (
            float(item["max_risk"]),
            float(item["warning_area_nm2"]),
            float(item["mean_risk"]),
        ),
        reverse=True,
    )
    return cases[:top_n]


def mine_cases_from_curated_csv(
    input_path: str | Path,
    own_mmsi: str,
    config_path: str | Path,
    radius_nm: float,
    top_n: int = 10,
    max_age_minutes: float = 5.0,
    min_targets: int = 1,
) -> list[dict[str, str]]:
    rows = load_curated_csv_rows(input_path)
    config = load_config(config_path)
    return mine_cases_from_curated_rows(
        rows=rows,
        own_mmsi=own_mmsi,
        config=config,
        radius_nm=radius_nm,
        top_n=top_n,
        max_age_minutes=max_age_minutes,
        min_targets=min_targets,
    )


def save_case_candidates(path: str | Path, rows: list[dict[str, str]]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "timestamp",
        "target_count",
        "max_risk",
        "mean_risk",
        "warning_area_nm2",
        "caution_area_nm2",
        "dominant_sector",
        "top_vessel_mmsi",
        "top_vessel_score",
        "top_vessel_encounter",
    ]
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
