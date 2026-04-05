from __future__ import annotations

import html
import json
from pathlib import Path

from .geo import latlon_to_local_xy_m
from .models import SnapshotInput


def _risk_color(risk: float) -> str:
    if risk <= 0.0:
        return "#e6f4f1"
    if risk < 0.35:
        return "#7bd3c3"
    if risk < 0.65:
        return "#f3b463"
    return "#df5a49"


def _sector_summary_text(summary: dict[str, object], top_vessel: dict[str, object] | None) -> str:
    sector = str(summary["dominant_sector"]).replace("_", " ")
    if top_vessel is None:
        return f"Dominant risk sector is {sector}. No target vessel explanation is available."
    factors = ", ".join(str(name) for name in top_vessel["top_factors"])
    return (
        f"Dominant risk sector is {sector}. "
        f"Top contributing vessel is {top_vessel['mmsi']} with encounter "
        f"{top_vessel['encounter_type']} driven by {factors}."
    )


def _format_float(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _render_metrics(summary: dict[str, object]) -> str:
    return (
        '<div class="metrics">'
        f'<div><span class="metric-label">Max Risk</span><span class="metric-value">{_format_float(float(summary["max_risk"]))}</span></div>'
        f'<div><span class="metric-label">Mean Risk</span><span class="metric-value">{_format_float(float(summary["mean_risk"]))}</span></div>'
        f'<div><span class="metric-label">Warning Area</span><span class="metric-value">{_format_float(float(summary["warning_area_nm2"]))} nm2</span></div>'
        f'<div><span class="metric-label">Caution Area</span><span class="metric-value">{_format_float(float(summary["caution_area_nm2"]))} nm2</span></div>'
        f'<div><span class="metric-label">Targets</span><span class="metric-value">{int(summary["target_count"])}</span></div>'
        f'<div><span class="metric-label">Dominant Sector</span><span class="metric-value">{html.escape(str(summary["dominant_sector"]))}</span></div>'
        "</div>"
    )


def _render_top_vessels(top_vessels: list[dict[str, object]]) -> str:
    if not top_vessels:
        return '<div class="empty">No target vessels in range.</div>'
    rows = []
    for vessel in top_vessels[:5]:
        factors = ", ".join(html.escape(str(name)) for name in vessel["top_factors"])
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(vessel['mmsi']))}</td>"
            f"<td>{_format_float(float(vessel['score']))}</td>"
            f"<td>{html.escape(str(vessel['encounter_type']))}</td>"
            f"<td>{_format_float(float(vessel['tcpa_min']), 1)}</td>"
            f"<td>{_format_float(float(vessel['dcpa_nm']), 2)}</td>"
            f"<td>{factors}</td>"
            "</tr>"
        )
    return (
        '<table class="vessel-table">'
        "<thead><tr><th>MMSI</th><th>Score</th><th>Encounter</th><th>TCPA(min)</th><th>DCPA(NM)</th><th>Top Factors</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _svg_style_block() -> str:
    return """<style>
    .range-ring { fill: none; stroke: rgba(29,43,42,0.18); stroke-width: 1; stroke-dasharray: 4 5; }
    .axis-line { stroke: rgba(29,43,42,0.2); stroke-width: 1; }
    .safe-boundary line { stroke: rgba(207,109,63,0.6); stroke-width: 1.25; }
    .warning-boundary line { stroke: rgba(182,66,53,0.9); stroke-width: 1.9; }
    .target-dot { fill: #1d2b2a; opacity: 0.88; }
    .target-label { fill: #1d2b2a; font-size: 11px; font-family: ui-monospace, monospace; }
    .own-ship-dot { fill: #0b6e63; stroke: #ffffff; stroke-width: 2; }
    .own-heading { stroke: #0b6e63; stroke-width: 3; stroke-linecap: round; }
    .caption-box { fill: #fffdf8; stroke: #d7cec0; stroke-width: 1; }
    .caption-title { fill: #1d2b2a; font-size: 12px; font-weight: 700; font-family: Georgia, serif; }
    .caption-line { fill: #495450; font-size: 11px; font-family: Georgia, serif; }
    </style>"""


def _svg_caption_lines(summary: dict[str, object], top_vessel: dict[str, object] | None) -> tuple[str, str, str]:
    scenario_name = str(summary["scenario_name"]).capitalize()
    line_1 = (
        f"{scenario_name} | speed x{float(summary['speed_multiplier']):.2f} | "
        f"max risk {_format_float(float(summary['max_risk']))} | "
        f"warning {_format_float(float(summary['warning_area_nm2']))} nm2"
    )
    line_2 = (
        f"targets {int(summary['target_count'])} | "
        f"dominant sector {str(summary['dominant_sector']).replace('_', ' ')} | "
        f"mean risk {_format_float(float(summary['mean_risk']))}"
    )
    if top_vessel is None:
        line_3 = "No target-vessel explanation available in this scenario."
    else:
        line_3 = (
            f"top vessel {top_vessel['mmsi']} | {top_vessel['encounter_type']} | "
            f"TCPA {_format_float(float(top_vessel['tcpa_min']), 1)} min | "
            f"DCPA {_format_float(float(top_vessel['dcpa_nm']), 2)} NM"
        )
    return line_1, line_2, line_3


def _build_cell_lookup(cells: list[dict[str, object]]) -> tuple[dict[tuple[float, float], float], float]:
    if len(cells) < 2:
        return {(float(cell["x_m"]), float(cell["y_m"])): float(cell["risk"]) for cell in cells}, 0.0
    xs = sorted({float(cell["x_m"]) for cell in cells})
    step = min(b - a for a, b in zip(xs, xs[1:], strict=False)) if len(xs) > 1 else 0.0
    lookup = {(float(cell["x_m"]), float(cell["y_m"])): float(cell["risk"]) for cell in cells}
    return lookup, step


def _boundary_segments(
    cells: list[dict[str, object]],
    threshold: float,
    cell_size_m: float,
    radius_m: float,
    width_px: int,
    height_px: int,
) -> list[str]:
    lookup, step = _build_cell_lookup(cells)
    if step <= 0.0:
        return []

    def to_px(x_m: float, y_m: float) -> tuple[float, float]:
        px = ((x_m + radius_m) / (2.0 * radius_m)) * width_px
        py = height_px - (((y_m + radius_m) / (2.0 * radius_m)) * height_px)
        return px, py

    half = cell_size_m / 2.0
    segments: list[str] = []
    directions = {
        "left": (-step, 0.0),
        "right": (step, 0.0),
        "down": (0.0, -step),
        "up": (0.0, step),
    }

    for (x_m, y_m), risk in lookup.items():
        if risk < threshold:
            continue
        for side, (dx, dy) in directions.items():
            neighbor_risk = lookup.get((x_m + dx, y_m + dy), -1.0)
            if neighbor_risk >= threshold:
                continue
            if side == "left":
                x1, y1 = to_px(x_m - half, y_m - half)
                x2, y2 = to_px(x_m - half, y_m + half)
            elif side == "right":
                x1, y1 = to_px(x_m + half, y_m - half)
                x2, y2 = to_px(x_m + half, y_m + half)
            elif side == "up":
                x1, y1 = to_px(x_m - half, y_m + half)
                x2, y2 = to_px(x_m + half, y_m + half)
            else:
                x1, y1 = to_px(x_m - half, y_m - half)
                x2, y2 = to_px(x_m + half, y_m - half)
            segments.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" />')
    return segments


def _render_svg_panel(
    scenario: dict[str, object],
    snapshot: SnapshotInput,
    radius_nm: float,
    cell_size_m: float,
    safe_threshold: float,
    warning_threshold: float,
) -> str:
    width_px = 420
    plot_height_px = 420
    footer_height_px = 82
    total_height_px = plot_height_px + footer_height_px + 8
    radius_m = radius_nm * 1852.0

    def to_px(x_m: float, y_m: float) -> tuple[float, float]:
        px = ((x_m + radius_m) / (2.0 * radius_m)) * width_px
        py = plot_height_px - (((y_m + radius_m) / (2.0 * radius_m)) * plot_height_px)
        return px, py

    cells = scenario["cells"]
    cell_rects = []
    half = cell_size_m / 2.0
    for cell in cells:
        x_m = float(cell["x_m"])
        y_m = float(cell["y_m"])
        risk = float(cell["risk"])
        if risk < 0.02:
            continue
        x1, y1 = to_px(x_m - half, y_m + half)
        x2, y2 = to_px(x_m + half, y_m - half)
        width = max(1.0, x2 - x1)
        height = max(1.0, y2 - y1)
        opacity = 0.1 + (0.9 * risk)
        cell_rects.append(
            f'<rect x="{x1:.2f}" y="{y1:.2f}" width="{width:.2f}" height="{height:.2f}" '
            f'fill="{_risk_color(risk)}" fill-opacity="{opacity:.3f}" stroke="none" />'
        )

    ring_elements = []
    for ring_nm in (2, 4, 6):
        radius_px = (ring_nm / radius_nm) * (width_px / 2.0)
        ring_elements.append(
            f'<circle cx="{width_px/2:.2f}" cy="{plot_height_px/2:.2f}" r="{radius_px:.2f}" class="range-ring" />'
        )

    axis_elements = [
        f'<line x1="{width_px/2:.2f}" y1="0" x2="{width_px/2:.2f}" y2="{plot_height_px}" class="axis-line" />',
        f'<line x1="0" y1="{plot_height_px/2:.2f}" x2="{width_px}" y2="{plot_height_px/2:.2f}" class="axis-line" />',
    ]

    target_elements = []
    for target in snapshot.targets:
        dx_m, dy_m = latlon_to_local_xy_m(snapshot.own_ship.lat, snapshot.own_ship.lon, target.lat, target.lon)
        px, py = to_px(dx_m, dy_m)
        target_elements.append(
            f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4.5" class="target-dot" />'
            f'<text x="{px + 7:.2f}" y="{py - 6:.2f}" class="target-label">{html.escape(target.mmsi[-4:])}</text>'
        )

    own_heading = snapshot.own_ship.heading_or_cog
    import math

    heading_rad = math.radians(own_heading)
    hx = (width_px / 2.0) + (32.0 * math.sin(heading_rad))
    hy = (plot_height_px / 2.0) - (32.0 * math.cos(heading_rad))
    own_ship_elements = [
        f'<circle cx="{width_px/2:.2f}" cy="{plot_height_px/2:.2f}" r="6" class="own-ship-dot" />',
        f'<line x1="{width_px/2:.2f}" y1="{plot_height_px/2:.2f}" x2="{hx:.2f}" y2="{hy:.2f}" class="own-heading" />',
    ]

    warning_segments = _boundary_segments(cells, warning_threshold, cell_size_m, radius_m, width_px, plot_height_px)
    safe_segments = _boundary_segments(cells, safe_threshold, cell_size_m, radius_m, width_px, plot_height_px)
    caption_top_vessel = scenario["top_vessels"][0] if scenario["top_vessels"] else None
    caption_line_1, caption_line_2, caption_line_3 = _svg_caption_lines(scenario["summary"], caption_top_vessel)
    footer_y = plot_height_px + 8

    return (
        f'<svg viewBox="0 0 {width_px} {total_height_px}" class="scenario-svg" role="img" '
        f'aria-label="Risk grid for {html.escape(str(scenario["summary"]["scenario_name"]))}">'
        f"{_svg_style_block()}"
        f"{''.join(cell_rects)}"
        f"{''.join(ring_elements)}"
        f"{''.join(axis_elements)}"
        f'<g class="safe-boundary">{"".join(safe_segments)}</g>'
        f'<g class="warning-boundary">{"".join(warning_segments)}</g>'
        f"{''.join(target_elements)}"
        f"{''.join(own_ship_elements)}"
        f'<rect x="8" y="{footer_y:.2f}" width="{width_px - 16:.2f}" height="{footer_height_px - 8:.2f}" rx="10" class="caption-box" />'
        f'<text x="18" y="{footer_y + 18:.2f}" class="caption-title">{html.escape(caption_line_1)}</text>'
        f'<text x="18" y="{footer_y + 38:.2f}" class="caption-line">{html.escape(caption_line_2)}</text>'
        f'<text x="18" y="{footer_y + 58:.2f}" class="caption-line">{html.escape(caption_line_3)}</text>'
        "</svg>"
    )


def build_scenario_svg_text(
    snapshot: SnapshotInput,
    scenario: dict[str, object],
    radius_nm: float,
    cell_size_m: float,
    safe_threshold: float,
    warning_threshold: float,
) -> str:
    return _render_svg_panel(
        scenario=scenario,
        snapshot=snapshot,
        radius_nm=radius_nm,
        cell_size_m=cell_size_m,
        safe_threshold=safe_threshold,
        warning_threshold=warning_threshold,
    )


def build_html_report_text(
    snapshot: SnapshotInput,
    result: dict[str, object],
    radius_nm: float,
    cell_size_m: float,
    safe_threshold: float,
    warning_threshold: float,
) -> str:
    scenario_blocks = []
    for scenario in result["scenarios"]:
        summary = scenario["summary"]
        top_vessels = scenario["top_vessels"]
        explanation = _sector_summary_text(summary, top_vessels[0] if top_vessels else None)
        scenario_blocks.append(
            '<section class="scenario-card">'
            f'<h2>{html.escape(str(summary["scenario_name"]))}</h2>'
            f'<div class="scenario-subtitle">Speed multiplier: {float(summary["speed_multiplier"]):.2f}x</div>'
            f'{build_scenario_svg_text(snapshot, scenario, radius_nm, cell_size_m, safe_threshold, warning_threshold)}'
            f'{_render_metrics(summary)}'
            f'<p class="scenario-explanation">{html.escape(explanation)}</p>'
            f"{_render_top_vessels(top_vessels)}"
            "</section>"
        )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(result["project_name"])} Report</title>
  <style>
    :root {{
      --bg: #f4f1e8;
      --panel: #fffdf8;
      --line: #d7cec0;
      --text: #1d2b2a;
      --muted: #66706c;
      --accent: #0b6e63;
      --warn: #cf6d3f;
      --danger: #b64235;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Georgia", "Times New Roman", serif;
      background: radial-gradient(circle at top left, #faf6ef 0%, var(--bg) 48%, #e9e2d4 100%);
      color: var(--text);
    }}
    .page {{
      max-width: 1480px;
      margin: 0 auto;
      padding: 28px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(11,110,99,0.08), rgba(182,66,53,0.05));
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 24px;
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 34px;
      line-height: 1.1;
    }}
    .sub {{
      color: var(--muted);
      margin-bottom: 16px;
      font-size: 15px;
    }}
    .disclaimer {{
      border-left: 4px solid var(--warn);
      padding-left: 12px;
      color: #574e46;
      font-size: 14px;
    }}
    .legend {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 16px;
    }}
    .legend span {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.7);
      border: 1px solid var(--line);
      font-size: 13px;
    }}
    .swatch {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      display: inline-block;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(430px, 1fr));
      gap: 18px;
    }}
    .scenario-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 12px 40px rgba(37, 34, 28, 0.05);
    }}
    .scenario-card h2 {{
      margin: 0;
      text-transform: capitalize;
      font-size: 24px;
    }}
    .scenario-subtitle {{
      color: var(--muted);
      margin: 6px 0 14px;
      font-size: 14px;
    }}
    .scenario-svg {{
      width: 100%;
      border-radius: 14px;
      background: linear-gradient(180deg, #eef8f6 0%, #f8f4ea 100%);
      border: 1px solid var(--line);
    }}
    .range-ring {{
      fill: none;
      stroke: rgba(29,43,42,0.18);
      stroke-width: 1;
      stroke-dasharray: 4 5;
    }}
    .axis-line {{
      stroke: rgba(29,43,42,0.2);
      stroke-width: 1;
    }}
    .safe-boundary line {{
      stroke: rgba(207,109,63,0.6);
      stroke-width: 1.25;
    }}
    .warning-boundary line {{
      stroke: rgba(182,66,53,0.9);
      stroke-width: 1.9;
    }}
    .target-dot {{
      fill: #1d2b2a;
      opacity: 0.88;
    }}
    .target-label {{
      fill: #1d2b2a;
      font-size: 11px;
      font-family: ui-monospace, "SFMono-Regular", monospace;
    }}
    .own-ship-dot {{
      fill: var(--accent);
      stroke: white;
      stroke-width: 2;
    }}
    .own-heading {{
      stroke: var(--accent);
      stroke-width: 3;
      stroke-linecap: round;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
      margin-bottom: 14px;
    }}
    .metrics > div {{
      background: rgba(11,110,99,0.05);
      border: 1px solid rgba(11,110,99,0.12);
      border-radius: 12px;
      padding: 10px;
    }}
    .metric-label {{
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 5px;
    }}
    .metric-value {{
      font-size: 18px;
      font-weight: 700;
    }}
    .scenario-explanation {{
      margin: 0 0 14px;
      line-height: 1.45;
    }}
    .vessel-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    .vessel-table th,
    .vessel-table td {{
      border-top: 1px solid var(--line);
      padding: 8px 6px;
      text-align: left;
      vertical-align: top;
    }}
    .vessel-table th {{
      color: var(--muted);
      font-weight: 600;
    }}
    .footer-note {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 13px;
    }}
    @media (max-width: 920px) {{
      .page {{ padding: 16px; }}
      .grid {{ grid-template-columns: 1fr; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <h1>{html.escape(result["project_name"])}</h1>
      <div class="sub">Own-ship-centric spatial risk report | timestamp {html.escape(result["timestamp"])}</div>
      <div class="disclaimer">{html.escape(result["disclaimer"])}</div>
      <div class="legend">
        <span><i class="swatch" style="background:#7bd3c3"></i> Safe (&lt; {safe_threshold:.2f})</span>
        <span><i class="swatch" style="background:#f3b463"></i> Caution ({safe_threshold:.2f} - {warning_threshold:.2f})</span>
        <span><i class="swatch" style="background:#df5a49"></i> Danger (&gt;= {warning_threshold:.2f})</span>
        <span><i class="swatch" style="background:#0b6e63"></i> Own ship</span>
        <span><i class="swatch" style="background:#1d2b2a"></i> Target ship</span>
      </div>
    </section>
    <section class="grid">
      {''.join(scenario_blocks)}
    </section>
    <div class="footer-note">
      Local frame view uses own ship as the center. Boundary lines are threshold boundaries over cell risks, not legal safety guarantees.
    </div>
  </main>
</body>
</html>
"""
    return html_text


def build_html_report(
    snapshot: SnapshotInput,
    result_path: str | Path,
    output_path: str | Path,
    radius_nm: float,
    cell_size_m: float,
    safe_threshold: float,
    warning_threshold: float,
) -> None:
    result = json.loads(Path(result_path).read_text(encoding="utf-8"))
    html_text = build_html_report_text(
        snapshot=snapshot,
        result=result,
        radius_nm=radius_nm,
        cell_size_m=cell_size_m,
        safe_threshold=safe_threshold,
        warning_threshold=warning_threshold,
    )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html_text, encoding="utf-8")


def save_scenario_svg(
    output_path: str | Path,
    snapshot: SnapshotInput,
    scenario: dict[str, object],
    radius_nm: float,
    cell_size_m: float,
    safe_threshold: float,
    warning_threshold: float,
) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        build_scenario_svg_text(
            snapshot=snapshot,
            scenario=scenario,
            radius_nm=radius_nm,
            cell_size_m=cell_size_m,
            safe_threshold=safe_threshold,
            warning_threshold=warning_threshold,
        ),
        encoding="utf-8",
    )


def build_all_scenario_svg_texts(
    snapshot: SnapshotInput,
    result: dict[str, object],
    radius_nm: float,
    cell_size_m: float,
    safe_threshold: float,
    warning_threshold: float,
) -> dict[str, str]:
    return {
        str(scenario["summary"]["scenario_name"]): build_scenario_svg_text(
            snapshot=snapshot,
            scenario=scenario,
            radius_nm=radius_nm,
            cell_size_m=cell_size_m,
            safe_threshold=safe_threshold,
            warning_threshold=warning_threshold,
        )
        for scenario in result["scenarios"]
    }


def save_all_scenario_svgs(
    output_dir: str | Path,
    snapshot: SnapshotInput,
    result: dict[str, object],
    radius_nm: float,
    cell_size_m: float,
    safe_threshold: float,
    warning_threshold: float,
) -> dict[str, str]:
    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    svg_texts = build_all_scenario_svg_texts(
        snapshot=snapshot,
        result=result,
        radius_nm=radius_nm,
        cell_size_m=cell_size_m,
        safe_threshold=safe_threshold,
        warning_threshold=warning_threshold,
    )
    saved_paths: dict[str, str] = {}
    for scenario_name, svg_text in svg_texts.items():
        output_path = destination_dir / f"{scenario_name}_scenario.svg"
        output_path.write_text(svg_text, encoding="utf-8")
        saved_paths[scenario_name] = str(output_path)
    return saved_paths
