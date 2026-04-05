from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path

from .experiments import build_ablation_settings
from .models import ProjectConfig, SnapshotInput, SnapshotResult
from .pipeline import run_snapshot
from .summary import build_markdown_summary_from_data

DEFAULT_PACKAGE_ABLATIONS = ("bearing", "density", "time_decay", "spatial_kernel")


def _aggregate_baseline_results(results: list[SnapshotResult], radius_nm: float) -> dict[str, object]:
    scenario_buckets: dict[str, list[dict[str, float]]] = {}
    sector_counter: Counter[str] = Counter()

    for result in results:
        current = next(
            (scenario for scenario in result.scenarios if scenario.summary.scenario_name == "current"),
            result.scenarios[0],
        )
        sector_counter[current.summary.dominant_sector] += 1
        for scenario in result.scenarios:
            scenario_buckets.setdefault(scenario.summary.scenario_name, []).append(
                {
                    "max_risk": scenario.summary.max_risk,
                    "mean_risk": scenario.summary.mean_risk,
                    "warning_area_nm2": scenario.summary.warning_area_nm2,
                    "delta_max_risk_vs_current": scenario.summary.max_risk - current.summary.max_risk,
                    "delta_warning_area_vs_current": scenario.summary.warning_area_nm2 - current.summary.warning_area_nm2,
                }
            )

    aggregate: dict[str, object] = {
        "case_count": len(results),
        "own_mmsi": "recommended_bundle_set",
        "radius_nm": radius_nm,
        "dominant_sector_counts_current": dict(sector_counter),
        "scenario_averages": {},
    }
    for scenario_name, values in scenario_buckets.items():
        count = len(values)
        aggregate["scenario_averages"][scenario_name] = {
            "avg_max_risk": sum(item["max_risk"] for item in values) / count if count else 0.0,
            "avg_mean_risk": sum(item["mean_risk"] for item in values) / count if count else 0.0,
            "avg_warning_area_nm2": sum(item["warning_area_nm2"] for item in values) / count if count else 0.0,
            "avg_delta_max_risk_vs_current": sum(item["delta_max_risk_vs_current"] for item in values) / count if count else 0.0,
            "avg_delta_warning_area_vs_current": sum(item["delta_warning_area_vs_current"] for item in values) / count if count else 0.0,
        }
    return aggregate


def _aggregate_ablation_results(
    snapshots: list[SnapshotInput],
    baseline_results: list[SnapshotResult],
    config: ProjectConfig,
    radius_nm: float,
    ablation_names: list[str],
) -> dict[str, object]:
    settings_list = [("baseline", None)] + [
        (build_ablation_settings(name).label, build_ablation_settings(name))
        for name in ablation_names
    ]
    aggregates: dict[str, dict[str, list[dict[str, float]]]] = {}

    for snapshot, baseline_result in zip(snapshots, baseline_results, strict=True):
        baseline_by_scenario = {
            scenario.summary.scenario_name: scenario.summary
            for scenario in baseline_result.scenarios
        }
        for label, settings in settings_list:
            result = baseline_result if settings is None else run_snapshot(snapshot, config, ablation=settings)
            for scenario in result.scenarios:
                baseline_summary = baseline_by_scenario[scenario.summary.scenario_name]
                aggregates.setdefault(label, {}).setdefault(scenario.summary.scenario_name, []).append(
                    {
                        "max_risk": scenario.summary.max_risk,
                        "mean_risk": scenario.summary.mean_risk,
                        "warning_area_nm2": scenario.summary.warning_area_nm2,
                        "delta_max_risk_vs_baseline": scenario.summary.max_risk - baseline_summary.max_risk,
                        "delta_warning_area_vs_baseline": scenario.summary.warning_area_nm2 - baseline_summary.warning_area_nm2,
                    }
                )

    payload: dict[str, object] = {
        "case_count": len(snapshots),
        "own_mmsi": "recommended_bundle_set",
        "radius_nm": radius_nm,
        "ablations": {},
    }
    for label, scenario_map in aggregates.items():
        payload["ablations"][label] = {}
        for scenario_name, values in scenario_map.items():
            count = len(values)
            payload["ablations"][label][scenario_name] = {
                "avg_max_risk": sum(item["max_risk"] for item in values) / count if count else 0.0,
                "avg_mean_risk": sum(item["mean_risk"] for item in values) / count if count else 0.0,
                "avg_warning_area_nm2": sum(item["warning_area_nm2"] for item in values) / count if count else 0.0,
                "avg_delta_max_risk_vs_baseline": sum(item["delta_max_risk_vs_baseline"] for item in values) / count if count else 0.0,
                "avg_delta_warning_area_vs_baseline": sum(item["delta_warning_area_vs_baseline"] for item in values) / count if count else 0.0,
            }
    return payload


def _inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)


def _markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    html_parts: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped == "":
            index += 1
            continue
        if stripped.startswith("## "):
            html_parts.append(f"<h2>{_inline_markdown(stripped[3:])}</h2>")
            index += 1
            continue
        if stripped.startswith("# "):
            html_parts.append(f"<h1>{_inline_markdown(stripped[2:])}</h1>")
            index += 1
            continue
        if stripped.startswith("- "):
            items: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append(f"<li>{_inline_markdown(lines[index].strip()[2:])}</li>")
                index += 1
            html_parts.append(f"<ul>{''.join(items)}</ul>")
            continue
        if stripped.startswith("|"):
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            if len(table_lines) >= 2:
                header_cells = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
                body_lines = table_lines[2:]
                rows = []
                for row_line in body_lines:
                    cells = [cell.strip() for cell in row_line.strip("|").split("|")]
                    rows.append("<tr>" + "".join(f"<td>{_inline_markdown(cell)}</td>" for cell in cells) + "</tr>")
                html_parts.append(
                    "<table><thead><tr>"
                    + "".join(f"<th>{_inline_markdown(cell)}</th>" for cell in header_cells)
                    + "</tr></thead><tbody>"
                    + "".join(rows)
                    + "</tbody></table>"
                )
            continue
        html_parts.append(f"<p>{_inline_markdown(stripped)}</p>")
        index += 1
    return "".join(html_parts)


def build_master_report_text(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
    findings_markdown: str,
) -> str:
    case_rows = "".join(
        "<tr>"
        f"<td>{int(case['rank'])}</td>"
        f"<td>{html.escape(str(case['own_mmsi']))}</td>"
        f"<td>{html.escape(str(case['timestamp']))}</td>"
        f"<td>{float(case['candidate_score']):.3f}</td>"
        f"<td>{float(case['current_max_risk']):.3f}</td>"
        f"<td>{int(case['target_count'])}</td>"
        f"<td>{html.escape(str(case['dominant_sector']))}</td>"
        f"<td><img class=\"thumb\" src=\"{html.escape(str(case['image_relpath']))}\" alt=\"risk snapshot\" /></td>"
        f"<td><a href=\"{html.escape(str(case['report_relpath']))}\">report</a></td>"
        "</tr>"
        for case in manifest["cases"]
    )
    findings_html = _markdown_to_html(findings_markdown)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(str(manifest["package_name"]))} Master Report</title>
  <style>
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: radial-gradient(circle at top left, #faf6ef 0%, #f2ebdd 48%, #e7dfd0 100%);
      color: #1d2b2a;
    }}
    .page {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px;
    }}
    .hero, .panel {{
      background: rgba(255, 253, 248, 0.95);
      border: 1px solid #d7cec0;
      border-radius: 18px;
      padding: 22px;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 34px;
    }}
    .sub {{
      color: #5f6a65;
      margin-bottom: 8px;
    }}
    .links {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 12px;
    }}
    .links a {{
      color: #0b6e63;
      text-decoration: none;
      font-weight: 600;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }}
    th, td {{
      border-bottom: 1px solid #e4dacb;
      text-align: left;
      padding: 10px 8px;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      color: #5f6a65;
      font-weight: 600;
    }}
    .thumb {{
      width: 120px;
      height: 120px;
      object-fit: contain;
      background: #eef6f2;
      border: 1px solid #d7cec0;
      border-radius: 10px;
      padding: 6px;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 24px;
    }}
    ul {{
      margin: 10px 0 14px 18px;
    }}
    p {{
      line-height: 1.55;
    }}
    code {{
      background: #f3ece1;
      border-radius: 6px;
      padding: 1px 6px;
      font-size: 0.95em;
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>{html.escape(str(manifest["package_name"]))} Master Report</h1>
      <div class="sub">recommended bundle count: {int(manifest["case_count"])}</div>
      <div class="sub">radius: {float(manifest["radius_nm"]):.1f} NM | source: {html.escape(str(manifest["input_path"]))}</div>
      <div class="sub">AIS-only decision-support baseline. Not a collision-avoidance command or safety guarantee.</div>
      <div class="links">
        <a href="index.html">demo index</a>
        <a href="summary.md">package summary</a>
        <a href="master_findings.md">master findings</a>
        <a href="package_experiment_aggregate.json">experiment aggregate</a>
        <a href="package_ablation_aggregate.json">ablation aggregate</a>
      </div>
    </section>
    <section class="panel">
      <h2>Recommended Cases</h2>
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Own MMSI</th>
            <th>Timestamp</th>
            <th>Candidate Score</th>
            <th>Current Max Risk</th>
            <th>Targets</th>
            <th>Dominant Sector</th>
            <th>Snapshot</th>
            <th>Report</th>
          </tr>
        </thead>
        <tbody>{case_rows}</tbody>
      </table>
    </section>
    <section class="panel">
      {findings_html}
    </section>
  </div>
</body>
</html>
"""


def build_master_report_assets(
    manifest: dict[str, object],
    snapshots: list[SnapshotInput],
    baseline_results: list[SnapshotResult],
    config: ProjectConfig,
    output_dir: str | Path,
    radius_nm: float,
    ablation_names: tuple[str, ...] = DEFAULT_PACKAGE_ABLATIONS,
) -> dict[str, str]:
    output_root = Path(output_dir)
    experiment_data = _aggregate_baseline_results(baseline_results, radius_nm=radius_nm)
    ablation_data = _aggregate_ablation_results(
        snapshots=snapshots,
        baseline_results=baseline_results,
        config=config,
        radius_nm=radius_nm,
        ablation_names=list(ablation_names),
    )
    findings_markdown = build_markdown_summary_from_data(experiment_data, ablation_data)

    experiment_path = output_root / "package_experiment_aggregate.json"
    ablation_path = output_root / "package_ablation_aggregate.json"
    findings_path = output_root / "master_findings.md"
    report_path = output_root / "master_report.html"
    experiment_path.write_text(json.dumps(experiment_data, indent=2), encoding="utf-8")
    ablation_path.write_text(json.dumps(ablation_data, indent=2), encoding="utf-8")
    findings_path.write_text(findings_markdown, encoding="utf-8")
    report_path.write_text(
        build_master_report_text(manifest, experiment_data, ablation_data, findings_markdown),
        encoding="utf-8",
    )
    return {
        "experiment_aggregate_path": str(experiment_path),
        "ablation_aggregate_path": str(ablation_path),
        "master_findings_path": str(findings_path),
        "master_report_path": str(report_path),
    }
