from __future__ import annotations

from collections.abc import Iterable

from .models import GridCellRisk


def _infer_step_from_cells(cells: list[GridCellRisk]) -> float:
    xs = sorted({cell.x_m for cell in cells})
    if len(xs) < 2:
        return 0.0
    diffs = [right - left for left, right in zip(xs, xs[1:], strict=False) if right > left]
    return min(diffs) if diffs else 0.0


def extract_threshold_segments(
    cells: Iterable[GridCellRisk],
    threshold: float,
    cell_size_m: float,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    cell_list = list(cells)
    step = _infer_step_from_cells(cell_list)
    if step <= 0.0:
        return []

    lookup = {(cell.x_m, cell.y_m): cell.risk for cell in cell_list}
    half = cell_size_m / 2.0
    directions = {
        "left": (-step, 0.0),
        "right": (step, 0.0),
        "down": (0.0, -step),
        "up": (0.0, step),
    }

    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for (x_m, y_m), risk in lookup.items():
        if risk < threshold:
            continue
        for side, (dx, dy) in directions.items():
            neighbor_risk = lookup.get((x_m + dx, y_m + dy), -1.0)
            if neighbor_risk >= threshold:
                continue
            if side == "left":
                start = (x_m - half, y_m - half)
                end = (x_m - half, y_m + half)
            elif side == "right":
                start = (x_m + half, y_m - half)
                end = (x_m + half, y_m + half)
            elif side == "up":
                start = (x_m - half, y_m + half)
                end = (x_m + half, y_m + half)
            else:
                start = (x_m - half, y_m - half)
                end = (x_m + half, y_m - half)
            segments.append((start, end))
    return segments
