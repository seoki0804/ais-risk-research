from __future__ import annotations

from dataclasses import replace

from .models import VesselState


def apply_speed_multiplier(vessel: VesselState, multiplier: float) -> VesselState:
    return replace(vessel, sog=max(0.0, vessel.sog * multiplier))
