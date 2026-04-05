from __future__ import annotations

import html
import json
from dataclasses import asdict
from pathlib import Path

from .csv_tools import build_snapshot_from_curated_rows, load_curated_csv_rows
from .io import save_result, save_snapshot
from .master_report import build_master_report_assets
from .models import ProjectConfig
from .own_ship_candidates import recommend_own_ship_candidates_rows
from .paper_assets import build_paper_assets_from_manifest
from .pipeline import run_snapshot
from .report import build_html_report_text, save_all_scenario_svgs


def _safe_timestamp_label(timestamp: str) -> str:
    return timestamp.replace(":", "").replace("-", "").replace("T", "_").replace("Z", "Z")


def _case_directory_name(rank: int, mmsi: str, timestamp: str) -> str:
    return f"rank_{rank:02d}_{mmsi}_{_safe_timestamp_label(timestamp)}"


def _preview_line(path: str | Path) -> str:
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return ""


def _build_package_index_html(manifest: dict[str, object]) -> str:
    preview_summary_en = ""
    preview_summary_ko = ""
    preview_results_en = ""
    preview_results_ko = ""
    preview_methods_en = ""
    preview_methods_ko = ""
    preview_discussion_en = ""
    preview_discussion_ko = ""
    if "paper_summary_note_en_path" in manifest:
        preview_summary_en = _preview_line(str(manifest["paper_summary_note_en_path"]))
    if "paper_summary_note_ko_path" in manifest:
        preview_summary_ko = _preview_line(str(manifest["paper_summary_note_ko_path"]))
    if "paper_results_section_en_path" in manifest:
        preview_results_en = _preview_line(str(manifest["paper_results_section_en_path"]))
    if "paper_results_section_ko_path" in manifest:
        preview_results_ko = _preview_line(str(manifest["paper_results_section_ko_path"]))
    if "paper_methods_section_en_path" in manifest:
        preview_methods_en = _preview_line(str(manifest["paper_methods_section_en_path"]))
    if "paper_methods_section_ko_path" in manifest:
        preview_methods_ko = _preview_line(str(manifest["paper_methods_section_ko_path"]))
    if "paper_discussion_section_en_path" in manifest:
        preview_discussion_en = _preview_line(str(manifest["paper_discussion_section_en_path"]))
    if "paper_discussion_section_ko_path" in manifest:
        preview_discussion_ko = _preview_line(str(manifest["paper_discussion_section_ko_path"]))
    cards = []
    for case in manifest["cases"]:
        figure_links = "".join(
            f'<a href="{html.escape(str(relpath))}">{html.escape(name)}</a>'
            for name, relpath in case["scenario_image_relpaths"].items()
        )
        cards.append(
            '<article class="case-card">'
            f'<div class="rank">#{int(case["rank"])}</div>'
            f'<h2>{html.escape(str(case["own_mmsi"]))}</h2>'
            f'<div class="meta">{html.escape(str(case["timestamp"]))}</div>'
            f'<img class="thumb" src="{html.escape(str(case["image_relpath"]))}" alt="risk snapshot for {html.escape(str(case["own_mmsi"]))}" />'
            f'<div class="metrics">'
            f'<span>candidate {float(case["candidate_score"]):.3f}</span>'
            f'<span>max risk {float(case["current_max_risk"]):.3f}</span>'
            f'<span>targets {int(case["target_count"])}</span>'
            f'</div>'
            f'<div class="sector">dominant sector: {html.escape(str(case["dominant_sector"]))}</div>'
            f'<div class="links">'
            f'<a href="{html.escape(str(case["report_relpath"]))}">report</a>'
            f'<a href="{html.escape(str(case["snapshot_relpath"]))}">snapshot</a>'
            f'<a href="{html.escape(str(case["result_relpath"]))}">result</a>'
            f"{figure_links}"
            f'</div>'
            "</article>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(str(manifest["package_name"]))}</title>
  <style>
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(160deg, #f7f2e7, #ece4d6);
      color: #1d2b2a;
    }}
    .page {{
      max-width: 1160px;
      margin: 0 auto;
      padding: 28px;
    }}
    .hero {{
      background: rgba(255, 253, 248, 0.92);
      border: 1px solid #d7cec0;
      border-radius: 18px;
      padding: 24px;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 32px;
    }}
    .sub {{
      color: #5f6a65;
      margin-bottom: 10px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 16px;
    }}
    .preview {{
      background: rgba(255, 253, 248, 0.96);
      border: 1px solid #d7cec0;
      border-radius: 16px;
      padding: 18px;
      margin-bottom: 18px;
    }}
    .case-card {{
      background: rgba(255, 253, 248, 0.96);
      border: 1px solid #d7cec0;
      border-radius: 16px;
      padding: 18px;
    }}
    .rank {{
      display: inline-block;
      padding: 4px 8px;
      border-radius: 999px;
      background: #0b6e63;
      color: #fff;
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .meta, .sector {{
      color: #5f6a65;
      font-size: 14px;
      margin-bottom: 10px;
    }}
    .thumb {{
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: contain;
      background: #eef6f2;
      border: 1px solid #d7cec0;
      border-radius: 12px;
      margin-bottom: 12px;
      padding: 8px;
    }}
    .metrics {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
    }}
    .metrics span {{
      background: #f2ebe0;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 13px;
    }}
    .links {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .links a {{
      color: #0b6e63;
      text-decoration: none;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>{html.escape(str(manifest["package_name"]))}</h1>
      <div class="sub">source: {html.escape(str(manifest["input_path"]))}</div>
      <div class="sub">case count: {int(manifest["case_count"])} | radius: {float(manifest["radius_nm"]):.1f} NM</div>
      <div class="sub">AIS-only decision-support demo package. Not a collision-avoidance command.</div>
      <div class="links">
        <a href="figure_bundle.html">figure bundle</a>
        <a href="figure_bundle.md">figure summary</a>
        <a href="figure_bundle_manifest.json">figure manifest</a>
        <a href="artifact_catalog.md">artifact catalog</a>
        <a href="artifact_catalog_ko.md">artifact catalog (KO)</a>
        <a href="audience_guide.md">audience guide</a>
        <a href="audience_guide_ko.md">audience guide (KO)</a>
        <a href="handoff_checklist.md">handoff checklist</a>
        <a href="handoff_checklist_ko.md">handoff checklist (KO)</a>
        <a href="deliverable_readiness.md">deliverable readiness</a>
        <a href="deliverable_readiness_ko.md">deliverable readiness (KO)</a>
        <a href="paper_summary_note.md">paper summary</a>
        <a href="paper_full_draft.md">paper full draft</a>
        <a href="paper_full_draft_ko.md">paper full draft (KO)</a>
        <a href="paper_full_draft.tex">paper full draft (LaTeX)</a>
        <a href="paper_claim_matrix.md">paper claim matrix</a>
        <a href="paper_claim_matrix_ko.md">paper claim matrix (KO)</a>
        <a href="paper_reviewer_faq.md">paper reviewer faq</a>
        <a href="paper_reviewer_faq_ko.md">paper reviewer faq (KO)</a>
        <a href="presentation_outline.md">presentation outline</a>
        <a href="presentation_outline_ko.md">presentation outline (KO)</a>
        <a href="demo_talk_track.md">demo talk track</a>
        <a href="demo_talk_track_ko.md">demo talk track (KO)</a>
        <a href="defense_packet.md">defense packet</a>
        <a href="defense_packet_ko.md">defense packet (KO)</a>
        <a href="portfolio_case_study.md">portfolio case study</a>
        <a href="portfolio_case_study_ko.md">portfolio case study (KO)</a>
        <a href="interview_answer_bank.md">interview answer bank</a>
        <a href="interview_answer_bank_ko.md">interview answer bank (KO)</a>
        <a href="advisor_review_pack.md">advisor review pack</a>
        <a href="reviewer_pack.md">reviewer pack</a>
        <a href="interview_pack.md">interview pack</a>
        <a href="portfolio_pack.md">portfolio pack</a>
        <a href="paper_summary_note_en.md">paper summary (EN)</a>
        <a href="paper_summary_note_ko.md">paper summary (KO)</a>
        <a href="paper_results_section.md">paper results</a>
        <a href="paper_results_section_en.md">paper results (EN)</a>
        <a href="paper_results_section_ko.md">paper results (KO)</a>
        <a href="paper_results_section.tex">paper results (LaTeX)</a>
        <a href="paper_methods_section.md">paper methods</a>
        <a href="paper_methods_section_en.md">paper methods (EN)</a>
        <a href="paper_methods_section_ko.md">paper methods (KO)</a>
        <a href="paper_methods_section.tex">paper methods (LaTeX)</a>
        <a href="paper_discussion_section.md">paper discussion</a>
        <a href="paper_discussion_section_en.md">paper discussion (EN)</a>
        <a href="paper_discussion_section_ko.md">paper discussion (KO)</a>
        <a href="paper_discussion_section.tex">paper discussion (LaTeX)</a>
        <a href="paper_figure_captions.md">paper captions</a>
        <a href="paper_figure_captions_ko.md">paper captions (KO)</a>
        <a href="paper_scenario_table.tex">paper tables (LaTeX)</a>
        <a href="paper_appendix.md">paper appendix</a>
        <a href="paper_appendix_ko.md">paper appendix (KO)</a>
        <a href="paper_appendix.tex">paper appendix (LaTeX)</a>
      </div>
    </section>
    <section class="preview">
      <h2>Paper Preview</h2>
      <div class="sub">EN: {html.escape(preview_summary_en)}</div>
      <div class="sub">KO: {html.escape(preview_summary_ko)}</div>
      <div class="sub">Results EN: {html.escape(preview_results_en)}</div>
      <div class="sub">Results KO: {html.escape(preview_results_ko)}</div>
      <div class="sub">Methods EN: {html.escape(preview_methods_en)}</div>
      <div class="sub">Methods KO: {html.escape(preview_methods_ko)}</div>
      <div class="sub">Discussion EN: {html.escape(preview_discussion_en)}</div>
      <div class="sub">Discussion KO: {html.escape(preview_discussion_ko)}</div>
    </section>
    <section class="grid">
      {''.join(cards)}
    </section>
  </div>
</body>
</html>
"""


def _build_package_summary_markdown(manifest: dict[str, object]) -> str:
    rows = "\n".join(
        (
            f"| {int(case['rank'])} | {case['own_mmsi']} | {case['timestamp']} | "
            f"{float(case['candidate_score']):.3f} | {float(case['current_max_risk']):.3f} | "
            f"{int(case['target_count'])} | {case['dominant_sector']} | {case['report_relpath']} |"
        )
        for case in manifest["cases"]
    ) or "| - | - | - | - | - | - | - | - |"
    return f"""# {manifest["package_name"]}

- Source CSV: `{manifest["input_path"]}`
- Case count: `{manifest["case_count"]}`
- Radius (NM): `{manifest["radius_nm"]:.1f}`

| Rank | Own MMSI | Timestamp | Candidate Score | Current Max Risk | Targets | Dominant Sector | Report |
|---|---|---|---:|---:|---:|---|---|
{rows}
"""


def _build_figure_bundle_manifest(manifest: dict[str, object]) -> dict[str, object]:
    return {
        "package_name": str(manifest["package_name"]),
        "case_count": int(manifest["case_count"]),
        "figure_count": sum(len(case["scenario_image_relpaths"]) for case in manifest["cases"]),
        "cases": [
            {
                "rank": int(case["rank"]),
                "own_mmsi": str(case["own_mmsi"]),
                "timestamp": str(case["timestamp"]),
                "dominant_sector": str(case["dominant_sector"]),
                "scenario_image_relpaths": dict(case["scenario_image_relpaths"]),
            }
            for case in manifest["cases"]
        ],
    }


def _build_figure_bundle_markdown(manifest: dict[str, object]) -> str:
    lines = [
        f"# {manifest['package_name']} Figure Bundle",
        "",
        f"- Case count: `{manifest['case_count']}`",
        f"- Radius (NM): `{manifest['radius_nm']:.1f}`",
        "",
    ]
    for case in manifest["cases"]:
        lines.append(f"## Rank {int(case['rank'])} | MMSI {case['own_mmsi']} | {case['timestamp']}")
        lines.append("")
        lines.append(f"- Dominant sector: `{case['dominant_sector']}`")
        lines.append(f"- Current max risk: `{float(case['current_max_risk']):.3f}`")
        lines.append("")
        lines.append("| Scenario | SVG |")
        lines.append("|---|---|")
        for scenario_name, relpath in case["scenario_image_relpaths"].items():
            lines.append(f"| {scenario_name} | {relpath} |")
        lines.append("")
    return "\n".join(lines)


def _build_figure_bundle_html(manifest: dict[str, object]) -> str:
    sections = []
    for case in manifest["cases"]:
        figure_cards = []
        for scenario_name, relpath in case["scenario_image_relpaths"].items():
            figure_cards.append(
                '<article class="figure-card">'
                f'<div class="scenario-name">{html.escape(str(scenario_name))}</div>'
                f'<img src="{html.escape(str(relpath))}" alt="{html.escape(str(case["own_mmsi"]))} {html.escape(str(scenario_name))} scenario" />'
                f'<a href="{html.escape(str(relpath))}">open svg</a>'
                "</article>"
            )
        sections.append(
            '<section class="case-section">'
            f'<h2>#{int(case["rank"])} | {html.escape(str(case["own_mmsi"]))} | {html.escape(str(case["timestamp"]))}</h2>'
            f'<div class="meta">dominant sector {html.escape(str(case["dominant_sector"]))} | max risk {float(case["current_max_risk"]):.3f}</div>'
            f'<div class="figure-grid">{"".join(figure_cards)}</div>'
            "</section>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(str(manifest["package_name"]))} Figure Bundle</title>
  <style>
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background: linear-gradient(180deg, #f7f2e7 0%, #ece4d6 100%);
      color: #1d2b2a;
    }}
    .page {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 28px;
    }}
    .hero, .case-section {{
      background: rgba(255, 253, 248, 0.95);
      border: 1px solid #d7cec0;
      border-radius: 18px;
      padding: 22px;
      margin-bottom: 18px;
    }}
    .sub, .meta {{
      color: #5f6a65;
    }}
    .figure-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
      margin-top: 14px;
    }}
    .figure-card {{
      background: #fffdf8;
      border: 1px solid #d7cec0;
      border-radius: 14px;
      padding: 12px;
    }}
    .figure-card img {{
      width: 100%;
      aspect-ratio: 1 / 1;
      object-fit: contain;
      background: #eef6f2;
      border: 1px solid #d7cec0;
      border-radius: 10px;
      padding: 6px;
      margin-bottom: 10px;
    }}
    .scenario-name {{
      text-transform: capitalize;
      font-weight: 700;
      margin-bottom: 8px;
    }}
    a {{
      color: #0b6e63;
      text-decoration: none;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>{html.escape(str(manifest["package_name"]))} Figure Bundle</h1>
      <div class="sub">Static SVG set for presentation, portfolio, and paper draft figures.</div>
      <div class="sub">AIS-only visualization outputs. Not a collision-avoidance command.</div>
    </section>
    {''.join(sections)}
  </div>
</body>
</html>
"""


def _save_figure_bundle_assets(output_root: Path, manifest: dict[str, object]) -> dict[str, str]:
    figure_manifest = _build_figure_bundle_manifest(manifest)
    figure_manifest_path = output_root / "figure_bundle_manifest.json"
    figure_bundle_html_path = output_root / "figure_bundle.html"
    figure_bundle_md_path = output_root / "figure_bundle.md"
    figure_manifest_path.write_text(json.dumps(figure_manifest, indent=2), encoding="utf-8")
    figure_bundle_html_path.write_text(_build_figure_bundle_html(manifest), encoding="utf-8")
    figure_bundle_md_path.write_text(_build_figure_bundle_markdown(manifest), encoding="utf-8")
    return {
        "figure_bundle_manifest_path": str(figure_manifest_path),
        "figure_bundle_html_path": str(figure_bundle_html_path),
        "figure_bundle_md_path": str(figure_bundle_md_path),
    }


def build_recommended_demo_package(
    rows: list[dict[str, str]],
    config: ProjectConfig,
    input_path: str | Path,
    output_dir: str | Path,
    radius_nm: float,
    top_n: int = 3,
    min_targets: int = 1,
) -> dict[str, object]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    recommendations = recommend_own_ship_candidates_rows(
        rows=rows,
        config=config,
        radius_nm=radius_nm,
        top_n=top_n,
        min_targets=min_targets,
    )

    case_entries: list[dict[str, object]] = []
    package_snapshots: list = []
    package_results: list = []
    for recommendation in recommendations:
        timestamp = str(recommendation["recommended_timestamp"])
        own_mmsi = str(recommendation["mmsi"])
        case_dir = output_root / _case_directory_name(int(recommendation["rank"]), own_mmsi, timestamp)
        case_dir.mkdir(parents=True, exist_ok=True)

        snapshot = build_snapshot_from_curated_rows(
            rows=rows,
            own_mmsi=own_mmsi,
            timestamp=timestamp,
            radius_nm=radius_nm,
        )
        result = run_snapshot(snapshot, config)
        current = next(
            (scenario for scenario in result.scenarios if scenario.summary.scenario_name == "current"),
            result.scenarios[0],
        )

        snapshot_path = case_dir / "snapshot.json"
        result_path = case_dir / "result.json"
        report_path = case_dir / "report.html"
        save_snapshot(snapshot_path, snapshot)
        save_result(result_path, result)
        report_path.write_text(
            build_html_report_text(
                snapshot=snapshot,
                result=asdict(result),
                radius_nm=config.grid.radius_nm,
                cell_size_m=config.grid.cell_size_m,
                safe_threshold=config.thresholds.safe,
                warning_threshold=config.thresholds.warning,
            ),
            encoding="utf-8",
        )
        scenario_svg_paths = save_all_scenario_svgs(
            output_dir=case_dir,
            snapshot=snapshot,
            result=asdict(result),
            radius_nm=config.grid.radius_nm,
            cell_size_m=config.grid.cell_size_m,
            safe_threshold=config.thresholds.safe,
            warning_threshold=config.thresholds.warning,
        )
        package_snapshots.append(snapshot)
        package_results.append(result)

        case_entries.append(
            {
                "rank": int(recommendation["rank"]),
                "own_mmsi": own_mmsi,
                "timestamp": timestamp,
                "candidate_score": float(recommendation["candidate_score"]),
                "recommendation_source": str(recommendation["recommendation_source"]),
                "target_count": int(current.summary.target_count),
                "current_max_risk": float(current.summary.max_risk),
                "current_warning_area_nm2": float(current.summary.warning_area_nm2),
                "dominant_sector": str(current.summary.dominant_sector),
                "case_dir": case_dir.name,
                "snapshot_relpath": f"{case_dir.name}/snapshot.json",
                "result_relpath": f"{case_dir.name}/result.json",
                "report_relpath": f"{case_dir.name}/report.html",
                "image_relpath": f"{case_dir.name}/current_scenario.svg",
                "scenario_image_relpaths": {
                    scenario_name: f"{case_dir.name}/{Path(path).name}"
                    for scenario_name, path in scenario_svg_paths.items()
                },
            }
        )

    manifest = {
        "project_name": config.project_name,
        "package_name": f"{config.project_name} Demo Package",
        "input_path": str(input_path),
        "output_dir": str(output_root),
        "radius_nm": radius_nm,
        "grid_cell_size_m": config.grid.cell_size_m,
        "grid_kernel_sigma_m": config.grid.kernel_sigma_m,
        "horizon_minutes": config.horizon.minutes,
        "time_step_seconds": config.horizon.time_step_seconds,
        "safe_threshold": config.thresholds.safe,
        "warning_threshold": config.thresholds.warning,
        "density_radius_nm": config.thresholds.density_radius_nm,
        "density_reference_count": config.thresholds.density_reference_count,
        "weights": asdict(config.weights),
        "scenario_multipliers": {name: value for name, value in config.scenarios},
        "case_count": len(case_entries),
        "cases": case_entries,
    }
    manifest_path = output_root / "manifest.json"
    index_path = output_root / "index.html"
    summary_path = output_root / "summary.md"
    master_assets = build_master_report_assets(
        manifest=manifest,
        snapshots=package_snapshots,
        baseline_results=package_results,
        config=config,
        output_dir=output_root,
        radius_nm=radius_nm,
    )
    manifest.update(master_assets)
    manifest.update(_save_figure_bundle_assets(output_root, manifest))
    manifest.update(build_paper_assets_from_manifest(manifest, output_dir=output_root))
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    index_path.write_text(_build_package_index_html(manifest), encoding="utf-8")
    summary_path.write_text(_build_package_summary_markdown(manifest), encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    manifest["index_path"] = str(index_path)
    manifest["summary_path"] = str(summary_path)
    return manifest


def build_recommended_demo_package_from_csv(
    input_path: str | Path,
    config: ProjectConfig,
    output_dir: str | Path,
    radius_nm: float,
    top_n: int = 3,
    min_targets: int = 1,
) -> dict[str, object]:
    rows = load_curated_csv_rows(input_path)
    return build_recommended_demo_package(
        rows=rows,
        config=config,
        input_path=input_path,
        output_dir=output_dir,
        radius_nm=radius_nm,
        top_n=top_n,
        min_targets=min_targets,
    )
