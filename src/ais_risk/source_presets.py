from __future__ import annotations

from dataclasses import dataclass

from .csv_tools import parse_column_overrides


@dataclass(frozen=True)
class SourcePreset:
    name: str
    description: str
    column_map_text: str


SOURCE_PRESETS: dict[str, SourcePreset] = {
    "auto": SourcePreset(
        name="auto",
        description="Alias-based auto detection only. Use this when the raw CSV is already close to common AIS headers.",
        column_map_text="",
    ),
    "marinecadastre_like": SourcePreset(
        name="marinecadastre_like",
        description="Typical MMSI/BaseDateTime/LAT/LON/SOG/COG/Heading/VesselType layout.",
        column_map_text="mmsi=MMSI,timestamp=BaseDateTime,lat=LAT,lon=LON,sog=SOG,cog=COG,heading=Heading,vessel_type=VesselType",
    ),
    "noaa_accessais": SourcePreset(
        name="noaa_accessais",
        description="NOAA AccessAIS exports compatible with MMSI/BaseDateTime/LAT/LON/SOG/COG/Heading/VesselType columns.",
        column_map_text="mmsi=MMSI,timestamp=BaseDateTime,lat=LAT,lon=LON,sog=SOG,cog=COG,heading=Heading,vessel_type=VesselType",
    ),
    "shipid_eventtime_xy": SourcePreset(
        name="shipid_eventtime_xy",
        description="Custom flat export with ShipId/Event Time/Y/X/Speed/Course columns.",
        column_map_text="mmsi=ShipId,timestamp=Event Time,lat=Y,lon=X,sog=Speed,cog=Course,heading=Heading,vessel_type=ShipCategory",
    ),
    "verbose_over_ground": SourcePreset(
        name="verbose_over_ground",
        description="Verbose headers such as Ship MMSI, Base Date Time, Speed Over Ground, Course Over Ground.",
        column_map_text="mmsi=Ship MMSI,timestamp=Base Date Time,lat=LATITUDE,lon=LONGITUDE,sog=Speed Over Ground,cog=Course Over Ground,heading=True Heading,vessel_type=Ship Type",
    ),
}


def list_source_preset_names() -> list[str]:
    return list(SOURCE_PRESETS.keys())


def get_source_preset(name: str | None) -> SourcePreset:
    preset_name = "auto" if name is None or name.strip() == "" else name.strip()
    if preset_name not in SOURCE_PRESETS:
        raise ValueError(f"Unsupported source preset: {preset_name}")
    return SOURCE_PRESETS[preset_name]


def resolve_source_preset(name: str | None, manual_override_text: str | None = None) -> dict[str, str]:
    preset = get_source_preset(name)
    preset_overrides = parse_column_overrides(preset.column_map_text)
    manual_overrides = parse_column_overrides(manual_override_text)
    return {
        **preset_overrides,
        **manual_overrides,
    }
