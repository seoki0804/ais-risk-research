from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .source_presets import get_source_preset
from .vessel_types import normalize_vessel_type


@dataclass(frozen=True)
class IngestionPresetBundle:
    name: str
    description: str
    source_preset: str
    vessel_types: tuple[str, ...]
    column_map_text: str = ""
    notes: tuple[str, ...] = ()


INGESTION_BUNDLES: dict[str, IngestionPresetBundle] = {
    "generic_harbor": IngestionPresetBundle(
        name="generic_harbor",
        description="General mixed-harbor ingestion starting point with alias auto detection and common commercial/service vessel filters.",
        source_preset="auto",
        vessel_types=("cargo", "tanker", "passenger", "tug", "service"),
        notes=(
            "Use this when the raw CSV header layout is unknown but the target sea area is a mixed harbor approach.",
            "If auto detection misses required headers, switch source preset or add manual column overrides.",
        ),
    ),
    "marinecadastre_harbor": IngestionPresetBundle(
        name="marinecadastre_harbor",
        description="MarineCadastre-like MMSI/BaseDateTime/LAT/LON/SOG/COG layout for harbor traffic screening.",
        source_preset="marinecadastre_like",
        vessel_types=("cargo", "tanker", "passenger", "tug", "service"),
        notes=(
            "Good default for typical US AIS exports with BaseDateTime, LAT, LON, SOG, COG, Heading, VesselType.",
            "Keep service and tug types when analyzing constrained harbor traffic.",
        ),
    ),
    "shipid_xy_demo": IngestionPresetBundle(
        name="shipid_xy_demo",
        description="Flat custom export with ShipId/Event Time/Y/X/Speed/Course columns, suited to demo and portfolio datasets.",
        source_preset="shipid_eventtime_xy",
        vessel_types=("cargo", "tanker", "passenger"),
        notes=(
            "Use this for simplified CSV exports where coordinate columns are Y/X and field names are not AIS-native.",
            "Add manual overrides only if heading or vessel type columns use different names.",
        ),
    ),
    "verbose_port_mix": IngestionPresetBundle(
        name="verbose_port_mix",
        description="Verbose-over-ground export with long-form headers and mixed port traffic filters.",
        source_preset="verbose_over_ground",
        vessel_types=("cargo", "tanker", "passenger", "service", "tug"),
        notes=(
            "Designed for exports using labels like Speed Over Ground and Course Over Ground.",
            "Useful when source files come from BI/reporting systems that expanded header names.",
        ),
    ),
}


def _parse_vessel_types_text(raw: str | None) -> tuple[str, ...]:
    if raw is None or raw.strip() == "":
        return ()
    normalized = []
    for item in raw.split(","):
        value = normalize_vessel_type(item)
        if value and value not in normalized:
            normalized.append(value)
    return tuple(normalized)


def list_ingestion_bundle_names() -> list[str]:
    return list(INGESTION_BUNDLES.keys())


def get_ingestion_bundle(name: str | None) -> IngestionPresetBundle:
    if name is None or name.strip() == "":
        raise ValueError("Ingestion bundle name is required.")
    bundle_name = name.strip()
    if bundle_name not in INGESTION_BUNDLES:
        raise ValueError(f"Unsupported ingestion bundle: {bundle_name}")
    return INGESTION_BUNDLES[bundle_name]


def load_ingestion_bundle_config(path: str | Path) -> IngestionPresetBundle:
    config_path = Path(path)
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    bundle_payload = payload.get("bundle")
    if not isinstance(bundle_payload, dict):
        raise ValueError(f"Invalid ingestion config: missing [bundle] table in {config_path}")

    defaults_payload = bundle_payload.get("defaults")
    if defaults_payload is None:
        defaults_payload = {}
    if not isinstance(defaults_payload, dict):
        raise ValueError(f"Invalid ingestion config: [bundle.defaults] must be a table in {config_path}")

    notes_payload = bundle_payload.get("notes")
    if notes_payload is None:
        notes_payload = {}
    if not isinstance(notes_payload, dict):
        raise ValueError(f"Invalid ingestion config: [bundle.notes] must be a table in {config_path}")

    raw_vessel_types = defaults_payload.get("vessel_types") or ()
    vessel_types: list[str] = []
    for item in raw_vessel_types:
        normalized = normalize_vessel_type(item)
        if normalized and normalized not in vessel_types:
            vessel_types.append(normalized)

    return IngestionPresetBundle(
        name=str(bundle_payload.get("name") or config_path.stem),
        description=str(bundle_payload.get("description") or ""),
        source_preset=str(bundle_payload.get("source_preset") or "auto"),
        vessel_types=tuple(vessel_types),
        column_map_text=str(defaults_payload.get("column_map") or ""),
        notes=tuple(str(item) for item in (notes_payload.get("items") or ())),
    )


def resolve_ingestion_bundle(
    bundle_name: str | None,
    config_path: str | Path | None,
    source_preset_name: str | None,
    manual_column_map_text: str | None,
    vessel_types_text: str | None,
) -> dict[str, object]:
    bundle = None if bundle_name is None or bundle_name.strip() == "" else get_ingestion_bundle(bundle_name)
    if config_path is not None and str(config_path).strip() != "":
        bundle = load_ingestion_bundle_config(config_path)
    source_preset = source_preset_name or "auto"
    if bundle is not None and source_preset == "auto":
        source_preset = bundle.source_preset

    column_map_text = manual_column_map_text.strip() if manual_column_map_text else ""
    if bundle is not None and column_map_text == "":
        column_map_text = bundle.column_map_text

    vessel_types = _parse_vessel_types_text(vessel_types_text)
    if bundle is not None and not vessel_types:
        vessel_types = bundle.vessel_types

    return {
        "bundle_name": None if bundle is None else bundle.name,
        "bundle_description": "" if bundle is None else bundle.description,
        "bundle_config_path": "" if config_path is None else str(config_path),
        "source_preset": source_preset,
        "column_map_text": column_map_text,
        "vessel_types": vessel_types,
        "notes": () if bundle is None else bundle.notes,
    }


def render_ingestion_bundle_toml(bundle: IngestionPresetBundle) -> str:
    note_lines = "\n".join(f'"{item}"' for item in bundle.notes)
    vessel_type_lines = ", ".join(f'"{item}"' for item in bundle.vessel_types)
    preset = get_source_preset(bundle.source_preset)
    return f"""[bundle]
name = "{bundle.name}"
description = "{bundle.description}"
source_preset = "{bundle.source_preset}"

[bundle.defaults]
vessel_types = [{vessel_type_lines}]
column_map = "{bundle.column_map_text}"

[bundle.source_preset_info]
description = "{preset.description}"
default_column_map = "{preset.column_map_text}"

[bundle.notes]
items = [{note_lines}]
"""


def write_ingestion_bundle_template(name: str, output_path: str | Path) -> Path:
    bundle = get_ingestion_bundle(name)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_ingestion_bundle_toml(bundle), encoding="utf-8")
    return destination
