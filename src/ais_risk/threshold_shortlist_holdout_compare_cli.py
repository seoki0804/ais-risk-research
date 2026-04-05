from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import asdict, replace
from pathlib import Path

from .config import load_config
from .io import load_snapshot, save_result
from .models import ProjectConfig, ScenarioResult, SnapshotInput, ThresholdConfig
from .pipeline import run_snapshot
from .report import build_html_report, build_scenario_svg_text


def _parse_profile(raw: str) -> dict[str, object]:
    parts = [part.strip() for part in raw.split(":")]
    if len(parts) != 3:
        raise ValueError(f"Invalid --profile format: {raw}")
    return {
        "label": parts[0],
        "safe": float(parts[1]),
        "warning": float(parts[2]),
    }


def _parse_case_spec(raw: str) -> dict[str, str]:
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) != 2:
        raise ValueError(f"Invalid --case-spec format: {raw}")
    return {
        "label": parts[0],
        "snapshot_json": parts[1],
    }


def _clone_config(config: ProjectConfig, safe: float, warning: float) -> ProjectConfig:
    thresholds = ThresholdConfig(
        safe=safe,
        warning=warning,
        density_radius_nm=config.thresholds.density_radius_nm,
        density_reference_count=config.thresholds.density_reference_count,
    )
    return replace(config, thresholds=thresholds)


def _select_cases_from_summary(
    summary_path: str | Path,
    scenario_name: str,
    prefer_warning_nonzero: bool,
) -> list[dict[str, object]]:
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    selected: list[dict[str, object]] = []
    for run in summary.get("runs", []):
        candidates = [sample for sample in run.get("samples", []) if str(sample.get("status")) == "completed"]
        if not candidates:
            continue

        def _sort_key(sample: dict[str, object]) -> tuple[int, float, float, float]:
            scenario = sample.get("scenarios", {}).get(scenario_name, {})
            warning_area = float(scenario.get("warning_area_nm2", 0.0) or 0.0)
            return (
                1 if prefer_warning_nonzero and warning_area > 0.0 else 0,
                float(sample.get("target_count", 0.0) or 0.0),
                float(sample.get("selection_score", 0.0) or 0.0),
                float(scenario.get("max_risk", 0.0) or 0.0),
            )

        best = sorted(candidates, key=_sort_key, reverse=True)[0]
        selected.append(
            {
                "label": str(run.get("label", "case")),
                "snapshot_json": str(best["snapshot_json"]),
                "selected_rank": int(best.get("selected_rank", 0) or 0),
                "candidate_rank": int(best.get("candidate_rank", 0) or 0),
                "timestamp": str(best.get("timestamp", "")),
                "own_mmsi": str(best.get("own_mmsi", "")),
                "target_count": int(best.get("target_count", 0) or 0),
                "selection_score": float(best.get("selection_score", 0.0) or 0.0),
                "selection_reason": (
                    "prefer_warning_nonzero"
                    if prefer_warning_nonzero
                    else "highest_target_count_then_selection_score"
                ),
            }
        )
    return selected


def _get_scenario(result, scenario_name: str) -> ScenarioResult:
    for scenario in result.scenarios:
        if scenario.summary.scenario_name == scenario_name:
            return scenario
    raise ValueError(f"Scenario {scenario_name} not found in result.")


def _inject_svg_position(svg_text: str, x: float, y: float, width: float, height: float) -> str:
    return re.sub(
        r"<svg\s+",
        f'<svg x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" ',
        svg_text,
        count=1,
    )


def _build_case_compare_svg(
    *,
    case_label: str,
    snapshot: SnapshotInput,
    scenario_name: str,
    scenario_rows: list[dict[str, object]],
    radius_nm: float,
    cell_size_m: float,
) -> str:
    panel_width = 420.0
    panel_height = 510.0
    panel_gap = 28.0
    margin_x = 28.0
    title_y = 34.0
    subtitle_y = 56.0
    panels_y = 92.0
    footer_y = panels_y + panel_height + 34.0
    width = (margin_x * 2.0) + (panel_width * len(scenario_rows)) + (panel_gap * max(0, len(scenario_rows) - 1))
    height = footer_y + 18.0

    child_svgs: list[str] = []
    header_texts: list[str] = []
    metric_texts: list[str] = []
    for index, row in enumerate(scenario_rows):
        x = margin_x + index * (panel_width + panel_gap)
        child_svgs.append(_inject_svg_position(str(row["scenario_svg"]), x=x, y=panels_y, width=panel_width, height=panel_height))
        header_texts.append(
            f'<text x="{x:.1f}" y="78.0" font-size="15" font-weight="700" fill="#1d2b2a">'
            f'{html.escape(str(row["profile_label"]))} | safe {float(row["safe"]):.2f} | warning {float(row["warning"]):.2f}</text>'
        )
        metric_texts.append(
            f'<text x="{x:.1f}" y="{footer_y:.1f}" font-size="13" fill="#5a645f">'
            f'max {float(row["max_risk"]):.3f} | warning {float(row["warning_area_nm2"]):.3f} nm2 | '
            f'caution {float(row["caution_area_nm2"]):.3f} nm2 | sector {html.escape(str(row["dominant_sector"]))}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height:.1f}" '
        f'width="{width:.1f}" height="{height:.1f}">'
        '<style>'
        'text { font-family: Georgia, "Times New Roman", serif; }'
        '</style>'
        f'<rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" fill="#f4f1e8" />'
        f'<text x="{margin_x:.1f}" y="{title_y:.1f}" font-size="24" font-weight="700" fill="#1d2b2a">'
        f'{html.escape(case_label)}</text>'
        f'<text x="{margin_x:.1f}" y="{subtitle_y:.1f}" font-size="14" fill="#5a645f">'
        f'{html.escape(snapshot.timestamp)} | own MMSI {html.escape(snapshot.own_ship.mmsi)} | '
        f'targets {len(snapshot.targets)} | scenario {html.escape(scenario_name)}</text>'
        f'{"".join(header_texts)}'
        f'{"".join(child_svgs)}'
        f'{"".join(metric_texts)}'
        "</svg>"
    )


def _build_case_compare_html(
    *,
    case_label: str,
    snapshot: SnapshotInput,
    scenario_name: str,
    scenario_rows: list[dict[str, object]],
    compare_svg_name: str,
) -> str:
    table_rows = []
    for row in scenario_rows:
        table_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['profile_label']))}</td>"
            f"<td>{float(row['safe']):.2f}</td>"
            f"<td>{float(row['warning']):.2f}</td>"
            f"<td>{float(row['max_risk']):.3f}</td>"
            f"<td>{float(row['mean_risk']):.3f}</td>"
            f"<td>{float(row['warning_area_nm2']):.3f}</td>"
            f"<td>{float(row['caution_area_nm2']):.3f}</td>"
            f"<td>{html.escape(str(row['dominant_sector']))}</td>"
            f"<td><a href=\"{html.escape(str(row['result_json_relpath']))}\">result.json</a> / "
            f"<a href=\"{html.escape(str(row['report_html_relpath']))}\">report.html</a></td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(case_label)} threshold shortlist compare</title>
  <style>
    body {{
      margin: 0;
      padding: 28px;
      font-family: Georgia, "Times New Roman", serif;
      background: #f4f1e8;
      color: #1d2b2a;
    }}
    .hero {{
      background: #fffdf8;
      border: 1px solid #d7cec0;
      border-radius: 18px;
      padding: 20px 24px;
      margin-bottom: 18px;
    }}
    .panel {{
      background: #fffdf8;
      border: 1px solid #d7cec0;
      border-radius: 18px;
      padding: 20px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .sub {{
      color: #5a645f;
      font-size: 14px;
    }}
    img {{
      width: 100%;
      border-radius: 12px;
      border: 1px solid #d7cec0;
      background: #f4f1e8;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
      font-size: 14px;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid #e1d9cc;
      text-align: left;
    }}
    th {{
      background: #faf6ef;
    }}
  </style>
</head>
<body>
  <section class="hero">
    <h1>{html.escape(case_label)}</h1>
    <div class="sub">{html.escape(snapshot.timestamp)} | own MMSI {html.escape(snapshot.own_ship.mmsi)} | targets {len(snapshot.targets)} | current focus {html.escape(scenario_name)}</div>
  </section>
  <section class="panel">
    <img src="{html.escape(compare_svg_name)}" alt="threshold shortlist comparison" />
    <table>
      <thead>
        <tr>
          <th>Profile</th>
          <th>Safe</th>
          <th>Warning</th>
          <th>Max Risk</th>
          <th>Mean Risk</th>
          <th>Warning Area (nm2)</th>
          <th>Caution Area (nm2)</th>
          <th>Dominant Sector</th>
          <th>Artifacts</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </section>
</body>
</html>
"""


def _build_summary_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Threshold Shortlist Holdout Compare",
        "",
        "## 1) 목적",
        "- [확정] shortlisted threshold 3개를 같은 holdout snapshot에 적용해 heatmap/contour 차이를 시각적으로 비교.",
        "- [확정] threshold를 단일값으로 고정하지 않고 shortlist로 운영해야 한다는 메시지를 spatial output으로 보완.",
        "",
        "## 2) 입력",
        f"- scenario shift summary: `{summary['scenario_shift_summary']}`" if summary.get("scenario_shift_summary") else "- scenario shift summary: manual case specs",
        f"- config path: `{summary['config_path']}`",
        f"- scenario name: `{summary['scenario_name']}`",
        "",
        "## 3) profile shortlist",
    ]
    for profile in summary.get("profiles", []):
        lines.append(
            f"- [확정] `{profile['label']}`: safe `{float(profile['safe']):.2f}`, warning `{float(profile['warning']):.2f}`"
        )

    for case in summary.get("cases", []):
        lines.extend(
            [
                "",
                f"## {case['label']}",
                f"- [확정] snapshot: `{case['timestamp']}` / own `{case['own_mmsi']}` / targets `{case['target_count']}`",
                f"- [합리적 가정] selection reason: `{case['selection_reason']}`",
                f"- [확정] compare svg: `{case['compare_svg']}`",
                f"- [확정] compare html: `{case['compare_html']}`",
                "",
                "| profile | safe | warning | max risk | mean risk | warning area (nm2) | caution area (nm2) | dominant sector |",
                "|---|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for row in case.get("profile_rows", []):
            lines.append(
                f"| {row['profile_label']} | {float(row['safe']):.2f} | {float(row['warning']):.2f} | "
                f"{float(row['max_risk']):.3f} | {float(row['mean_risk']):.3f} | {float(row['warning_area_nm2']):.3f} | "
                f"{float(row['caution_area_nm2']):.3f} | {row['dominant_sector']} |"
            )

    lines.extend(
        [
            "",
            "## 4) 해석",
            "- [확정] 동일 snapshot에서도 safe/warning threshold 조합에 따라 warning contour의 면적과 연결성이 달라진다.",
            "- [확정] 이 비교는 threshold를 single best value로 주장하기보다 shortlist 운영이 타당하다는 보조 근거로 쓰는 편이 적절하다.",
            "- [리스크] AIS-only 결과이므로 contour는 비교용 내부 경계이지 법적 안전 경계가 아니다.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate holdout heatmap/contour comparison artifacts for shortlisted threshold profiles."
    )
    parser.add_argument("--config", default="configs/base.toml", help="Path to base config TOML.")
    parser.add_argument("--output-dir", required=True, help="Directory to write comparison artifacts.")
    parser.add_argument("--scenario-name", default="current", help="Scenario to compare. Default: current.")
    parser.add_argument(
        "--profile",
        action="append",
        required=True,
        help="Profile in label:safe:warning format. Repeatable.",
    )
    parser.add_argument(
        "--scenario-shift-summary",
        help="Optional scenario_shift_multi summary JSON. If provided and --case-spec is omitted, one case per run is auto-selected.",
    )
    parser.add_argument(
        "--case-spec",
        action="append",
        help="Optional manual case in label|snapshot_json format. Repeatable.",
    )
    parser.add_argument(
        "--prefer-warning-nonzero",
        action="store_true",
        help="When auto-selecting from scenario shift summary, prefer cases with nonzero warning area in the target scenario.",
    )
    args = parser.parse_args()

    profiles = [_parse_profile(item) for item in args.profile]
    if not profiles:
        raise ValueError("At least one --profile is required.")

    case_specs: list[dict[str, object]] = []
    if args.case_spec:
        case_specs.extend(_parse_case_spec(item) for item in args.case_spec)
    elif args.scenario_shift_summary:
        case_specs.extend(
            _select_cases_from_summary(
                summary_path=args.scenario_shift_summary,
                scenario_name=args.scenario_name,
                prefer_warning_nonzero=bool(args.prefer_warning_nonzero),
            )
        )
    else:
        raise ValueError("Provide either --scenario-shift-summary or at least one --case-spec.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)

    summary: dict[str, object] = {
        "status": "completed",
        "config_path": str(Path(args.config)),
        "scenario_shift_summary": str(args.scenario_shift_summary) if args.scenario_shift_summary else None,
        "scenario_name": args.scenario_name,
        "profiles": profiles,
        "cases": [],
    }

    for case in case_specs:
        case_label = str(case["label"])
        snapshot_path = Path(str(case["snapshot_json"]))
        snapshot = load_snapshot(snapshot_path)
        case_slug = re.sub(r"[^a-z0-9]+", "_", case_label.lower()).strip("_")
        case_dir = output_dir / case_slug
        case_dir.mkdir(parents=True, exist_ok=True)
        scenario_rows: list[dict[str, object]] = []

        for profile in profiles:
            profile_label = str(profile["label"])
            safe = float(profile["safe"])
            warning = float(profile["warning"])
            profile_slug = re.sub(r"[^a-z0-9]+", "_", profile_label.lower()).strip("_")
            profile_config = _clone_config(config, safe=safe, warning=warning)
            result = run_snapshot(snapshot=snapshot, config=profile_config)
            scenario = _get_scenario(result, args.scenario_name)

            result_path = case_dir / f"{case_slug}_{profile_slug}_result.json"
            report_path = case_dir / f"{case_slug}_{profile_slug}_report.html"
            save_result(result_path, result)
            build_html_report(
                snapshot=snapshot,
                result_path=result_path,
                output_path=report_path,
                radius_nm=profile_config.grid.radius_nm,
                cell_size_m=profile_config.grid.cell_size_m,
                safe_threshold=profile_config.thresholds.safe,
                warning_threshold=profile_config.thresholds.warning,
            )

            scenario_rows.append(
                {
                    "profile_label": profile_label,
                    "safe": safe,
                    "warning": warning,
                    "max_risk": scenario.summary.max_risk,
                    "mean_risk": scenario.summary.mean_risk,
                    "warning_area_nm2": scenario.summary.warning_area_nm2,
                    "caution_area_nm2": scenario.summary.caution_area_nm2,
                    "dominant_sector": scenario.summary.dominant_sector,
                    "result_json_relpath": str(result_path.relative_to(case_dir)),
                    "report_html_relpath": str(report_path.relative_to(case_dir)),
                    "scenario_svg": build_scenario_svg_text(
                        snapshot=snapshot,
                        scenario=asdict(scenario),
                        radius_nm=profile_config.grid.radius_nm,
                        cell_size_m=profile_config.grid.cell_size_m,
                        safe_threshold=profile_config.thresholds.safe,
                        warning_threshold=profile_config.thresholds.warning,
                    ),
                }
            )

        compare_svg_text = _build_case_compare_svg(
            case_label=case_label,
            snapshot=snapshot,
            scenario_name=args.scenario_name,
            scenario_rows=scenario_rows,
            radius_nm=config.grid.radius_nm,
            cell_size_m=config.grid.cell_size_m,
        )
        compare_svg_path = case_dir / f"{case_slug}_{args.scenario_name}_threshold_shortlist_compare.svg"
        compare_svg_path.write_text(compare_svg_text, encoding="utf-8")

        compare_html_path = case_dir / f"{case_slug}_{args.scenario_name}_threshold_shortlist_compare.html"
        compare_html_path.write_text(
            _build_case_compare_html(
                case_label=case_label,
                snapshot=snapshot,
                scenario_name=args.scenario_name,
                scenario_rows=scenario_rows,
                compare_svg_name=compare_svg_path.name,
            ),
            encoding="utf-8",
        )

        summary["cases"].append(
            {
                "label": case_label,
                "snapshot_json": str(snapshot_path),
                "timestamp": snapshot.timestamp,
                "own_mmsi": snapshot.own_ship.mmsi,
                "target_count": len(snapshot.targets),
                "selection_reason": case.get("selection_reason", "manual_case_spec"),
                "selected_rank": case.get("selected_rank"),
                "candidate_rank": case.get("candidate_rank"),
                "selection_score": case.get("selection_score"),
                "compare_svg": str(compare_svg_path),
                "compare_html": str(compare_html_path),
                "profile_rows": [
                    {
                        key: value
                        for key, value in row.items()
                        if key not in {"scenario_svg"}
                    }
                    for row in scenario_rows
                ],
            }
        )

    summary_json = output_dir / "threshold_shortlist_holdout_compare_summary.json"
    summary_md = output_dir / "threshold_shortlist_holdout_compare_summary.md"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md.write_text(_build_summary_markdown(summary), encoding="utf-8")

    print(f"case_count={len(summary['cases'])}")
    print(f"summary_json={summary_json}")
    print(f"summary_md={summary_md}")


if __name__ == "__main__":
    main()
