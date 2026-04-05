from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import plotly.graph_objects as go
import streamlit as st

from ais_risk.case_mining import mine_cases_from_curated_rows
from ais_risk.config import load_config
from ais_risk.contours import extract_threshold_segments
from ais_risk.csv_tools import build_snapshot_from_curated_rows, load_curated_csv_rows, parse_column_overrides, preprocess_ais_csv
from ais_risk.demo_package import build_recommended_demo_package
from ais_risk.experiments import run_ablation_experiment, run_baseline_experiment
from ais_risk.geo import latlon_to_local_xy_m, local_xy_to_latlon
from ais_risk.ingestion_bundles import (
    get_ingestion_bundle,
    list_ingestion_bundle_names,
    load_ingestion_bundle_config,
    resolve_ingestion_bundle,
)
from ais_risk.io import load_snapshot
from ais_risk.models import PairwiseRisk, ProjectConfig, ScenarioResult, SnapshotInput, SnapshotResult
from ais_risk.own_ship_candidates import recommend_own_ship_candidates_rows
from ais_risk.paper_assets import build_paper_assets_from_manifest
from ais_risk.pipeline import run_snapshot
from ais_risk.profile import build_profile_markdown, profile_curated_rows
from ais_risk.report import build_all_scenario_svg_texts, build_html_report_text, build_scenario_svg_text
from ais_risk.schema_probe import inspect_csv_schema
from ais_risk.source_presets import get_source_preset, list_source_preset_names, resolve_source_preset
from ais_risk.summary import build_markdown_summary_from_data
from ais_risk.trajectory import reconstruct_trajectory_csv
from ais_risk.workflow import run_ingestion_workflow


DEFAULT_CONFIG = Path("configs/base.toml")
DEFAULT_TRACKS = Path("outputs/sample_ais_tracks.csv")
DEFAULT_SNAPSHOT = Path("outputs/from_tracks_snapshot.json")


@st.cache_data(show_spinner=False)
def cached_load_config(path: str) -> ProjectConfig:
    return load_config(path)


@st.cache_data(show_spinner=False)
def cached_load_rows(path: str) -> list[dict[str, str]]:
    return load_curated_csv_rows(path)


@st.cache_data(show_spinner=False)
def cached_load_snapshot(path: str) -> SnapshotInput:
    return load_snapshot(path)


@st.cache_data(show_spinner=False)
def cached_run_snapshot(snapshot: SnapshotInput, config: ProjectConfig) -> SnapshotResult:
    return run_snapshot(snapshot, config)


@st.cache_data(show_spinner=False)
def cached_rank_own_ship_candidates(
    path: str,
    config_path: str,
    radius_nm: float,
    top_n: int,
    min_targets: int,
) -> list[dict[str, object]]:
    rows = load_curated_csv_rows(path)
    config = load_config(config_path)
    return recommend_own_ship_candidates_rows(
        rows=rows,
        config=config,
        radius_nm=radius_nm,
        top_n=top_n,
        min_targets=min_targets,
    )


def _scenario_figure(
    snapshot: SnapshotInput,
    scenario: ScenarioResult,
    config: ProjectConfig,
    show_contours: bool,
) -> go.Figure:
    marker_size = max(6.0, min(20.0, config.grid.cell_size_m / 16.0))
    cell_x = [cell.x_m for cell in scenario.cells if cell.risk >= 0.02]
    cell_y = [cell.y_m for cell in scenario.cells if cell.risk >= 0.02]
    cell_risk = [cell.risk for cell in scenario.cells if cell.risk >= 0.02]
    cell_text = [
        f"risk={cell.risk:.3f}<br>label={cell.label}<br>x={cell.x_m:.0f}m<br>y={cell.y_m:.0f}m"
        for cell in scenario.cells
        if cell.risk >= 0.02
    ]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=cell_x,
            y=cell_y,
            mode="markers",
            marker={
                "symbol": "square",
                "size": marker_size,
                "color": cell_risk,
                "colorscale": [
                    [0.0, "#7bd3c3"],
                    [0.5, "#f3b463"],
                    [1.0, "#df5a49"],
                ],
                "cmin": 0.0,
                "cmax": 1.0,
                "line": {"width": 0},
                "opacity": 0.80,
                "colorbar": {"title": "Risk"} if scenario.summary.scenario_name == "current" else None,
            },
            text=cell_text,
            hovertemplate="%{text}<extra></extra>",
            name="Risk Cells",
        )
    )

    figure.add_trace(
        go.Scatter(
            x=[0.0],
            y=[0.0],
            mode="markers+text",
            marker={"size": 14, "color": "#0b6e63", "symbol": "diamond"},
            text=["Own Ship"],
            textposition="top center",
            name="Own Ship",
            hovertemplate="Own ship<extra></extra>",
        )
    )

    target_x = []
    target_y = []
    target_text = []
    for target in snapshot.targets:
        dx_m, dy_m = latlon_to_local_xy_m(snapshot.own_ship.lat, snapshot.own_ship.lon, target.lat, target.lon)
        target_x.append(dx_m)
        target_y.append(dy_m)
        target_text.append(
            f"MMSI={target.mmsi}<br>SOG={target.sog:.1f} kn<br>COG={target.cog:.1f} deg<br>Type={target.vessel_type or 'unknown'}"
        )
    if target_x:
        figure.add_trace(
            go.Scatter(
                x=target_x,
                y=target_y,
                mode="markers+text",
                marker={"size": 9, "color": "#1d2b2a"},
                text=[target.mmsi[-4:] for target in snapshot.targets],
                textposition="top center",
                name="Targets",
                hovertemplate="%{text}<br>%{customdata}<extra></extra>",
                customdata=target_text,
            )
        )

    radius_m = config.grid.radius_nm * 1852.0
    for ring_nm in (2, 4, 6):
        ring_m = ring_nm * 1852.0
        if ring_m > radius_m:
            continue
        figure.add_shape(type="circle", x0=-ring_m, y0=-ring_m, x1=ring_m, y1=ring_m, line={"color": "rgba(29,43,42,0.2)", "dash": "dot"})

    figure.add_hline(y=0.0, line={"color": "rgba(29,43,42,0.18)", "width": 1})
    figure.add_vline(x=0.0, line={"color": "rgba(29,43,42,0.18)", "width": 1})
    if show_contours:
        safe_segments = extract_threshold_segments(
            scenario.cells,
            threshold=config.thresholds.safe,
            cell_size_m=config.grid.cell_size_m,
        )
        warning_segments = extract_threshold_segments(
            scenario.cells,
            threshold=config.thresholds.warning,
            cell_size_m=config.grid.cell_size_m,
        )
        if safe_segments:
            safe_x: list[float | None] = []
            safe_y: list[float | None] = []
            for (x1, y1), (x2, y2) in safe_segments:
                safe_x.extend([x1, x2, None])
                safe_y.extend([y1, y2, None])
            figure.add_trace(
                go.Scatter(
                    x=safe_x,
                    y=safe_y,
                    mode="lines",
                    line={"color": "#cf6d3f", "width": 1.5},
                    hoverinfo="skip",
                    name="Safety Contour",
                )
            )
        if warning_segments:
            warning_x: list[float | None] = []
            warning_y: list[float | None] = []
            for (x1, y1), (x2, y2) in warning_segments:
                warning_x.extend([x1, x2, None])
                warning_y.extend([y1, y2, None])
            figure.add_trace(
                go.Scatter(
                    x=warning_x,
                    y=warning_y,
                    mode="lines",
                    line={"color": "#b64235", "width": 2.0},
                    hoverinfo="skip",
                    name="Warning Contour",
                )
            )
    figure.update_layout(
        title=f"{scenario.summary.scenario_name.capitalize()} ({scenario.summary.speed_multiplier:.2f}x)",
        margin={"l": 10, "r": 10, "t": 44, "b": 10},
        paper_bgcolor="#fffdf8",
        plot_bgcolor="#eef8f6",
        height=450,
        legend={"orientation": "h"},
    )
    figure.update_xaxes(title="Local X (m)", range=[-radius_m, radius_m], scaleanchor="y", scaleratio=1)
    figure.update_yaxes(title="Local Y (m)", range=[-radius_m, radius_m])
    return figure


def _scenario_map_figure(
    snapshot: SnapshotInput,
    scenario: ScenarioResult,
    config: ProjectConfig,
    show_contours: bool,
) -> go.Figure:
    own_lat = snapshot.own_ship.lat
    own_lon = snapshot.own_ship.lon
    risk_cells = [cell for cell in scenario.cells if cell.risk >= 0.02]
    cell_lats = []
    cell_lons = []
    cell_risks = []
    cell_text = []
    for cell in risk_cells:
        lat, lon = local_xy_to_latlon(own_lat, own_lon, cell.x_m, cell.y_m)
        cell_lats.append(lat)
        cell_lons.append(lon)
        cell_risks.append(cell.risk)
        cell_text.append(
            f"risk={cell.risk:.3f}<br>label={cell.label}<br>x={cell.x_m:.0f}m<br>y={cell.y_m:.0f}m"
        )

    figure = go.Figure()
    if cell_lats:
        figure.add_trace(
            go.Scattermapbox(
                lat=cell_lats,
                lon=cell_lons,
                mode="markers",
                marker={
                    "size": 10,
                    "color": cell_risks,
                    "colorscale": [
                        [0.0, "#7bd3c3"],
                        [0.5, "#f3b463"],
                        [1.0, "#df5a49"],
                    ],
                    "cmin": 0.0,
                    "cmax": 1.0,
                    "opacity": 0.70,
                    "colorbar": {"title": "Risk"} if scenario.summary.scenario_name == "current" else None,
                },
                text=cell_text,
                hovertemplate="%{text}<extra></extra>",
                name="Risk Cells",
            )
        )

    figure.add_trace(
        go.Scattermapbox(
            lat=[own_lat],
            lon=[own_lon],
            mode="markers+text",
            marker={"size": 16, "color": "#0b6e63"},
            text=["Own Ship"],
            textposition="top right",
            hovertemplate="Own ship<extra></extra>",
            name="Own Ship",
        )
    )
    if snapshot.targets:
        figure.add_trace(
            go.Scattermapbox(
                lat=[target.lat for target in snapshot.targets],
                lon=[target.lon for target in snapshot.targets],
                mode="markers+text",
                marker={"size": 9, "color": "#1d2b2a"},
                text=[target.mmsi[-4:] for target in snapshot.targets],
                textposition="top right",
                hovertemplate=(
                    "MMSI=%{customdata[0]}<br>SOG=%{customdata[1]:.1f} kn<br>"
                    "COG=%{customdata[2]:.1f} deg<br>Type=%{customdata[3]}<extra></extra>"
                ),
                customdata=[
                    [target.mmsi, target.sog, target.cog, target.vessel_type or "unknown"]
                    for target in snapshot.targets
                ],
                name="Targets",
            )
        )

    if show_contours:
        safe_segments = extract_threshold_segments(
            scenario.cells,
            threshold=config.thresholds.safe,
            cell_size_m=config.grid.cell_size_m,
        )
        warning_segments = extract_threshold_segments(
            scenario.cells,
            threshold=config.thresholds.warning,
            cell_size_m=config.grid.cell_size_m,
        )
        if safe_segments:
            safe_lat: list[float | None] = []
            safe_lon: list[float | None] = []
            for (x1, y1), (x2, y2) in safe_segments:
                lat1, lon1 = local_xy_to_latlon(own_lat, own_lon, x1, y1)
                lat2, lon2 = local_xy_to_latlon(own_lat, own_lon, x2, y2)
                safe_lat.extend([lat1, lat2, None])
                safe_lon.extend([lon1, lon2, None])
            figure.add_trace(
                go.Scattermapbox(
                    lat=safe_lat,
                    lon=safe_lon,
                    mode="lines",
                    line={"color": "#cf6d3f", "width": 2},
                    hoverinfo="skip",
                    name="Safety Contour",
                )
            )
        if warning_segments:
            warning_lat: list[float | None] = []
            warning_lon: list[float | None] = []
            for (x1, y1), (x2, y2) in warning_segments:
                lat1, lon1 = local_xy_to_latlon(own_lat, own_lon, x1, y1)
                lat2, lon2 = local_xy_to_latlon(own_lat, own_lon, x2, y2)
                warning_lat.extend([lat1, lat2, None])
                warning_lon.extend([lon1, lon2, None])
            figure.add_trace(
                go.Scattermapbox(
                    lat=warning_lat,
                    lon=warning_lon,
                    mode="lines",
                    line={"color": "#b64235", "width": 3},
                    hoverinfo="skip",
                    name="Warning Contour",
                )
            )

    radius_km = config.grid.radius_nm * 1.852
    zoom = max(7.0, min(13.0, 12.5 - math.log2(max(radius_km, 0.5))))
    figure.update_layout(
        title=f"{scenario.summary.scenario_name.capitalize()} Geo Map",
        height=450,
        margin={"l": 10, "r": 10, "t": 44, "b": 10},
        mapbox={
            "style": "carto-positron",
            "center": {"lat": own_lat, "lon": own_lon},
            "zoom": zoom,
        },
        legend={"orientation": "h"},
    )
    return figure


def _top_vessel_rows(top_vessels: Iterable[PairwiseRisk]) -> list[dict[str, str]]:
    rows = []
    for vessel in top_vessels:
        rows.append(
            {
                "mmsi": vessel.mmsi,
                "score": f"{vessel.score:.3f}",
                "encounter": vessel.encounter_type,
                "tcpa_min": f"{vessel.tcpa_min:.1f}",
                "dcpa_nm": f"{vessel.dcpa_nm:.2f}",
                "distance_nm": f"{vessel.distance_nm:.2f}",
                "top_factors": ", ".join(vessel.top_factors),
            }
        )
    return rows


def _build_snapshot_from_controls(rows: list[dict[str, str]], own_mmsi: str, timestamp: str, radius_nm: float) -> SnapshotInput:
    return build_snapshot_from_curated_rows(
        rows=rows,
        own_mmsi=own_mmsi,
        timestamp=timestamp,
        radius_nm=radius_nm,
    )


def _render_summary_cards(result: SnapshotResult) -> None:
    columns = st.columns(len(result.scenarios))
    for column, scenario in zip(columns, result.scenarios, strict=True):
        with column:
            st.metric("Scenario", scenario.summary.scenario_name)
            st.metric("Max Risk", f"{scenario.summary.max_risk:.3f}")
            st.metric("Warning Area (nm2)", f"{scenario.summary.warning_area_nm2:.3f}")
            st.metric("Dominant Sector", scenario.summary.dominant_sector)


def _default_existing_path(preferred: Path, fallback: Path) -> str:
    if preferred.exists():
        return str(preferred)
    return str(fallback)


def _optional_float(raw: str) -> float | None:
    text = raw.strip()
    if not text:
        return None
    return float(text)


def _optional_str(raw: str) -> str | None:
    text = raw.strip()
    return text or None


def _rows_to_csv_text(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _format_candidate_rows(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    formatted: list[dict[str, str]] = []
    for row in rows:
        formatted.append(
            {
                "rank": str(row["rank"]),
                "mmsi": str(row["mmsi"]),
                "score": f"{float(row['candidate_score']):.3f}",
                "interaction": f"{float(row['interaction_score']):.3f}",
                "continuity": f"{float(row['continuity_score']):.3f}",
                "best_time": str(row.get("recommended_timestamp", "")),
                "best_max_risk": "" if "recommended_max_risk" not in row else f"{float(row['recommended_max_risk']):.3f}",
                "source": str(row.get("recommendation_source", "")),
                "active_windows": str(row["active_window_count"]),
                "avg_nearby": f"{float(row['average_nearby_targets']):.2f}",
                "type": str(row["vessel_type"]),
                "reason": str(row["reason_summary"]),
            }
        )
    return formatted


def _scenario_average_chart(aggregate: dict[str, object]) -> go.Figure:
    scenario_names = list(aggregate["scenario_averages"].keys())
    warning_area = [aggregate["scenario_averages"][name]["avg_warning_area_nm2"] for name in scenario_names]
    max_risk = [aggregate["scenario_averages"][name]["avg_max_risk"] for name in scenario_names]

    figure = go.Figure()
    figure.add_trace(go.Bar(name="Avg Warning Area (nm2)", x=scenario_names, y=warning_area, marker_color="#cf6d3f"))
    figure.add_trace(go.Bar(name="Avg Max Risk", x=scenario_names, y=max_risk, marker_color="#0b6e63"))
    figure.update_layout(
        barmode="group",
        height=360,
        margin={"l": 10, "r": 10, "t": 36, "b": 10},
        paper_bgcolor="#fffdf8",
        plot_bgcolor="#fffdf8",
        title="Scenario Averages",
    )
    return figure


def _ablation_current_chart(aggregate: dict[str, object]) -> go.Figure:
    labels = []
    warning_deltas = []
    risk_deltas = []
    for label, scenario_map in aggregate["ablations"].items():
        if label == "baseline":
            continue
        current = scenario_map.get("current")
        if current is None:
            continue
        labels.append(label)
        warning_deltas.append(current["avg_delta_warning_area_vs_baseline"])
        risk_deltas.append(current["avg_delta_max_risk_vs_baseline"])

    figure = go.Figure()
    if labels:
        figure.add_trace(go.Bar(name="Delta Warning Area vs Baseline", x=labels, y=warning_deltas, marker_color="#df5a49"))
        figure.add_trace(go.Bar(name="Delta Max Risk vs Baseline", x=labels, y=risk_deltas, marker_color="#245e72"))
    figure.update_layout(
        barmode="group",
        height=360,
        margin={"l": 10, "r": 10, "t": 36, "b": 10},
        paper_bgcolor="#fffdf8",
        plot_bgcolor="#fffdf8",
        title="Current Scenario Ablation Impact",
    )
    return figure


def _render_experiment_lab(rows: list[dict[str, str]], own_mmsi: str, radius_nm: float, config: ProjectConfig) -> None:
    st.subheader("Experiment Lab")
    control_columns = st.columns([1, 1, 2])
    with control_columns[0]:
        top_n = st.slider("Experiment Top N Cases", min_value=2, max_value=20, value=5, step=1)
    with control_columns[1]:
        min_targets = st.slider("Experiment Min Targets", min_value=1, max_value=10, value=1, step=1)
    with control_columns[2]:
        selected_ablations = st.multiselect(
            "Ablations",
            options=["distance", "dcpa", "tcpa", "bearing", "relspeed", "encounter", "density", "time_decay", "spatial_kernel"],
            default=["bearing", "density", "time_decay", "spatial_kernel"],
        )

    button_columns = st.columns(2)
    if button_columns[0].button("Run Baseline Experiment", use_container_width=True):
        experiment_rows, experiment_aggregate = run_baseline_experiment(
            rows=rows,
            own_mmsi=own_mmsi,
            config=config,
            radius_nm=radius_nm,
            top_n=top_n,
            min_targets=min_targets,
        )
        st.session_state["experiment_rows"] = experiment_rows
        st.session_state["experiment_aggregate"] = experiment_aggregate

    if button_columns[1].button("Run Ablation Experiment", use_container_width=True):
        ablation_rows, ablation_aggregate = run_ablation_experiment(
            rows=rows,
            own_mmsi=own_mmsi,
            config=config,
            radius_nm=radius_nm,
            ablation_names=selected_ablations,
            top_n=top_n,
            min_targets=min_targets,
        )
        st.session_state["ablation_rows"] = ablation_rows
        st.session_state["ablation_aggregate"] = ablation_aggregate

    experiment_aggregate = st.session_state.get("experiment_aggregate")
    experiment_rows = st.session_state.get("experiment_rows")
    if experiment_aggregate:
        st.markdown("**Baseline Batch Summary**")
        metric_columns = st.columns(3)
        metric_columns[0].metric("Case Count", int(experiment_aggregate["case_count"]))
        current_metrics = experiment_aggregate["scenario_averages"]["current"]
        metric_columns[1].metric("Current Avg Max Risk", f"{current_metrics['avg_max_risk']:.3f}")
        metric_columns[2].metric("Current Avg Warning Area", f"{current_metrics['avg_warning_area_nm2']:.3f} nm2")
        st.plotly_chart(_scenario_average_chart(experiment_aggregate), use_container_width=True)
        with st.expander("Baseline Experiment Rows", expanded=False):
            st.dataframe(experiment_rows, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Baseline Cases CSV",
                data=_rows_to_csv_text(experiment_rows),
                file_name="baseline_experiment_cases.csv",
                mime="text/csv",
            )
            st.download_button(
                "Download Baseline Aggregate JSON",
                data=json.dumps(experiment_aggregate, indent=2),
                file_name="baseline_experiment_aggregate.json",
                mime="application/json",
            )

    ablation_aggregate = st.session_state.get("ablation_aggregate")
    ablation_rows = st.session_state.get("ablation_rows")
    if ablation_aggregate:
        st.markdown("**Ablation Impact Summary**")
        st.plotly_chart(_ablation_current_chart(ablation_aggregate), use_container_width=True)
        with st.expander("Ablation Rows", expanded=False):
            st.dataframe(ablation_rows, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Ablation Cases CSV",
                data=_rows_to_csv_text(ablation_rows),
                file_name="ablation_cases.csv",
                mime="text/csv",
            )
            st.download_button(
                "Download Ablation Aggregate JSON",
                data=json.dumps(ablation_aggregate, indent=2),
                file_name="ablation_aggregate.json",
                mime="application/json",
            )

    if experiment_aggregate and ablation_aggregate:
        findings_markdown = build_markdown_summary_from_data(experiment_aggregate, ablation_aggregate)
        st.markdown("**Auto Findings Draft**")
        st.markdown(findings_markdown)
        st.download_button(
            "Download Findings Markdown",
            data=findings_markdown,
            file_name="findings_summary.md",
            mime="text/markdown",
        )


def _render_demo_package_builder(rows: list[dict[str, str]], data_path: str, radius_nm: float, config: ProjectConfig) -> None:
    st.subheader("Demo Package Builder")
    control_columns = st.columns([1, 1, 2])
    with control_columns[0]:
        top_n = st.slider("Package Top N", min_value=1, max_value=10, value=3, step=1)
    with control_columns[1]:
        min_targets = st.slider("Package Min Targets", min_value=1, max_value=10, value=1, step=1)
    with control_columns[2]:
        output_dir = st.text_input("Package output dir", value=str(Path("outputs/demo_package")))

    if st.button("Build Recommended Demo Package", use_container_width=True):
        try:
            manifest = build_recommended_demo_package(
                rows=rows,
                config=config,
                input_path=data_path,
                output_dir=output_dir,
                radius_nm=radius_nm,
                top_n=top_n,
                min_targets=min_targets,
            )
            st.session_state["demo_package_manifest"] = manifest
        except Exception as exc:  # pragma: no cover - UI guard
            st.error(f"Demo package build failed: {exc}")

    manifest = st.session_state.get("demo_package_manifest")
    if manifest:
        st.success(
            f"Saved {int(manifest['case_count'])} cases to `{manifest['output_dir']}`. "
            f"Index: `{manifest['index_path']}` | Master report: `{manifest['master_report_path']}`"
        )
        st.dataframe(manifest["cases"], use_container_width=True, hide_index=True)
        download_columns = st.columns(3)
        download_columns[0].download_button(
            "Download Package Manifest JSON",
            data=json.dumps(manifest, indent=2),
            file_name="demo_package_manifest.json",
            mime="application/json",
        )
        summary_path = Path(str(manifest["summary_path"]))
        if summary_path.exists():
            download_columns[1].download_button(
                "Download Package Summary Markdown",
                data=summary_path.read_text(encoding="utf-8"),
                file_name="demo_package_summary.md",
                mime="text/markdown",
            )
        master_findings_path = Path(str(manifest["master_findings_path"]))
        if master_findings_path.exists():
            download_columns[2].download_button(
                "Download Master Findings Markdown",
                data=master_findings_path.read_text(encoding="utf-8"),
                file_name="master_findings.md",
                mime="text/markdown",
            )

        st.markdown("**Paper Export**")
        if st.button("Refresh Paper Assets", use_container_width=False):
            try:
                refreshed = build_paper_assets_from_manifest(manifest, output_dir=manifest["output_dir"])
                manifest.update(refreshed)
                st.session_state["demo_package_manifest"] = manifest
                st.rerun()
            except Exception as exc:  # pragma: no cover - UI guard
                st.error(f"Paper asset refresh failed: {exc}")

        paper_columns = st.columns(4)
        for index, key in enumerate(
            [
                "paper_summary_note_en_path",
                "paper_summary_note_ko_path",
                "paper_results_section_en_path",
                "paper_results_section_ko_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    paper_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        draft_columns = st.columns(3)
        for index, key in enumerate(
            [
                "paper_full_draft_en_path",
                "paper_full_draft_ko_path",
                "paper_full_draft_tex_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    draft_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="application/x-tex" if target_path.suffix == ".tex" else "text/markdown",
                    )

        catalog_columns = st.columns(2)
        for index, key in enumerate(
            [
                "artifact_catalog_md_path",
                "artifact_catalog_ko_md_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    catalog_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        audience_columns = st.columns(2)
        for index, key in enumerate(
            [
                "audience_guide_path",
                "audience_guide_ko_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    audience_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        readiness_columns = st.columns(4)
        for index, key in enumerate(
            [
                "handoff_checklist_path",
                "handoff_checklist_ko_path",
                "deliverable_readiness_path",
                "deliverable_readiness_ko_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    readiness_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        review_columns = st.columns(4)
        for index, key in enumerate(
            [
                "paper_claim_matrix_md_path",
                "paper_claim_matrix_ko_md_path",
                "paper_reviewer_faq_path",
                "paper_reviewer_faq_ko_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    review_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        presentation_columns = st.columns(4)
        for index, key in enumerate(
            [
                "presentation_outline_path",
                "presentation_outline_ko_path",
                "demo_talk_track_path",
                "demo_talk_track_ko_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    presentation_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        defense_columns = st.columns(2)
        for index, key in enumerate(
            [
                "defense_packet_path",
                "defense_packet_ko_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    defense_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        portfolio_columns = st.columns(4)
        for index, key in enumerate(
            [
                "portfolio_case_study_path",
                "portfolio_case_study_ko_path",
                "interview_answer_bank_path",
                "interview_answer_bank_ko_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    portfolio_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        pack_columns = st.columns(4)
        for index, key in enumerate(
            [
                "advisor_review_pack_path",
                "reviewer_pack_path",
                "interview_pack_path",
                "portfolio_pack_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    pack_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        methods_columns = st.columns(4)
        for index, key in enumerate(
            [
                "paper_methods_section_en_path",
                "paper_methods_section_ko_path",
                "paper_discussion_section_en_path",
                "paper_discussion_section_ko_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    methods_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        appendix_columns = st.columns(2)
        for index, key in enumerate(
            [
                "paper_appendix_en_md_path",
                "paper_appendix_ko_md_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    appendix_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        caption_columns = st.columns(2)
        for index, key in enumerate(
            [
                "paper_figure_captions_en_path",
                "paper_figure_captions_ko_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    caption_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="text/markdown",
                    )

        latex_columns = st.columns(3)
        for index, key in enumerate(
            [
                "paper_case_tex_path",
                "paper_scenario_tex_path",
                "paper_ablation_tex_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    latex_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="application/x-tex",
                    )

        latex_section_columns = st.columns(2)
        for index, key in enumerate(
            [
                "paper_results_section_tex_path",
                "paper_methods_section_tex_path",
            ]
        ):
            if key in manifest:
                target_path = Path(str(manifest[key]))
                if target_path.exists():
                    latex_section_columns[index].download_button(
                        f"Download {target_path.stem}",
                        data=target_path.read_text(encoding="utf-8"),
                        file_name=target_path.name,
                        mime="application/x-tex",
                    )

        latex_discussion_columns = st.columns(1)
        key = "paper_discussion_section_tex_path"
        if key in manifest:
            target_path = Path(str(manifest[key]))
            if target_path.exists():
                latex_discussion_columns[0].download_button(
                    f"Download {target_path.stem}",
                    data=target_path.read_text(encoding="utf-8"),
                    file_name=target_path.name,
                    mime="application/x-tex",
                )


def _profile_bar_chart(title: str, x_values: list[str], y_values: list[float], color: str) -> go.Figure:
    figure = go.Figure(
        data=[go.Bar(x=x_values, y=y_values, marker_color=color)]
    )
    figure.update_layout(
        title=title,
        height=320,
        margin={"l": 10, "r": 10, "t": 36, "b": 10},
        paper_bgcolor="#fffdf8",
        plot_bgcolor="#fffdf8",
    )
    return figure


def _render_dataset_profile(rows: list[dict[str, str]]) -> None:
    profile = profile_curated_rows(rows, top_n=10)
    st.subheader("Dataset Profile")
    metric_columns = st.columns(5)
    metric_columns[0].metric("Rows", int(profile["row_count"]))
    metric_columns[1].metric("Unique Vessels", int(profile["unique_vessels"]))
    metric_columns[2].metric("Heading Coverage", f"{profile['heading_coverage_ratio']:.3f}")
    metric_columns[3].metric("Segment Breaks > 10 min", int(profile["segment_estimate_count_gap_gt_10min"]))
    speed_stats = profile["speed_stats"]
    metric_columns[4].metric("Median SOG", f"{speed_stats['median_sog']:.2f} kn")

    spatial = profile["spatial_extent"]
    st.caption(
        f"Time range: {profile['time_range']['start']} to {profile['time_range']['end']} | "
        f"Lat {spatial['min_lat']:.4f}..{spatial['max_lat']:.4f} | "
        f"Lon {spatial['min_lon']:.4f}..{spatial['max_lon']:.4f}"
    )

    chart_columns = st.columns(2)
    with chart_columns[0]:
        vessel_type_counts = profile["vessel_type_counts"]
        st.plotly_chart(
            _profile_bar_chart(
                "Vessel Type Counts",
                list(vessel_type_counts.keys()),
                list(vessel_type_counts.values()),
                "#0b6e63",
            ),
            use_container_width=True,
        )
    with chart_columns[1]:
        top_vessels = profile["top_vessels_by_rows"]
        st.plotly_chart(
            _profile_bar_chart(
                "Top MMSI by Row Count",
                [item["mmsi"] for item in top_vessels],
                [item["row_count"] for item in top_vessels],
                "#cf6d3f",
            ),
            use_container_width=True,
        )

    gap_stats = profile["gap_stats_seconds"]
    if gap_stats is not None:
        st.write(
            f"Gap stats (sec): min `{gap_stats['min']:.1f}`, median `{gap_stats['median']:.1f}`, "
            f"p90 `{gap_stats['p90']:.1f}`, max `{gap_stats['max']:.1f}`"
        )

    profile_json = json.dumps(profile, indent=2)
    profile_md = build_profile_markdown(profile)
    download_columns = st.columns(2)
    download_columns[0].download_button(
        "Download Profile JSON",
        data=profile_json,
        file_name="dataset_profile.json",
        mime="application/json",
    )
    download_columns[1].download_button(
        "Download Profile Markdown",
        data=profile_md,
        file_name="dataset_profile.md",
        mime="text/markdown",
    )


def _render_current_exports(snapshot: SnapshotInput, result: SnapshotResult, config: ProjectConfig) -> None:
    timestamp_safe = snapshot.timestamp.replace(":", "").replace("-", "").replace("T", "_").replace("Z", "Z")
    snapshot_json = json.dumps(asdict(snapshot), indent=2)
    result_json = json.dumps(asdict(result), indent=2)
    report_html = build_html_report_text(
        snapshot=snapshot,
        result=asdict(result),
        radius_nm=config.grid.radius_nm,
        cell_size_m=config.grid.cell_size_m,
        safe_threshold=config.thresholds.safe,
        warning_threshold=config.thresholds.warning,
    )
    current_scenario = next((scenario for scenario in result.scenarios if scenario.summary.scenario_name == "current"), result.scenarios[0])
    scenario_svg = build_scenario_svg_text(
        snapshot=snapshot,
        scenario=asdict(current_scenario),
        radius_nm=config.grid.radius_nm,
        cell_size_m=config.grid.cell_size_m,
        safe_threshold=config.thresholds.safe,
        warning_threshold=config.thresholds.warning,
    )
    all_scenario_svgs = build_all_scenario_svg_texts(
        snapshot=snapshot,
        result=asdict(result),
        radius_nm=config.grid.radius_nm,
        cell_size_m=config.grid.cell_size_m,
        safe_threshold=config.thresholds.safe,
        warning_threshold=config.thresholds.warning,
    )

    st.subheader("Current Exports")
    export_columns = st.columns(4)
    export_columns[0].download_button(
        "Download Snapshot JSON",
        data=snapshot_json,
        file_name=f"snapshot_{timestamp_safe}.json",
        mime="application/json",
    )
    export_columns[1].download_button(
        "Download Result JSON",
        data=result_json,
        file_name=f"result_{timestamp_safe}.json",
        mime="application/json",
    )
    export_columns[2].download_button(
        "Download HTML Report",
        data=report_html,
        file_name=f"report_{timestamp_safe}.html",
        mime="text/html",
    )
    export_columns[3].download_button(
        "Download Current SVG",
        data=scenario_svg,
        file_name=f"current_{timestamp_safe}.svg",
        mime="image/svg+xml",
    )
    scenario_columns = st.columns(max(1, len(all_scenario_svgs)))
    for column, (scenario_name, svg_text) in zip(scenario_columns, all_scenario_svgs.items(), strict=False):
        with column:
            st.download_button(
                f"Download {scenario_name.capitalize()} SVG",
                data=svg_text,
                file_name=f"{scenario_name}_{timestamp_safe}.svg",
                mime="image/svg+xml",
            )


def main() -> None:
    st.set_page_config(page_title="AIS Risk Mapping Dashboard", layout="wide")
    st.title("AIS Risk Mapping Dashboard")
    st.caption("Own-ship-centric spatial risk awareness tool for AIS-only decision support.")

    with st.sidebar:
        st.header("Inputs")
        config_path = st.text_input("Config path", value=str(DEFAULT_CONFIG))
        mode = st.radio("Input mode", ("Reconstructed CSV", "Snapshot JSON"), index=0)
        try:
            config = cached_load_config(config_path)
        except Exception as exc:  # pragma: no cover - UI guard
            st.error(f"Failed to load config: {exc}")
            st.stop()

        if mode == "Reconstructed CSV":
            if "analysis_csv_path" not in st.session_state:
                st.session_state["analysis_csv_path"] = _default_existing_path(DEFAULT_TRACKS, Path("outputs/sample_ais_curated.csv"))
            data_path = st.text_input("Curated/Tracks CSV path", key="analysis_csv_path")

            with st.expander("Data Prep Lab", expanded=False):
                raw_input_path = st.text_input("Raw CSV path", value=str(Path("examples/sample_ais.csv")))
                curated_output_path = st.text_input("Curated output path", value=str(Path("outputs/dashboard_curated.csv")))
                tracks_output_path = st.text_input("Tracks output path", value=str(Path("outputs/dashboard_tracks.csv")))
                ingestion_config_path = st.text_input("Ingestion config path", value="")
                ingestion_bundle_name = st.selectbox("Ingestion bundle", options=["none"] + list_ingestion_bundle_names(), index=0)
                source_preset = st.selectbox("Source preset", options=list_source_preset_names(), index=0)
                preset = get_source_preset(source_preset)
                st.caption(preset.description)
                if ingestion_config_path.strip():
                    try:
                        config_bundle = load_ingestion_bundle_config(ingestion_config_path)
                        st.caption(
                            f"Config `{config_bundle.name}`: source preset `{config_bundle.source_preset}`, "
                            f"default vessel types `{', '.join(config_bundle.vessel_types) or 'none'}`"
                        )
                    except Exception as exc:  # pragma: no cover - UI guard
                        st.warning(f"Failed to load ingestion config: {exc}")
                elif ingestion_bundle_name != "none":
                    bundle = get_ingestion_bundle(ingestion_bundle_name)
                    st.caption(
                        f"Bundle `{bundle.name}`: source preset `{bundle.source_preset}`, "
                        f"default vessel types `{', '.join(bundle.vessel_types)}`"
                    )
                st.caption("If both ingestion config path and bundle are set, the config path takes precedence.")
                filter_columns = st.columns(2)
                with filter_columns[0]:
                    min_lat_raw = st.text_input("Min lat", value="")
                    max_lat_raw = st.text_input("Max lat", value="")
                    start_time_raw = st.text_input("Start time", value="")
                    vessel_types_raw = st.text_input("Vessel types (standardized, comma-separated)", value="")
                with filter_columns[1]:
                    min_lon_raw = st.text_input("Min lon", value="")
                    max_lon_raw = st.text_input("Max lon", value="")
                    end_time_raw = st.text_input("End time", value="")
                    column_map_raw = st.text_area(
                        "Column overrides",
                        value="",
                        help="Optional. Format: mmsi=ShipId,timestamp=Event Time,lat=Y,lon=X,sog=Speed,cog=Course",
                    )
                track_columns = st.columns(3)
                split_gap_min = track_columns[0].number_input("Split gap min", min_value=1.0, max_value=120.0, value=10.0, step=1.0)
                max_interp_gap_min = track_columns[1].number_input("Max interp gap min", min_value=0.5, max_value=30.0, value=2.0, step=0.5)
                step_sec = track_columns[2].number_input("Interp step sec", min_value=10, max_value=300, value=30, step=10)
                schema_sample_size = st.number_input("Schema sample rows", min_value=5, max_value=500, value=50, step=5)
                workflow_columns = st.columns(3)
                workflow_output_dir = workflow_columns[0].text_input("Workflow output dir", value=str(Path("outputs/dashboard_workflow")))
                workflow_top_n = workflow_columns[1].number_input("Workflow top-N", min_value=1, max_value=10, value=3, step=1)
                workflow_min_targets = workflow_columns[2].number_input("Workflow min targets", min_value=1, max_value=10, value=1, step=1)

                action_columns = st.columns(3)
                if action_columns[0].button("Inspect Raw Schema", use_container_width=True):
                    try:
                        resolved_bundle = resolve_ingestion_bundle(
                            bundle_name=None if ingestion_bundle_name == "none" else ingestion_bundle_name,
                            config_path=_optional_str(ingestion_config_path),
                            source_preset_name=source_preset,
                            manual_column_map_text=column_map_raw,
                            vessel_types_text=vessel_types_raw,
                        )
                        st.session_state["schema_probe"] = inspect_csv_schema(
                            raw_input_path,
                            sample_size=int(schema_sample_size),
                            column_overrides=resolve_source_preset(
                                str(resolved_bundle["source_preset"]),
                                str(resolved_bundle["column_map_text"]),
                            ),
                        )
                    except Exception as exc:  # pragma: no cover - UI guard
                        st.error(f"Schema inspect failed: {exc}")

                if action_columns[1].button("Run Preprocess", use_container_width=True):
                    try:
                        resolved_bundle = resolve_ingestion_bundle(
                            bundle_name=None if ingestion_bundle_name == "none" else ingestion_bundle_name,
                            config_path=_optional_str(ingestion_config_path),
                            source_preset_name=source_preset,
                            manual_column_map_text=column_map_raw,
                            vessel_types_text=vessel_types_raw,
                        )
                        vessel_types = set(resolved_bundle["vessel_types"]) or None
                        stats = preprocess_ais_csv(
                            input_path=raw_input_path,
                            output_path=curated_output_path,
                            min_lat=_optional_float(min_lat_raw),
                            max_lat=_optional_float(max_lat_raw),
                            min_lon=_optional_float(min_lon_raw),
                            max_lon=_optional_float(max_lon_raw),
                            start_time=_optional_str(start_time_raw),
                            end_time=_optional_str(end_time_raw),
                            allowed_vessel_types=vessel_types,
                            column_overrides=resolve_source_preset(
                                str(resolved_bundle["source_preset"]),
                                str(resolved_bundle["column_map_text"]),
                            ),
                        )
                        st.session_state["preprocess_stats"] = stats
                        st.session_state["analysis_csv_path"] = curated_output_path
                        cached_load_rows.clear()
                        cached_rank_own_ship_candidates.clear()
                        st.rerun()
                    except Exception as exc:  # pragma: no cover - UI guard
                        st.error(f"Preprocess failed: {exc}")

                if action_columns[2].button("Run Reconstruction", use_container_width=True):
                    try:
                        stats = reconstruct_trajectory_csv(
                            input_path=st.session_state["analysis_csv_path"],
                            output_path=tracks_output_path,
                            split_gap_minutes=float(split_gap_min),
                            max_interp_gap_minutes=float(max_interp_gap_min),
                            step_seconds=int(step_sec),
                        )
                        st.session_state["trajectory_stats"] = stats
                        st.session_state["analysis_csv_path"] = tracks_output_path
                        cached_load_rows.clear()
                        cached_rank_own_ship_candidates.clear()
                        st.rerun()
                    except Exception as exc:  # pragma: no cover - UI guard
                        st.error(f"Trajectory reconstruction failed: {exc}")

                if st.button("Run Full Workflow", use_container_width=True):
                    try:
                        summary = run_ingestion_workflow(
                            input_path=raw_input_path,
                            output_dir=workflow_output_dir,
                            project_config_path=config_path,
                            ingestion_bundle_name=None if ingestion_bundle_name == "none" else ingestion_bundle_name,
                            ingestion_config_path=_optional_str(ingestion_config_path),
                            source_preset_name=source_preset,
                            manual_column_map_text=column_map_raw,
                            vessel_types_text=vessel_types_raw,
                            min_lat=_optional_float(min_lat_raw),
                            max_lat=_optional_float(max_lat_raw),
                            min_lon=_optional_float(min_lon_raw),
                            max_lon=_optional_float(max_lon_raw),
                            start_time=_optional_str(start_time_raw),
                            end_time=_optional_str(end_time_raw),
                            split_gap_minutes=float(split_gap_min),
                            max_interp_gap_minutes=float(max_interp_gap_min),
                            step_seconds=int(step_sec),
                            schema_sample_size=int(schema_sample_size),
                            radius_nm=float(config.grid.radius_nm),
                            top_n=int(workflow_top_n),
                            min_targets=int(workflow_min_targets),
                        )
                        st.session_state["workflow_summary"] = summary
                        st.session_state["analysis_csv_path"] = str(summary["tracks_csv_path"])
                        cached_load_rows.clear()
                        cached_rank_own_ship_candidates.clear()
                        st.rerun()
                    except Exception as exc:  # pragma: no cover - UI guard
                        st.error(f"Workflow execution failed: {exc}")

                preprocess_stats = st.session_state.get("preprocess_stats")
                if preprocess_stats:
                    st.write("Preprocess stats")
                    st.json(preprocess_stats, expanded=False)
                trajectory_stats = st.session_state.get("trajectory_stats")
                if trajectory_stats:
                    st.write("Trajectory stats")
                    st.json(trajectory_stats, expanded=False)
                schema_probe = st.session_state.get("schema_probe")
                if schema_probe:
                    st.write("Schema probe")
                    st.json(schema_probe, expanded=False)
                workflow_summary = st.session_state.get("workflow_summary")
                if workflow_summary:
                    st.write("Workflow summary")
                    st.json(workflow_summary, expanded=False)
                    workflow_download_columns = st.columns(2)
                    workflow_download_columns[0].download_button(
                        "Download Workflow Summary JSON",
                        data=Path(str(workflow_summary["summary_json_path"])).read_text(encoding="utf-8"),
                        file_name=Path(str(workflow_summary["summary_json_path"])).name,
                        mime="application/json",
                    )
                    workflow_download_columns[1].download_button(
                        "Download Workflow Summary Markdown",
                        data=Path(str(workflow_summary["summary_md_path"])).read_text(encoding="utf-8"),
                        file_name=Path(str(workflow_summary["summary_md_path"])).name,
                        mime="text/markdown",
                    )

            try:
                rows = cached_load_rows(data_path)
            except Exception as exc:  # pragma: no cover - UI guard
                st.error(f"Failed to load CSV rows: {exc}")
                st.stop()
            vessel_ids = sorted({row["mmsi"] for row in rows})
            if not vessel_ids:
                st.error("No vessels found in the selected CSV file.")
                st.stop()
            recommended_candidates = cached_rank_own_ship_candidates(
                data_path,
                config_path,
                radius_nm=float(config.grid.radius_nm),
                top_n=5,
                min_targets=1,
            )
            recommended_mmsi = str(recommended_candidates[0]["mmsi"]) if recommended_candidates else None
            default_mmsi = "440000001" if "440000001" in vessel_ids else recommended_mmsi or vessel_ids[0]
            current_mmsi = st.session_state.get("own_mmsi_select", default_mmsi)
            if current_mmsi not in vessel_ids:
                current_mmsi = default_mmsi
                st.session_state["own_mmsi_select"] = default_mmsi

            with st.expander("Own Ship Recommendation", expanded=False):
                st.caption("Continuity + nearby traffic + movement suitability. Reconstructed tracks are preferred.")
                if recommended_candidates:
                    top_recommendation = recommended_candidates[0]
                    st.info(
                        f"Top recommended MMSI: `{top_recommendation['mmsi']}` "
                        f"(score {float(top_recommendation['candidate_score']):.3f}, "
                        f"time `{top_recommendation.get('recommended_timestamp', '')}`)"
                    )
                    if st.button("Use Top Recommended MMSI", use_container_width=True):
                        st.session_state["own_mmsi_select"] = str(top_recommendation["mmsi"])
                        if top_recommendation.get("recommended_timestamp"):
                            st.session_state["timestamp_select"] = str(top_recommendation["recommended_timestamp"])
                        st.rerun()
                    recommendation_labels = [
                        (
                            f"{candidate['rank']}. {candidate['mmsi']} | "
                            f"{candidate.get('recommended_timestamp', '')} | "
                            f"risk {float(candidate.get('recommended_max_risk', 0.0)):.3f}"
                        )
                        for candidate in recommended_candidates
                    ]
                    selected_recommendation_index = st.selectbox(
                        "Recommendation bundle",
                        options=list(range(len(recommended_candidates))),
                        index=0,
                        format_func=lambda index: recommendation_labels[index],
                    )
                    if st.button("Use Selected Recommendation Bundle", use_container_width=True):
                        selected_recommendation = recommended_candidates[selected_recommendation_index]
                        st.session_state["own_mmsi_select"] = str(selected_recommendation["mmsi"])
                        if selected_recommendation.get("recommended_timestamp"):
                            st.session_state["timestamp_select"] = str(selected_recommendation["recommended_timestamp"])
                        st.rerun()
                    st.dataframe(_format_candidate_rows(recommended_candidates), use_container_width=True, hide_index=True)
                    st.download_button(
                        "Download Own Ship Candidates CSV",
                        data=_rows_to_csv_text(_format_candidate_rows(recommended_candidates)),
                        file_name="own_ship_candidates.csv",
                        mime="text/csv",
                    )
                else:
                    st.write("No candidate recommendations available for the selected dataset.")

            own_mmsi = st.selectbox("Own ship MMSI", vessel_ids, index=vessel_ids.index(current_mmsi), key="own_mmsi_select")
            candidate_times = sorted({row["timestamp"] for row in rows if row["mmsi"] == own_mmsi})
            if not candidate_times:
                st.error("No timestamps found for the selected own ship.")
                st.stop()
            default_time = "2026-03-07T09:00:00Z"
            current_timestamp = st.session_state.get("timestamp_select", default_time if default_time in candidate_times else candidate_times[0])
            if current_timestamp not in candidate_times:
                current_timestamp = default_time if default_time in candidate_times else candidate_times[0]
                st.session_state["timestamp_select"] = current_timestamp
            timestamp = st.selectbox("Timestamp", candidate_times, index=candidate_times.index(current_timestamp), key="timestamp_select")
            radius_nm = st.slider("Target radius (NM)", min_value=2.0, max_value=12.0, value=float(config.grid.radius_nm), step=0.5)
            try:
                snapshot = _build_snapshot_from_controls(rows, own_mmsi, timestamp, radius_nm)
            except Exception as exc:  # pragma: no cover - UI guard
                st.error(f"Failed to build snapshot: {exc}")
                st.stop()
        else:
            snapshot_path = st.text_input("Snapshot path", value=_default_existing_path(DEFAULT_SNAPSHOT, Path("examples/sample_snapshot.json")))
            try:
                snapshot = cached_load_snapshot(snapshot_path)
            except Exception as exc:  # pragma: no cover - UI guard
                st.error(f"Failed to load snapshot: {exc}")
                st.stop()
            radius_nm = float(config.grid.radius_nm)

        st.markdown("---")
        st.caption("Disclaimer")
        st.write("AIS-only, constant-velocity proxy. Not a collision-avoidance command and not a legal safety guarantee.")

    if mode == "Reconstructed CSV":
        _render_dataset_profile(rows)

    result = cached_run_snapshot(snapshot, config)

    st.subheader("Scenario Summary")
    _render_summary_cards(result)

    st.subheader("Scenario Comparison")
    scenario_controls = st.columns([2, 1])
    with scenario_controls[0]:
        view_mode = st.radio("Scenario View Mode", ("Local Frame", "Geo Map"), horizontal=True)
    with scenario_controls[1]:
        show_contours = st.checkbox("Show Contours", value=True)
    scenario_columns = st.columns(len(result.scenarios))
    for column, scenario in zip(scenario_columns, result.scenarios, strict=True):
        with column:
            figure = (
                _scenario_figure(snapshot, scenario, config, show_contours=show_contours)
                if view_mode == "Local Frame"
                else _scenario_map_figure(snapshot, scenario, config, show_contours=show_contours)
            )
            st.plotly_chart(figure, use_container_width=True)
            st.write(
                f"Top risk sector: `{scenario.summary.dominant_sector}` | "
                f"Targets: `{scenario.summary.target_count}` | "
                f"Mean risk: `{scenario.summary.mean_risk:.3f}`"
            )

    st.subheader("Top Contributing Vessels")
    tab_labels = [scenario.summary.scenario_name for scenario in result.scenarios]
    for tab, scenario in zip(st.tabs(tab_labels), result.scenarios, strict=True):
        with tab:
            st.dataframe(_top_vessel_rows(scenario.top_vessels), use_container_width=True, hide_index=True)
            if scenario.top_vessels:
                top = scenario.top_vessels[0]
                st.info(
                    f"{top.mmsi} is the strongest contributor in `{scenario.summary.scenario_name}` "
                    f"with score {top.score:.3f}, encounter `{top.encounter_type}`, "
                    f"TCPA {top.tcpa_min:.1f} min, DCPA {top.dcpa_nm:.2f} NM."
                )

    _render_current_exports(snapshot, result, config)

    st.subheader("Raw Snapshot State")
    state_columns = st.columns(2)
    with state_columns[0]:
        st.markdown("**Own Ship**")
        st.json(asdict(snapshot.own_ship), expanded=False)
    with state_columns[1]:
        st.markdown("**Targets**")
        st.json([asdict(target) for target in snapshot.targets], expanded=False)

    if mode == "Reconstructed CSV":
        st.subheader("Case Candidates")
        with st.expander("Rank top risk timestamps for the selected own ship", expanded=False):
            top_n = st.slider("Top N", min_value=3, max_value=20, value=5, step=1)
            min_targets = st.slider("Minimum targets", min_value=1, max_value=10, value=1, step=1)
            if st.button("Mine Cases", use_container_width=False):
                case_rows = mine_cases_from_curated_rows(
                    rows=rows,
                    own_mmsi=own_mmsi,
                    config=config,
                    radius_nm=radius_nm,
                    top_n=top_n,
                    min_targets=min_targets,
                )
                st.dataframe(case_rows, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download Case Candidates CSV",
                    data=_rows_to_csv_text(case_rows),
                    file_name="case_candidates.csv",
                    mime="text/csv",
                )

        _render_demo_package_builder(rows=rows, data_path=data_path, radius_nm=radius_nm, config=config)
        _render_experiment_lab(rows=rows, own_mmsi=own_mmsi, radius_nm=radius_nm, config=config)


if __name__ == "__main__":
    main()
