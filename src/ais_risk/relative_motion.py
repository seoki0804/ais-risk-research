from __future__ import annotations

from .geo import (
    absolute_course_difference_deg,
    latlon_to_local_xy_m,
    m_to_nm,
    relative_bearing_deg,
    velocity_vector_ms,
    vector_norm,
)
from .models import RelativeKinematics, VesselState


def classify_encounter(own: VesselState, target: VesselState, beta_deg: float, course_diff_deg: float, tcpa_min: float) -> str:
    if tcpa_min <= 0:
        return "diverging"
    if abs(beta_deg) <= 15.0 and course_diff_deg >= 150.0:
        return "head_on"
    if abs(beta_deg) > 112.5 and target.sog > own.sog and course_diff_deg <= 45.0:
        return "overtaking"
    if abs(beta_deg) <= 112.5:
        return "crossing"
    return "diverging"


def compute_relative_kinematics(own: VesselState, target: VesselState) -> RelativeKinematics:
    dx_m, dy_m = latlon_to_local_xy_m(own.lat, own.lon, target.lat, target.lon)
    distance_nm = m_to_nm(vector_norm(dx_m, dy_m))
    beta_deg = relative_bearing_deg(own.heading_or_cog, dx_m, dy_m)

    own_vx, own_vy = velocity_vector_ms(own.sog, own.cog)
    target_vx, target_vy = velocity_vector_ms(target.sog, target.cog)
    rel_vx = target_vx - own_vx
    rel_vy = target_vy - own_vy
    rel_speed_ms = vector_norm(rel_vx, rel_vy)
    rel_speed_knots = rel_speed_ms * 3600.0 / 1852.0

    rel_speed_sq = rel_vx * rel_vx + rel_vy * rel_vy
    if rel_speed_sq < 1e-9:
        raw_tcpa_sec = 0.0
        closest_x = dx_m
        closest_y = dy_m
    else:
        raw_tcpa_sec = -((dx_m * rel_vx) + (dy_m * rel_vy)) / rel_speed_sq
        closest_t = max(0.0, raw_tcpa_sec)
        closest_x = dx_m + rel_vx * closest_t
        closest_y = dy_m + rel_vy * closest_t

    tcpa_min = raw_tcpa_sec / 60.0
    dcpa_nm = m_to_nm(vector_norm(closest_x, closest_y))
    course_diff_deg = absolute_course_difference_deg(target.cog, own.cog)
    encounter_type = classify_encounter(own, target, beta_deg, course_diff_deg, tcpa_min)

    return RelativeKinematics(
        dx_m=dx_m,
        dy_m=dy_m,
        distance_nm=distance_nm,
        relative_bearing_deg=beta_deg,
        relative_speed_knots=rel_speed_knots,
        tcpa_min=tcpa_min,
        dcpa_nm=dcpa_nm,
        course_difference_deg=course_diff_deg,
        encounter_type=encounter_type,
    )
