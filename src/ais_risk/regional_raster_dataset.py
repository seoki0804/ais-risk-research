from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RasterConfig:
    half_width_nm: float = 3.0
    raster_size: int = 64
    occupancy_clip: float = 4.0
    speed_clip: float = 20.0


@dataclass
class RasterSample:
    image: np.ndarray
    scalar_features: np.ndarray
    label: int
    metadata: dict[str, str]


def scene_key(row: dict[str, str]) -> tuple[str, str]:
    return str(row.get("timestamp", "")), str(row.get("own_mmsi", ""))


def rows_by_scene(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(scene_key(row), []).append(row)
    return grouped


def local_xy_nm_from_row(row: dict[str, str]) -> tuple[float, float]:
    distance_nm = float(row.get("distance_nm", 0.0) or 0.0)
    bearing_deg = float(row.get("relative_bearing_deg", 0.0) or 0.0)
    theta = math.radians(bearing_deg)
    x_nm = distance_nm * math.cos(theta)
    y_nm = distance_nm * math.sin(theta)
    return x_nm, y_nm


def grid_indices_from_xy(x_nm: float, y_nm: float, config: RasterConfig) -> tuple[int, int] | None:
    half_width = float(config.half_width_nm)
    if not (-half_width <= x_nm <= half_width and -half_width <= y_nm <= half_width):
        return None
    cell_width = (2.0 * half_width) / float(config.raster_size)
    col = int((x_nm + half_width) / cell_width)
    row = int((half_width - y_nm) / cell_width)
    col = min(max(col, 0), config.raster_size - 1)
    row = min(max(row, 0), config.raster_size - 1)
    return row, col


def build_scene_base_channels(scene_rows: list[dict[str, str]], config: RasterConfig) -> tuple[np.ndarray, dict[str, tuple[int, int]]]:
    raster = np.zeros((3, config.raster_size, config.raster_size), dtype=np.float32)
    focal_lookup: dict[str, tuple[int, int]] = {}
    for row in scene_rows:
        xy = local_xy_nm_from_row(row)
        indices = grid_indices_from_xy(xy[0], xy[1], config)
        if indices is None:
            continue
        r, c = indices
        focal_lookup[str(row.get("target_mmsi", ""))] = (r, c)
        raster[0, r, c] = min(float(config.occupancy_clip), raster[0, r, c] + 1.0)
        raster[1, r, c] = max(raster[1, r, c], float(row.get("rule_score", 0.0) or 0.0))
        speed_value = float(row.get("relative_speed_knots", 0.0) or 0.0)
        tcpa_value = float(row.get("tcpa_min", 0.0) or 0.0)
        signed_speed = speed_value if tcpa_value >= 0.0 else -speed_value
        raster[2, r, c] += float(np.clip(signed_speed / float(config.speed_clip), -1.0, 1.0))
    raster[0] = np.clip(raster[0] / float(config.occupancy_clip), 0.0, 1.0)
    raster[2] = np.clip(raster[2], -1.0, 1.0)
    return raster, focal_lookup


def rasterize_scene_for_target(
    scene_rows: list[dict[str, str]],
    focal_row: dict[str, str],
    config: RasterConfig,
) -> np.ndarray:
    base_channels, focal_lookup = build_scene_base_channels(scene_rows, config)
    raster = np.zeros((5, config.raster_size, config.raster_size), dtype=np.float32)
    raster[:3] = base_channels
    target_mmsi = str(focal_row.get("target_mmsi", ""))
    indices = focal_lookup.get(target_mmsi)
    if indices is not None:
        r, c = indices
        raster[3, r, c] = 1.0
        raster[4, r, c] = float(focal_row.get("rule_score", 0.0) or 0.0)
    return raster


def build_raster_samples(rows: list[dict[str, str]], config: RasterConfig) -> list[RasterSample]:
    scenes = rows_by_scene(rows)
    samples: list[RasterSample] = []
    for row in rows:
        scene_rows = scenes[scene_key(row)]
        raster = rasterize_scene_for_target(scene_rows, row, config)
        scalar_features = np.array(
            [
                float(row.get("distance_nm", 0.0) or 0.0) / max(float(config.half_width_nm), 1e-6),
                float(row.get("dcpa_nm", 0.0) or 0.0) / max(float(config.half_width_nm), 1e-6),
                float(row.get("tcpa_min", 0.0) or 0.0) / 30.0,
                float(row.get("relative_speed_knots", 0.0) or 0.0) / float(config.speed_clip),
                float(row.get("rule_score", 0.0) or 0.0),
            ],
            dtype=np.float32,
        )
        samples.append(
            RasterSample(
                image=raster,
                scalar_features=np.clip(scalar_features, -2.0, 2.0),
                label=int(row.get("label_future_conflict", 0) or 0),
                metadata={
                    "timestamp": str(row.get("timestamp", "")),
                    "own_mmsi": str(row.get("own_mmsi", "")),
                    "target_mmsi": str(row.get("target_mmsi", "")),
                    "label_future_conflict": str(row.get("label_future_conflict", "")),
                },
            )
        )
    return samples


def stack_raster_samples(samples: list[RasterSample]) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, str]]]:
    if not samples:
        raise ValueError("At least one raster sample is required.")
    images = np.stack([sample.image for sample in samples], axis=0).astype(np.float32)
    scalar_features = np.stack([sample.scalar_features for sample in samples], axis=0).astype(np.float32)
    labels = np.array([sample.label for sample in samples], dtype=np.int64)
    metadata = [sample.metadata for sample in samples]
    return images, scalar_features, labels, metadata


def truncate_rows(rows: list[dict[str, str]], max_rows: int | None) -> list[dict[str, str]]:
    if max_rows is None or max_rows <= 0 or len(rows) <= max_rows:
        return rows
    return rows[: int(max_rows)]


def summarize_raster_tensor(images: np.ndarray) -> dict[str, Any]:
    return {
        "num_samples": int(images.shape[0]),
        "channels": int(images.shape[1]),
        "height": int(images.shape[2]),
        "width": int(images.shape[3]),
        "mean_activation": float(np.mean(images)),
        "nonzero_fraction": float(np.mean(images != 0.0)),
    }
