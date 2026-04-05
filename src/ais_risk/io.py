from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import SnapshotInput, SnapshotResult, VesselState


def _parse_vessel(raw: dict[str, object]) -> VesselState:
    return VesselState(
        mmsi=str(raw["mmsi"]),
        lat=float(raw["lat"]),
        lon=float(raw["lon"]),
        sog=float(raw["sog"]),
        cog=float(raw["cog"]),
        heading=float(raw["heading"]) if raw.get("heading") is not None else None,
        vessel_type=str(raw["vessel_type"]) if raw.get("vessel_type") is not None else None,
    )


def load_snapshot(path: str | Path) -> SnapshotInput:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return SnapshotInput(
        timestamp=str(raw["timestamp"]),
        own_ship=_parse_vessel(raw["own_ship"]),
        targets=tuple(_parse_vessel(item) for item in raw["targets"]),
    )


def save_result(path: str | Path, result: SnapshotResult) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")


def save_snapshot(path: str | Path, snapshot: SnapshotInput) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(asdict(snapshot), indent=2), encoding="utf-8")
