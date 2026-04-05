from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000.0
NM_TO_M = 1852.0


def nm_to_m(value: float) -> float:
    return value * NM_TO_M


def m_to_nm(value: float) -> float:
    return value / NM_TO_M


def m2_to_nm2(value: float) -> float:
    return value / (NM_TO_M * NM_TO_M)


def normalize_deg(angle: float) -> float:
    return angle % 360.0


def signed_angle_diff_deg(target_deg: float, reference_deg: float) -> float:
    diff = (target_deg - reference_deg + 180.0) % 360.0 - 180.0
    return diff


def absolute_course_difference_deg(a_deg: float, b_deg: float) -> float:
    return abs(signed_angle_diff_deg(a_deg, b_deg))


def latlon_to_local_xy_m(ref_lat: float, ref_lon: float, lat: float, lon: float) -> tuple[float, float]:
    ref_lat_rad = math.radians(ref_lat)
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    ref_lon_rad = math.radians(ref_lon)
    x_m = (lon_rad - ref_lon_rad) * math.cos((lat_rad + ref_lat_rad) / 2.0) * EARTH_RADIUS_M
    y_m = (lat_rad - ref_lat_rad) * EARTH_RADIUS_M
    return x_m, y_m


def local_xy_to_latlon(ref_lat: float, ref_lon: float, x_m: float, y_m: float) -> tuple[float, float]:
    ref_lat_rad = math.radians(ref_lat)
    ref_lon_rad = math.radians(ref_lon)
    lat_rad = ref_lat_rad + (y_m / EARTH_RADIUS_M)
    mean_lat = (lat_rad + ref_lat_rad) / 2.0
    lon_rad = ref_lon_rad + (x_m / (EARTH_RADIUS_M * math.cos(mean_lat)))
    return math.degrees(lat_rad), math.degrees(lon_rad)


def vector_norm(x: float, y: float) -> float:
    return math.hypot(x, y)


def bearing_from_vector_deg(x_m: float, y_m: float) -> float:
    return normalize_deg(math.degrees(math.atan2(x_m, y_m)))


def relative_bearing_deg(own_heading_deg: float, dx_m: float, dy_m: float) -> float:
    target_bearing = bearing_from_vector_deg(dx_m, dy_m)
    return signed_angle_diff_deg(target_bearing, own_heading_deg)


def velocity_vector_ms(speed_knots: float, cog_deg: float) -> tuple[float, float]:
    speed_ms = nm_to_m(speed_knots) / 3600.0
    course_rad = math.radians(cog_deg)
    vx = speed_ms * math.sin(course_rad)
    vy = speed_ms * math.cos(course_rad)
    return vx, vy
