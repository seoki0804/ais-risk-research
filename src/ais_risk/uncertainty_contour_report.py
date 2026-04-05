from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import load_config
from .contours import extract_threshold_segments
from .models import GridCellRisk


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _risk_color(risk: float) -> str:
    if risk <= 0.0:
        return "#eef4f3"
    if risk < 0.35:
        return "#79c9bd"
    if risk < 0.65:
        return "#efb064"
    return "#db5b4e"


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _resolve_case_id(case_rows: list[dict[str, str]], requested_case_id: str | None) -> str:
    if requested_case_id:
        for row in case_rows:
            if str(row.get("case_id", "")) == requested_case_id:
                return requested_case_id
        raise ValueError(f"Requested case_id not found: {requested_case_id}")

    ranked = sorted(
        case_rows,
        key=lambda row: _safe_float(row.get("max_risk_mean")) or 0.0,
        reverse=True,
    )
    if not ranked:
        raise ValueError("Case summary CSV is empty.")
    return str(ranked[0].get("case_id", ""))


def _to_grid_cells(rows: list[dict[str, str]], risk_key: str) -> list[GridCellRisk]:
    cells: list[GridCellRisk] = []
    for row in rows:
        risk_value = _safe_float(row.get(risk_key))
        x_m = _safe_float(row.get("x_m"))
        y_m = _safe_float(row.get("y_m"))
        if None in {risk_value, x_m, y_m}:
            continue
        cells.append(
            GridCellRisk(
                x_m=float(x_m),
                y_m=float(y_m),
                risk=float(risk_value),
                label="",
            )
        )
    return cells


def _render_panel(
    title: str,
    cells: list[GridCellRisk],
    radius_m: float,
    cell_size_m: float,
    safe_threshold: float,
    warning_threshold: float,
    max_risk_text: str,
) -> str:
    width_px = 320
    height_px = 320
    footer_y = 350

    def to_px(x_m: float, y_m: float) -> tuple[float, float]:
        px = ((x_m + radius_m) / (2.0 * radius_m)) * width_px
        py = height_px - (((y_m + radius_m) / (2.0 * radius_m)) * height_px)
        return px, py

    half = cell_size_m / 2.0
    rects: list[str] = []
    for cell in cells:
        if cell.risk < 0.01:
            continue
        x1, y1 = to_px(cell.x_m - half, cell.y_m + half)
        x2, y2 = to_px(cell.x_m + half, cell.y_m - half)
        rects.append(
            f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{max(1.0, x2 - x1):.2f}" height="{max(1.0, y2 - y1):.2f}" '
            f'fill="{_risk_color(cell.risk)}" fill-opacity="{0.08 + (0.92 * min(1.0, cell.risk)):.3f}" stroke="none" />'
        )

    safe_segments = extract_threshold_segments(cells, threshold=safe_threshold, cell_size_m=cell_size_m)
    warning_segments = extract_threshold_segments(cells, threshold=warning_threshold, cell_size_m=cell_size_m)
    safe_lines: list[str] = []
    warning_lines: list[str] = []
    for start, end in safe_segments:
        x1, y1 = to_px(*start)
        x2, y2 = to_px(*end)
        safe_lines.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" class="safe-boundary" />')
    for start, end in warning_segments:
        x1, y1 = to_px(*start)
        x2, y2 = to_px(*end)
        warning_lines.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" class="warning-boundary" />')

    ring_elements = []
    for fraction in (1 / 3, 2 / 3, 1.0):
        ring_elements.append(
            f'<circle cx="{width_px / 2:.2f}" cy="{height_px / 2:.2f}" r="{(width_px / 2) * fraction:.2f}" class="range-ring" />'
        )

    return (
        f'<g>'
        f'<rect x="0" y="0" width="{width_px}" height="{height_px}" fill="#fbfcfb" stroke="#d4ddda" stroke-width="1" />'
        f'{"".join(ring_elements)}'
        f'{"".join(rects)}'
        f'{"".join(safe_lines)}'
        f'{"".join(warning_lines)}'
        f'<circle cx="{width_px / 2:.2f}" cy="{height_px / 2:.2f}" r="5" fill="#0b6e63" stroke="#ffffff" stroke-width="2" />'
        f'<text x="0" y="{footer_y}" class="panel-title">{title}</text>'
        f'<text x="0" y="{footer_y + 18}" class="panel-subtitle">max risk {max_risk_text}</text>'
        f'</g>'
    )


def _build_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Uncertainty Contour Report Summary",
        "",
        "## Selected Case",
        "",
        f"- case_id: `{summary['case_id']}`",
        f"- timestamp: `{summary['timestamp']}`",
        f"- own_mmsi: `{summary['own_mmsi']}`",
        f"- model: `{summary['model']}`",
        f"- target_count: `{summary['target_count']}`",
        f"- max_risk_raw: `{_format_metric(summary['max_risk_raw'])}`",
        f"- max_risk_mean: `{_format_metric(summary['max_risk_mean'])}`",
        f"- max_cell_band_span: `{_format_metric(summary['max_cell_band_span'])}`",
        "",
        "## Outputs",
        "",
        f"- svg: `{summary['figure_svg_path']}`",
        f"- summary_json: `{summary['summary_json_path']}`",
        f"- summary_md: `{summary['summary_md_path']}`",
        "",
    ]
    return "\n".join(lines)


def build_uncertainty_contour_report(
    projected_cells_csv_path: str | Path,
    case_summary_csv_path: str | Path,
    output_prefix: str | Path,
    config_path: str | Path = "configs/base.toml",
    case_id: str | None = None,
) -> dict[str, Any]:
    projected_cells_path = Path(projected_cells_csv_path)
    case_summary_path = Path(case_summary_csv_path)
    resolved_config_path = Path(config_path)
    config = load_config(resolved_config_path)

    projected_rows = _read_csv_rows(projected_cells_path)
    case_rows = _read_csv_rows(case_summary_path)
    if not projected_rows:
        raise ValueError("Projected cells CSV is empty.")
    if not case_rows:
        raise ValueError("Case summary CSV is empty.")

    resolved_case_id = _resolve_case_id(case_rows, case_id)
    selected_case_summary = next(row for row in case_rows if str(row.get("case_id", "")) == resolved_case_id)
    selected_projected_rows = [row for row in projected_rows if str(row.get("case_id", "")) == resolved_case_id]
    if not selected_projected_rows:
        raise ValueError(f"No projected cell rows found for case_id={resolved_case_id}")

    radius_m = config.grid.radius_nm * 1852.0
    layers = [
        ("Raw Contour", "risk_raw", selected_case_summary.get("max_risk_raw", "0.0")),
        ("Lower Band", "risk_lower", selected_case_summary.get("max_risk_lower", "0.0")),
        ("Mean Band", "risk_mean", selected_case_summary.get("max_risk_mean", "0.0")),
        ("Upper Band", "risk_upper", selected_case_summary.get("max_risk_upper", "0.0")),
    ]

    panel_width = 320
    panel_height = 380
    gap_x = 36
    gap_y = 42
    total_width = (panel_width * 2) + gap_x
    total_height = (panel_height * 2) + gap_y + 110

    panel_groups: list[str] = []
    for index, (title, risk_key, max_risk_text) in enumerate(layers):
        row_index = index // 2
        col_index = index % 2
        x_offset = col_index * (panel_width + gap_x)
        y_offset = 78 + (row_index * (panel_height + gap_y))
        grid_cells = _to_grid_cells(selected_projected_rows, risk_key=risk_key)
        panel_groups.append(
            f'<g transform="translate({x_offset}, {y_offset})">'
            f'{_render_panel(title, grid_cells, radius_m, config.grid.cell_size_m, config.thresholds.safe, config.thresholds.warning, str(max_risk_text))}'
            f'</g>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{total_height}" viewBox="0 0 {total_width} {total_height}">
<style>
.title {{ fill: #1e2a29; font-size: 24px; font-weight: 700; font-family: Georgia, serif; }}
.subtitle {{ fill: #51605d; font-size: 13px; font-family: Georgia, serif; }}
.panel-title {{ fill: #1e2a29; font-size: 16px; font-weight: 700; font-family: Georgia, serif; }}
.panel-subtitle {{ fill: #51605d; font-size: 12px; font-family: Georgia, serif; }}
.range-ring {{ fill: none; stroke: rgba(24, 48, 44, 0.16); stroke-width: 1; stroke-dasharray: 4 4; }}
.safe-boundary {{ stroke: rgba(224, 147, 59, 0.85); stroke-width: 1.3; }}
.warning-boundary {{ stroke: rgba(190, 66, 50, 0.95); stroke-width: 1.9; }}
</style>
<rect x="0" y="0" width="{total_width}" height="{total_height}" fill="#fffdf9" />
<text x="0" y="28" class="title">Uncertainty-Aware Contour Pilot</text>
<text x="0" y="50" class="subtitle">case {resolved_case_id} | own ship {selected_case_summary.get('own_mmsi', '')} | timestamp {selected_case_summary.get('timestamp', '')} | model {selected_case_summary.get('model', '')}</text>
<text x="0" y="68" class="subtitle">target_count {selected_case_summary.get('target_count', '')} | max_cell_band_span {_format_metric(_safe_float(selected_case_summary.get('max_cell_band_span')) or 0.0)} | mean_target_band_width {_format_metric(_safe_float(selected_case_summary.get('mean_target_band_width')) or 0.0)}</text>
{''.join(panel_groups)}
</svg>"""

    output_root = Path(f"{output_prefix}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    figure_svg_path = output_root.with_name(f"{output_root.name}_figure.svg")
    summary_json_path = output_root.with_name(f"{output_root.name}_summary.json")
    summary_md_path = output_root.with_name(f"{output_root.name}_summary.md")
    figure_svg_path.write_text(svg, encoding="utf-8")

    summary = {
        "status": "completed",
        "case_id": resolved_case_id,
        "timestamp": str(selected_case_summary.get("timestamp", "")),
        "own_mmsi": str(selected_case_summary.get("own_mmsi", "")),
        "model": str(selected_case_summary.get("model", "")),
        "target_count": int(float(selected_case_summary.get("target_count", 0) or 0)),
        "max_risk_raw": _safe_float(selected_case_summary.get("max_risk_raw")) or 0.0,
        "max_risk_mean": _safe_float(selected_case_summary.get("max_risk_mean")) or 0.0,
        "max_cell_band_span": _safe_float(selected_case_summary.get("max_cell_band_span")) or 0.0,
        "projected_cells_csv_path": str(projected_cells_path),
        "case_summary_csv_path": str(case_summary_path),
        "config_path": str(resolved_config_path),
        "figure_svg_path": str(figure_svg_path),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }
    with summary_json_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    summary_md_path.write_text(_build_summary_markdown(summary), encoding="utf-8")
    return summary
