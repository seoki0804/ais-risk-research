from __future__ import annotations

import csv
import json
import re
from pathlib import Path


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _write_csv(path: str | Path, rows: list[dict[str, object]], fieldnames: list[str]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return destination


def _write_text(path: str | Path, text: str) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return destination


def _latex_escape(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _inline_code_to_latex(text: str) -> str:
    parts = re.split(r"(`[^`]+`)", text)
    rendered: list[str] = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) >= 2:
            rendered.append(f"\\texttt{{{_latex_escape(part[1:-1])}}}")
        else:
            rendered.append(_latex_escape(part))
    return "".join(rendered)


def _case_table_rows(manifest: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "rank": int(case["rank"]),
            "own_mmsi": str(case["own_mmsi"]),
            "timestamp": str(case["timestamp"]),
            "candidate_score": _fmt(float(case["candidate_score"])),
            "current_max_risk": _fmt(float(case["current_max_risk"])),
            "current_warning_area_nm2": _fmt(float(case["current_warning_area_nm2"])),
            "target_count": int(case["target_count"]),
            "dominant_sector": str(case["dominant_sector"]),
        }
        for case in manifest["cases"]
    ]


def _scenario_table_rows(experiment_data: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for scenario_name, metrics in experiment_data["scenario_averages"].items():
        rows.append(
            {
                "scenario": scenario_name,
                "avg_max_risk": _fmt(float(metrics["avg_max_risk"])),
                "avg_mean_risk": _fmt(float(metrics["avg_mean_risk"])),
                "avg_warning_area_nm2": _fmt(float(metrics["avg_warning_area_nm2"])),
                "avg_delta_max_risk_vs_current": _fmt(float(metrics["avg_delta_max_risk_vs_current"])),
                "avg_delta_warning_area_vs_current": _fmt(float(metrics["avg_delta_warning_area_vs_current"])),
            }
        )
    return rows


def _ablation_table_rows(ablation_data: dict[str, object], scenario_name: str = "current") -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for ablation_name, scenario_map in ablation_data["ablations"].items():
        metrics = scenario_map.get(scenario_name)
        if metrics is None:
            continue
        rows.append(
            {
                "ablation": ablation_name,
                "scenario": scenario_name,
                "avg_max_risk": _fmt(float(metrics["avg_max_risk"])),
                "avg_mean_risk": _fmt(float(metrics["avg_mean_risk"])),
                "avg_warning_area_nm2": _fmt(float(metrics["avg_warning_area_nm2"])),
                "avg_delta_max_risk_vs_baseline": _fmt(float(metrics["avg_delta_max_risk_vs_baseline"])),
                "avg_delta_warning_area_vs_baseline": _fmt(float(metrics["avg_delta_warning_area_vs_baseline"])),
            }
        )
    return rows


def _figure_inventory_rows(manifest: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for case in manifest["cases"]:
        scenario_paths = dict(case["scenario_image_relpaths"])
        rows.append(
            {
                "rank": int(case["rank"]),
                "own_mmsi": str(case["own_mmsi"]),
                "timestamp": str(case["timestamp"]),
                "slowdown_svg": str(scenario_paths.get("slowdown", "")),
                "current_svg": str(scenario_paths.get("current", "")),
                "speedup_svg": str(scenario_paths.get("speedup", "")),
            }
        )
    return rows


def _table_json(path: str | Path, rows: list[dict[str, object]]) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return destination


def _table_markdown(title: str, rows: list[dict[str, object]]) -> str:
    if not rows:
        return f"# {title}\n\nNo rows.\n"
    columns = list(rows[0].keys())
    header = "| " + " | ".join(columns) + " |"
    divider = "|" + "|".join("---" for _ in columns) + "|"
    body = ["| " + " | ".join(str(row[column]) for column in columns) + " |" for row in rows]
    return f"# {title}\n\n" + "\n".join([header, divider, *body]) + "\n"


def _humanize_column_name(name: str) -> str:
    mapping = {
        "own_mmsi": "Own MMSI",
        "candidate_score": "Candidate score",
        "current_max_risk": "Current max risk",
        "current_warning_area_nm2": "Current warning area (nm2)",
        "target_count": "Target count",
        "dominant_sector": "Dominant sector",
        "avg_max_risk": "Avg. max risk",
        "avg_mean_risk": "Avg. mean risk",
        "avg_warning_area_nm2": "Avg. warning area (nm2)",
        "avg_delta_max_risk_vs_current": "Avg. delta max risk vs current",
        "avg_delta_warning_area_vs_current": "Avg. delta warning area vs current",
        "avg_delta_max_risk_vs_baseline": "Avg. delta max risk vs baseline",
        "avg_delta_warning_area_vs_baseline": "Avg. delta warning area vs baseline",
    }
    return mapping.get(name, name.replace("_", " ").capitalize())


def _table_latex(caption: str, label: str, rows: list[dict[str, object]]) -> str:
    if not rows:
        return (
            "\\begin{table}[t]\n\\centering\n"
            f"\\caption{{{_latex_escape(caption)}}}\n"
            f"\\label{{{_latex_escape(label)}}}\n"
            "\\begin{tabular}{l}\n\\hline\nNo rows \\\\\n\\hline\n\\end{tabular}\n\\end{table}\n"
        )
    columns = list(rows[0].keys())
    header = " & ".join(_latex_escape(_humanize_column_name(column)) for column in columns) + r" \\"
    body = [
        " & ".join(_latex_escape(row[column]) for column in columns) + r" \\"
        for row in rows
    ]
    alignment = "l" * len(columns)
    return (
        "\\begin{table}[t]\n"
        "\\centering\n"
        f"\\caption{{{_latex_escape(caption)}}}\n"
        f"\\label{{{_latex_escape(label)}}}\n"
        f"\\begin{{tabular}}{{{alignment}}}\n"
        "\\hline\n"
        f"{header}\n"
        "\\hline\n"
        + "\n".join(body)
        + "\n\\hline\n\\end{tabular}\n\\end{table}\n"
    )


def _strip_markdown_headings(text: str) -> list[str]:
    lines = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            continue
        lines.append(raw_line)
    return lines


def _drop_first_markdown_heading(text: str) -> str:
    lines = text.splitlines()
    rendered: list[str] = []
    dropped = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if not dropped and not stripped:
            continue
        if not dropped and stripped.startswith("#"):
            dropped = True
            continue
        rendered.append(raw_line)
    return "\n".join(rendered).strip()


def build_paper_appendix_markdown(
    manifest: dict[str, object],
    case_rows: list[dict[str, object]],
    scenario_rows: list[dict[str, object]],
    ablation_rows: list[dict[str, object]],
    figure_rows: list[dict[str, object]],
    summary_note: str,
    figure_captions: str,
) -> str:
    sections = [
        "# Paper Appendix",
        "",
        "## Scope",
        "",
        f"- Package name: `{manifest['package_name']}`",
        f"- Case count: `{manifest['case_count']}`",
        f"- Radius (NM): `{manifest['radius_nm']:.1f}`",
        f"- Source CSV: `{manifest['input_path']}`",
        "",
        "## Figure Inventory",
        "",
        _table_markdown("Figure Inventory", figure_rows).replace("# Figure Inventory\n\n", "", 1).rstrip(),
        "",
        "## Recommended Summary",
        "",
        "\n".join(_strip_markdown_headings(summary_note)).strip(),
        "",
        "## Figure Captions",
        "",
        "\n".join(_strip_markdown_headings(figure_captions)).strip(),
        "",
        "## Embedded Tables",
        "",
        _table_markdown("Paper Case Table", case_rows).rstrip(),
        "",
        _table_markdown("Paper Scenario Table", scenario_rows).rstrip(),
        "",
        _table_markdown("Paper Current Ablation Table", ablation_rows).rstrip(),
        "",
    ]
    return "\n".join(sections)


def build_paper_appendix_latex(
    manifest: dict[str, object],
    figure_rows: list[dict[str, object]],
    summary_note: str,
    figure_captions: str,
) -> str:
    figure_items = "\n".join(
        (
            "\\item "
            f"Case {int(row['rank'])} ({_latex_escape(row['own_mmsi'])}, {_latex_escape(row['timestamp'])}): "
            f"slowdown \\texttt{{{_latex_escape(Path(str(row['slowdown_svg'])).name)}}}, "
            f"current \\texttt{{{_latex_escape(Path(str(row['current_svg'])).name)}}}, "
            f"speedup \\texttt{{{_latex_escape(Path(str(row['speedup_svg'])).name)}}}."
        )
        for row in figure_rows
    )
    def markdownish_to_latex(text: str) -> str:
        rendered: list[str] = []
        in_list = False
        for raw_line in _strip_markdown_headings(text):
            stripped = raw_line.strip()
            if stripped == "":
                if in_list:
                    rendered.append("\\end{itemize}")
                    in_list = False
                rendered.append("")
                continue
            if stripped.startswith("- "):
                if not in_list:
                    rendered.append("\\begin{itemize}")
                    in_list = True
                rendered.append(f"\\item {_inline_code_to_latex(stripped[2:])}")
                continue
            if in_list:
                rendered.append("\\end{itemize}")
                in_list = False
            rendered.append(_inline_code_to_latex(stripped))
        if in_list:
            rendered.append("\\end{itemize}")
        return "\n".join(rendered).strip()

    summary_latex = markdownish_to_latex(summary_note)
    captions_latex = markdownish_to_latex(figure_captions)
    return f"""\\section*{{Appendix: AIS Risk Mapping Demo Outputs}}

This appendix summarizes the AIS-only demo package generated for the own-ship-centric spatial risk mapping workflow. It should be cited as comparative decision-support evidence, not as a collision-avoidance command.

\\subsection*{{Scope}}

Package: \\texttt{{{_latex_escape(manifest['package_name'])}}} \\\\
Case count: {_latex_escape(manifest['case_count'])} \\\\
Radius: {_latex_escape(f"{float(manifest['radius_nm']):.1f}")} NM \\\\
Source CSV: \\texttt{{{_latex_escape(manifest['input_path'])}}}

\\subsection*{{Figure Inventory}}

\\begin{{itemize}}
{figure_items}
\\end{{itemize}}

\\subsection*{{Recommended Summary}}

{summary_latex}

\\subsection*{{Figure Captions}}

{captions_latex}

\\subsection*{{Tables}}

\\input{{paper_case_table.tex}}

\\input{{paper_scenario_table.tex}}

\\input{{paper_ablation_current_table.tex}}
"""


def _best_scenario(experiment_data: dict[str, object]) -> tuple[str, dict[str, float]]:
    return min(
        experiment_data["scenario_averages"].items(),
        key=lambda item: (
            item[1]["avg_warning_area_nm2"],
            item[1]["avg_max_risk"],
        ),
    )


def _strongest_current_ablation(ablation_data: dict[str, object]) -> tuple[str, dict[str, float]]:
    candidate_items = [
        (name, values["current"])
        for name, values in ablation_data["ablations"].items()
        if name != "baseline" and "current" in values
    ]
    return max(
        candidate_items,
        key=lambda item: abs(float(item[1]["avg_delta_warning_area_vs_baseline"])),
    )


def _failure_case_rows(manifest: dict[str, object], limit: int = 2) -> list[dict[str, object]]:
    ranked = sorted(
        manifest["cases"],
        key=lambda case: (
            float(case["current_max_risk"]),
            float(case["current_warning_area_nm2"]),
            int(case["target_count"]),
        ),
        reverse=True,
    )
    return list(ranked[:limit])


def build_failure_case_notes(manifest: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for case in _failure_case_rows(manifest, limit=2):
        lines.append(
            f"Case `{case['own_mmsi']}` at `{case['timestamp']}` reached current max risk `{_fmt(float(case['current_max_risk']))}` "
            f"with warning area `{_fmt(float(case['current_warning_area_nm2']))}` nm2 and dominant sector `{case['dominant_sector']}`."
        )
    return lines


def build_failure_case_notes_ko(manifest: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for case in _failure_case_rows(manifest, limit=2):
        lines.append(
            f"사례 `{case['own_mmsi']}` / `{case['timestamp']}`는 current max risk `{_fmt(float(case['current_max_risk']))}`, "
            f"warning area `{_fmt(float(case['current_warning_area_nm2']))}` nm2, dominant sector `{case['dominant_sector']}`를 보였다."
        )
    return lines


def build_ablation_interpretation_notes(ablation_data: dict[str, object]) -> list[str]:
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    density_metrics = ablation_data["ablations"].get("drop_density", {}).get("current")
    time_decay_metrics = ablation_data["ablations"].get("drop_time_decay", {}).get("current")
    notes = [
        f"`{strongest_ablation_name}` produced the strongest absolute warning-area shift in the current scenario "
        f"({_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))} nm2)."
    ]
    if density_metrics is not None:
        notes.append(
            f"`drop_density` changed current warning area by {_fmt(float(density_metrics['avg_delta_warning_area_vs_baseline']))} nm2, "
            "which suggests local traffic context materially changes the spatial envelope."
        )
    if time_decay_metrics is not None:
        notes.append(
            f"`drop_time_decay` changed current mean risk by {_fmt(float(time_decay_metrics['avg_mean_risk']))}, "
            "indicating temporal weighting strongly affects how broad the elevated-risk region becomes."
        )
    return notes


def build_ablation_interpretation_notes_ko(ablation_data: dict[str, object]) -> list[str]:
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    density_metrics = ablation_data["ablations"].get("drop_density", {}).get("current")
    time_decay_metrics = ablation_data["ablations"].get("drop_time_decay", {}).get("current")
    notes = [
        f"`{strongest_ablation_name}`은 current scenario에서 warning area를 "
        f"`{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 가장 크게 변화시켰다."
    ]
    if density_metrics is not None:
        notes.append(
            f"`drop_density`는 current warning area를 `{_fmt(float(density_metrics['avg_delta_warning_area_vs_baseline']))}` nm2 변화시켰고, "
            "이는 local traffic context가 spatial envelope 형성에 실질적 영향을 준다는 뜻이다."
        )
    if time_decay_metrics is not None:
        notes.append(
            f"`drop_time_decay`의 current mean risk는 `{_fmt(float(time_decay_metrics['avg_mean_risk']))}`로 나타났으며, "
            "temporal weighting이 고위험 영역의 확장 정도에 큰 영향을 준다는 해석이 가능하다."
        )
    return notes


def build_paper_figure_captions(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)

    lines = [
        "# Paper Figure And Table Captions",
        "",
        "## Figure 1",
        "Own-ship-centric spatial risk comparison for the top-ranked case. "
        "Each panel shows the AIS-only grid-based risk distribution around the own ship under slowdown, current, and speedup scenarios. "
        "Boundary lines indicate threshold contours over aggregated cell risks, not legal safety limits.",
        "",
        "## Figure 2",
        "Multi-case figure bundle for the recommended evaluation set. "
        "Each case is rendered with matched slowdown/current/speedup SVGs so that reviewers can compare directional risk concentration and warning-area changes under speed variation.",
        "",
        "## Table 1",
        "Recommended own-ship evaluation cases ranked by continuity, interaction density, and mobility. "
        "This table defines the case set used for qualitative inspection and package-level aggregation.",
        "",
        "## Table 2",
        f"Package-level scenario comparison. In this sample, `{best_scenario_name}` produced the smallest average warning area "
        f"({_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))} nm2) among the tested speed scenarios.",
        "",
        "## Table 3",
        f"Current-scenario ablation summary. In this sample, `{strongest_ablation_name}` caused the largest absolute change in warning area "
        f"({_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))} nm2) relative to the baseline.",
        "",
    ]

    for case in manifest["cases"]:
        lines.extend(
            [
                f"## Case Figure #{int(case['rank'])}",
                f"Own ship `{case['own_mmsi']}` at `{case['timestamp']}` with dominant sector `{case['dominant_sector']}`. "
                f"The current scenario reaches max risk `{_fmt(float(case['current_max_risk']))}` with `{int(case['target_count'])}` nearby targets. "
                f"The associated SVG set should be cited when discussing scenario-wise spatial redistribution rather than pairwise-only conflict scoring.",
                "",
            ]
        )
    return "\n".join(lines)


def build_paper_figure_captions_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)

    lines = [
        "# 논문 그림 및 표 캡션 초안",
        "",
        "## 그림 1",
        "Top-ranked case에 대한 자선(own ship) 중심 공간 위험도 비교 그림이다. "
        "각 패널은 slowdown, current, speedup 시나리오에서 자선 주변 AIS-only grid risk distribution을 보여준다. "
        "경계선은 cell risk threshold contour이며 법적 안전 경계를 의미하지 않는다.",
        "",
        "## 그림 2",
        "추천 evaluation set 전체에 대한 multi-case figure bundle이다. "
        "각 case는 slowdown/current/speedup SVG를 동일한 구도로 배치하여 속력 변화에 따른 방향별 위험 집중과 warning area 변화를 비교할 수 있게 한다.",
        "",
        "## 표 1",
        "연속성, 상호작용 밀도, 이동성을 기준으로 정렬된 own-ship evaluation case 목록이다. "
        "이 표는 정성 분석 및 package-level aggregation에 사용한 사례 집합을 정의한다.",
        "",
        "## 표 2",
        f"Package-level scenario 비교 결과이다. 이 샘플에서는 `{best_scenario_name}` 시나리오가 평균 warning area "
        f"`{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았다.",
        "",
        "## 표 3",
        f"Current scenario 기준 ablation 요약이다. 이 샘플에서는 `{strongest_ablation_name}`이 baseline 대비 평균 warning area를 "
        f"`{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 가장 크게 변화시켰다.",
        "",
    ]

    for case in manifest["cases"]:
        lines.extend(
            [
                f"## 사례 그림 #{int(case['rank'])}",
                f"자선 `{case['own_mmsi']}`의 시점 `{case['timestamp']}` 사례이며 dominant sector는 `{case['dominant_sector']}`이다. "
                f"Current scenario의 max risk는 `{_fmt(float(case['current_max_risk']))}`, 주변 target 수는 `{int(case['target_count'])}`이다. "
                f"이 SVG 세트는 pairwise score만이 아니라 시나리오별 spatial redistribution을 설명할 때 인용하는 것이 적절하다.",
                "",
            ]
        )
    return "\n".join(lines)


def build_paper_summary_note(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    failure_notes = build_failure_case_notes(manifest)
    ablation_notes = build_ablation_interpretation_notes(ablation_data)
    return f"""# Paper Summary Note

## Recommended Results Paragraph

Using AIS-only reconstructed traffic snapshots, the proposed own-ship-centric risk mapper generated a spatial risk distribution over the surrounding sea area instead of relying on pairwise conflict outputs alone. Across `{manifest['case_count']}` recommended evaluation cases, the `current` scenario produced an average max risk of `{_fmt(float(current_metrics['avg_max_risk']))}` and an average warning area of `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2. Among the tested speed scenarios, `{best_scenario_name}` yielded the smallest average warning area at `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2, showing that speed variation changes not only pairwise indicators but also the geometry of the surrounding high-risk region.

## Recommended Ablation Paragraph

The ablation study was designed to test whether the baseline explanation logic is structurally necessary. In the `current` scenario, `{strongest_ablation_name}` caused the largest absolute warning-area shift relative to the baseline, with an average delta of `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2. This indicates that the removed factor materially affects the final spatial envelope, not just vessel-level ranking.

## Failure Case Notes

- {failure_notes[0]}
- {failure_notes[1] if len(failure_notes) > 1 else failure_notes[0]}

## Ablation Interpretation Bullets

- {ablation_notes[0]}
- {ablation_notes[1] if len(ablation_notes) > 1 else ablation_notes[0]}
- {ablation_notes[2] if len(ablation_notes) > 2 else ablation_notes[-1]}

## Claim Guardrails

- This output is an AIS-only proxy analysis, not a collision-avoidance command.
- `warning area` and `max risk` are internal comparative indicators for scenario analysis.
- Results should be framed as decision-support visualization and research baseline evidence.
"""


def build_paper_summary_note_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    failure_notes = build_failure_case_notes_ko(manifest)
    ablation_notes = build_ablation_interpretation_notes_ko(ablation_data)
    return f"""# 논문 요약 문단 초안

## 결과 요약 문단

AIS-only 재구성 교통 snapshot을 사용한 결과, 제안 시스템은 선박 쌍(pairwise) 단위 충돌 지표만이 아니라 자선 주변 전체 해역에 대한 spatial risk distribution을 생성했다. 추천된 `{manifest['case_count']}`개 evaluation case 전체에서 `current` 시나리오는 평균 max risk `{_fmt(float(current_metrics['avg_max_risk']))}`와 평균 warning area `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2를 보였다. 시험한 속력 시나리오 중에서는 `{best_scenario_name}`가 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았으며, 이는 속력 변화가 pairwise indicator뿐 아니라 주변 고위험 영역의 형상 자체도 바꾼다는 점을 보여준다.

## Ablation 요약 문단

이 ablation study는 baseline 설명 로직의 구조적 필요성을 점검하기 위해 수행했다. `current` 시나리오에서 `{strongest_ablation_name}`는 baseline 대비 평균 warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 변화시켜 가장 큰 절대 효과를 보였다. 이는 해당 요소가 vessel-level ranking만이 아니라 최종 spatial envelope 형성에도 실질적인 영향을 준다는 뜻이다.

## Failure Case Notes

- {failure_notes[0]}
- {failure_notes[1] if len(failure_notes) > 1 else failure_notes[0]}

## Ablation 해석 Bullet

- {ablation_notes[0]}
- {ablation_notes[1] if len(ablation_notes) > 1 else ablation_notes[0]}
- {ablation_notes[2] if len(ablation_notes) > 2 else ablation_notes[-1]}

## Claim Guardrails

- 본 결과는 AIS-only proxy analysis이며 충돌회피 명령 생성 시스템이 아니다.
- `warning area`와 `max risk`는 시나리오 비교를 위한 내부 지표다.
- 결과 해석은 의사결정 지원 시각화 및 연구 baseline 근거 수준으로 제한해야 한다.
"""


def build_paper_results_section(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    density_metrics = ablation_data["ablations"].get("drop_density", {}).get("current")
    time_decay_metrics = ablation_data["ablations"].get("drop_time_decay", {}).get("current")
    lines = [
        "# Paper Results Section Draft",
        "",
        "## Results",
        "",
        "### Scenario-Level Spatial Risk Comparison",
        "",
        f"Across `{manifest['case_count']}` recommended evaluation cases, the AIS-only own-ship-centric mapper produced an average current max risk of `{_fmt(float(current_metrics['avg_max_risk']))}` and an average current warning area of `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2. "
        f"At the package level, `{best_scenario_name}` yielded the smallest average warning area at `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2. "
        "This supports the claim that speed variation changes the geometry of the surrounding elevated-risk envelope rather than only shifting pairwise CPA/TCPA-style indicators.",
        "",
        "### Ablation And Explainability Check",
        "",
        f"In the current scenario, `{strongest_ablation_name}` produced the largest absolute warning-area delta relative to the baseline "
        f"(`{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2). "
        "This indicates that the removed factor is structurally involved in shaping the final spatial contour, not merely in re-ranking nearby targets.",
        "",
    ]
    if density_metrics is not None:
        lines.extend(
            [
                f"Removing density changed current warning area by `{_fmt(float(density_metrics['avg_delta_warning_area_vs_baseline']))}` nm2, "
                "which suggests local traffic context materially influences the breadth of the mapped warning zone.",
                "",
            ]
        )
    if time_decay_metrics is not None:
        lines.extend(
            [
                f"Removing time decay produced a current mean risk of `{_fmt(float(time_decay_metrics['avg_mean_risk']))}`, "
                "showing that temporal weighting affects how broadly the risk field remains elevated around the own ship.",
                "",
            ]
        )
    lines.extend(
        [
            "### Representative High-Risk Cases",
            "",
        ]
    )
    for case in _failure_case_rows(manifest, limit=2):
        lines.append(
            f"- Case `{case['own_mmsi']}` at `{case['timestamp']}` reached current max risk `{_fmt(float(case['current_max_risk']))}` with warning area `{_fmt(float(case['current_warning_area_nm2']))}` nm2, `{int(case['target_count'])}` nearby targets, and dominant sector `{case['dominant_sector']}`."
        )
    lines.extend(
        [
            "",
            "### Reporting Guardrails",
            "",
            "- These outputs should be framed as AIS-only spatial risk evidence for decision support.",
            "- The generated heatmaps and contours are comparative internal indicators, not legal safety limits.",
            "- The package should not be presented as an autonomous collision-avoidance controller.",
            "",
        ]
    )
    return "\n".join(lines)


def build_paper_results_section_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    density_metrics = ablation_data["ablations"].get("drop_density", {}).get("current")
    time_decay_metrics = ablation_data["ablations"].get("drop_time_decay", {}).get("current")
    lines = [
        "# 논문 Results 초안",
        "",
        "## Results",
        "",
        "### 시나리오 수준 공간 위험 비교",
        "",
        f"추천된 `{manifest['case_count']}`개 evaluation case 전체에서 AIS-only 자선 중심 mapper는 current max risk 평균 `{_fmt(float(current_metrics['avg_max_risk']))}`와 current warning area 평균 `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2를 산출했다. "
        f"패키지 수준 비교에서는 `{best_scenario_name}` 시나리오가 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았다. "
        "이는 속력 변화가 pairwise CPA/TCPA 유사 지표만이 아니라 자선 주변 고위험 영역의 형상 자체를 바꾼다는 해석을 뒷받침한다.",
        "",
        "### Ablation 및 설명 가능성 점검",
        "",
        f"Current scenario에서 `{strongest_ablation_name}`은 baseline 대비 warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 가장 크게 변화시켰다. "
        "이는 제거된 요소가 단순한 vessel ranking 보정이 아니라 최종 spatial contour 형성에 구조적으로 관여한다는 뜻이다.",
        "",
    ]
    if density_metrics is not None:
        lines.extend(
            [
                f"`drop_density`는 current warning area를 `{_fmt(float(density_metrics['avg_delta_warning_area_vs_baseline']))}` nm2 변화시켰고, "
                "이는 local traffic context가 warning zone의 폭을 실질적으로 좌우한다는 점을 보여준다.",
                "",
            ]
        )
    if time_decay_metrics is not None:
        lines.extend(
            [
                f"`drop_time_decay`의 current mean risk는 `{_fmt(float(time_decay_metrics['avg_mean_risk']))}`로 나타났고, "
                "이는 temporal weighting이 자선 주변 위험장의 확산 정도를 크게 바꾼다는 해석으로 이어진다.",
                "",
            ]
        )
    lines.extend(
        [
            "### 대표 고위험 사례",
            "",
        ]
    )
    for case in _failure_case_rows(manifest, limit=2):
        lines.append(
            f"- 사례 `{case['own_mmsi']}` / `{case['timestamp']}`는 current max risk `{_fmt(float(case['current_max_risk']))}`, warning area `{_fmt(float(case['current_warning_area_nm2']))}` nm2, 주변 target `{int(case['target_count'])}`척, dominant sector `{case['dominant_sector']}`를 보였다."
        )
    lines.extend(
        [
            "",
            "### 해석 가드레일",
            "",
            "- 본 출력은 AIS-only spatial risk evidence이며 항해 의사결정 지원 범위로 해석해야 한다.",
            "- 생성된 heatmap과 contour는 비교용 내부 지표이며 법적 안전 경계를 의미하지 않는다.",
            "- 본 패키지를 완전자율 충돌회피 제어기로 설명해서는 안 된다.",
            "",
        ]
    )
    return "\n".join(lines)


def build_paper_results_section_latex(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    density_metrics = ablation_data["ablations"].get("drop_density", {}).get("current")
    time_decay_metrics = ablation_data["ablations"].get("drop_time_decay", {}).get("current")
    case_items = "\n".join(
        (
            "\\item "
            f"Case {_latex_escape(case['own_mmsi'])} at {_latex_escape(case['timestamp'])}: "
            f"current max risk {_latex_escape(_fmt(float(case['current_max_risk'])))}; "
            f"warning area {_latex_escape(_fmt(float(case['current_warning_area_nm2'])))} nm2; "
            f"targets {_latex_escape(int(case['target_count']))}; "
            f"dominant sector {_latex_escape(case['dominant_sector'])}."
        )
        for case in _failure_case_rows(manifest, limit=2)
    )
    density_sentence = ""
    if density_metrics is not None:
        density_sentence = (
            f"Removing density changed current warning area by "
            f"{_latex_escape(_fmt(float(density_metrics['avg_delta_warning_area_vs_baseline'])))} nm2, "
            "which suggests local traffic context materially influences the breadth of the mapped warning zone."
        )
    time_decay_sentence = ""
    if time_decay_metrics is not None:
        time_decay_sentence = (
            f"Removing time decay produced a current mean risk of "
            f"{_latex_escape(_fmt(float(time_decay_metrics['avg_mean_risk'])))}; "
            "this indicates that temporal weighting strongly affects how broadly the risk field remains elevated."
        )
    return f"""\\section{{Results}}

\\subsection{{Scenario-Level Spatial Risk Comparison}}

Across {_latex_escape(manifest['case_count'])} recommended evaluation cases, the AIS-only own-ship-centric mapper produced an average current max risk of {_latex_escape(_fmt(float(current_metrics['avg_max_risk'])))} and an average current warning area of {_latex_escape(_fmt(float(current_metrics['avg_warning_area_nm2'])))} nm2. At the package level, \\texttt{{{_latex_escape(best_scenario_name)}}} yielded the smallest average warning area at {_latex_escape(_fmt(float(best_scenario_metrics['avg_warning_area_nm2'])))} nm2 (Table~\\ref{{tab:scenario_comparison}}). This indicates that speed variation changes the geometry of the surrounding elevated-risk envelope rather than only shifting pairwise CPA/TCPA-style indicators. The standalone SVG figure bundle should therefore be interpreted as a spatial redistribution view around the own ship.

\\subsection{{Ablation And Explainability Check}}

In the current scenario, \\texttt{{{_latex_escape(strongest_ablation_name)}}} produced the largest absolute warning-area delta relative to the baseline, with {_latex_escape(_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline'])))} nm2 (Table~\\ref{{tab:current_ablation}}). This indicates that the removed factor is structurally involved in shaping the final spatial contour, not merely in re-ranking nearby targets.

{density_sentence}

{time_decay_sentence}

\\subsection{{Representative High-Risk Cases}}

\\begin{{itemize}}
{case_items}
\\end{{itemize}}

\\subsection{{Reporting Guardrails}}

\\begin{{itemize}}
\\item These outputs should be framed as AIS-only spatial risk evidence for decision support.
\\item The generated heatmaps and contours are comparative internal indicators, not legal safety limits.
\\item The package should not be presented as an autonomous collision-avoidance controller.
\\end{{itemize}}
"""


def build_paper_methods_section(manifest: dict[str, object]) -> str:
    scenario_map = manifest.get("scenario_multipliers", {})
    weights = manifest.get("weights", {})
    grid_cell_size_m = float(manifest.get("grid_cell_size_m", 250.0))
    grid_kernel_sigma_m = float(manifest.get("grid_kernel_sigma_m", 200.0))
    safe_threshold = float(manifest.get("safe_threshold", 0.35))
    warning_threshold = float(manifest.get("warning_threshold", 0.65))
    horizon_minutes = int(manifest.get("horizon_minutes", 15))
    time_step_seconds = int(manifest.get("time_step_seconds", 30))
    scenario_text = ", ".join(
        f"`{name}`={_fmt(float(value), 2)}x" for name, value in scenario_map.items()
    ) or "`slowdown`/`current`/`speedup`"
    weight_text = ", ".join(
        f"`{name}`={_fmt(float(value), 2)}" for name, value in weights.items()
    ) or "`distance`/`dcpa`/`tcpa`/`bearing`/`relspeed`/`encounter`/`density`"
    return f"""# Paper Methods Section Draft

## Methods

### Data Scope And Preprocessing

The workflow uses AIS-only traffic data from `{manifest['input_path']}` and constructs own-ship-centric evaluation cases within a radius of `{_fmt(float(manifest['radius_nm']), 1)}` NM. Raw records are normalized, filtered, and reconstructed into time-consistent vessel tracks before extracting own-ship snapshots. This pipeline is designed for public AIS data and does not assume radar, camera, LiDAR, or helm-command labels.

### Rule-Based Risk Baseline

For each snapshot, nearby vessels are converted into relative-motion features including distance, relative bearing, relative speed, DCPA, TCPA, and encounter type. A rule-based baseline then combines these factors into a pairwise risk score using weighted components: {weight_text}. The approach remains intentionally explainable and is positioned as the primary MVP baseline rather than as a hidden black-box model.

### Spatial Aggregation And Contours

Pairwise vessel risk is projected onto a local grid around the own ship using a cell size of `{_fmt(grid_cell_size_m, 1)}` m and a spatial kernel sigma of `{_fmt(grid_kernel_sigma_m, 1)}` m. Aggregated cell risk is summarized as heatmaps and threshold contours. In this package, the `safe` threshold is `{_fmt(safe_threshold, 2)}` and the `warning` threshold is `{_fmt(warning_threshold, 2)}`. These contours are comparative internal boundaries, not certified safety limits.

### Scenario Design And Evaluation

Speed scenarios are evaluated by rescaling own-ship speed while keeping the same traffic snapshot: {scenario_text}. The prediction horizon is `{horizon_minutes}` minutes with a time step of `{time_step_seconds}` seconds. Scenario comparison focuses on max risk, mean risk, warning-area size, dominant sector, and package-level aggregates across recommended evaluation cases.

### Modeling Guardrails

- The baseline is AIS-only and does not estimate full bridge intent or collision-avoidance commands.
- The generated heatmap is intended for risk awareness and decision support, not autonomous control.
- ML comparators may be added later, but this method section describes the rule-based baseline used for the current MVP and research package.
"""


def build_paper_methods_section_ko(manifest: dict[str, object]) -> str:
    scenario_map = manifest.get("scenario_multipliers", {})
    weights = manifest.get("weights", {})
    grid_cell_size_m = float(manifest.get("grid_cell_size_m", 250.0))
    grid_kernel_sigma_m = float(manifest.get("grid_kernel_sigma_m", 200.0))
    safe_threshold = float(manifest.get("safe_threshold", 0.35))
    warning_threshold = float(manifest.get("warning_threshold", 0.65))
    horizon_minutes = int(manifest.get("horizon_minutes", 15))
    time_step_seconds = int(manifest.get("time_step_seconds", 30))
    scenario_text = ", ".join(
        f"`{name}`={_fmt(float(value), 2)}x" for name, value in scenario_map.items()
    ) or "`slowdown`/`current`/`speedup`"
    weight_text = ", ".join(
        f"`{name}`={_fmt(float(value), 2)}" for name, value in weights.items()
    ) or "`distance`/`dcpa`/`tcpa`/`bearing`/`relspeed`/`encounter`/`density`"
    return f"""# 논문 Methods 초안

## Methods

### 데이터 범위 및 전처리

본 workflow는 `{manifest['input_path']}`의 AIS-only 교통 데이터를 사용하고, 반경 `{_fmt(float(manifest['radius_nm']), 1)}` NM 내에서 자선 중심 evaluation case를 구성한다. Raw record는 정규화, 필터링, trajectory reconstruction을 거친 뒤 own-ship snapshot으로 추출된다. 이 파이프라인은 공개 AIS 데이터만을 전제로 하며 radar, camera, LiDAR, helm-command label을 가정하지 않는다.

### 규칙 기반 위험도 baseline

각 snapshot에서 주변 선박은 distance, relative bearing, relative speed, DCPA, TCPA, encounter type 등의 상대운동 feature로 변환된다. 이후 규칙 기반 baseline이 {weight_text} 가중치를 사용해 pairwise risk score를 계산한다. 본 접근은 설명 가능성을 우선한 설계이며, 숨겨진 black-box model이 아니라 현재 MVP와 연구 패키지의 주 baseline으로 위치시킨다.

### 공간 집계와 contour

Pairwise vessel risk는 자선 주변 local grid에 투영되며, cell size는 `{_fmt(grid_cell_size_m, 1)}` m, spatial kernel sigma는 `{_fmt(grid_kernel_sigma_m, 1)}` m이다. 집계된 cell risk는 heatmap과 threshold contour로 요약된다. 이 패키지에서 `safe` threshold는 `{_fmt(safe_threshold, 2)}`, `warning` threshold는 `{_fmt(warning_threshold, 2)}`이다. 이 contour는 비교용 내부 경계이며 인증된 안전 기준이 아니다.

### 시나리오 설계와 평가

속력 시나리오는 동일한 traffic snapshot에서 자선 속력을 재조정하는 방식으로 평가한다: {scenario_text}. 예측 horizon은 `{horizon_minutes}`분, time step은 `{time_step_seconds}`초다. 시나리오 비교는 max risk, mean risk, warning area, dominant sector, recommended case 집합 전반의 package-level aggregate를 중심으로 수행한다.

### 모델링 가드레일

- 본 baseline은 AIS-only이며 bridge intent 전체나 collision-avoidance command를 추정하지 않는다.
- 생성된 heatmap은 위험 인지 및 의사결정 지원 목적이며 autonomous control 출력이 아니다.
- ML comparator는 후속 확장안으로 둘 수 있으나, 현재 문단은 규칙 기반 baseline 중심의 MVP/연구 패키지를 설명한다.
"""


def build_paper_methods_section_latex(manifest: dict[str, object]) -> str:
    scenario_map = manifest.get("scenario_multipliers", {})
    weights = manifest.get("weights", {})
    grid_cell_size_m = float(manifest.get("grid_cell_size_m", 250.0))
    grid_kernel_sigma_m = float(manifest.get("grid_kernel_sigma_m", 200.0))
    safe_threshold = float(manifest.get("safe_threshold", 0.35))
    warning_threshold = float(manifest.get("warning_threshold", 0.65))
    horizon_minutes = int(manifest.get("horizon_minutes", 15))
    time_step_seconds = int(manifest.get("time_step_seconds", 30))
    scenario_text = ", ".join(
        f"\\texttt{{{_latex_escape(str(name))}}}={_latex_escape(_fmt(float(value), 2))}x"
        for name, value in scenario_map.items()
    ) or "\\texttt{slowdown}/\\texttt{current}/\\texttt{speedup}"
    weight_text = ", ".join(
        f"\\texttt{{{_latex_escape(str(name))}}}={_latex_escape(_fmt(float(value), 2))}"
        for name, value in weights.items()
    ) or "\\texttt{distance}, \\texttt{dcpa}, \\texttt{tcpa}, \\texttt{bearing}, \\texttt{relspeed}, \\texttt{encounter}, \\texttt{density}"
    return f"""\\section{{Methods}}

\\subsection{{Data Scope And Preprocessing}}

The workflow uses AIS-only traffic data from \\texttt{{{_latex_escape(manifest['input_path'])}}} and constructs own-ship-centric evaluation cases within a radius of {_latex_escape(_fmt(float(manifest['radius_nm']), 1))} NM. Raw records are normalized, filtered, and reconstructed into time-consistent vessel tracks before extracting own-ship snapshots. The pipeline does not assume radar, camera, LiDAR, or helm-command labels.

\\subsection{{Rule-Based Risk Baseline}}

For each snapshot, nearby vessels are converted into relative-motion features including distance, relative bearing, relative speed, DCPA, TCPA, and encounter type. A rule-based baseline combines these factors into a pairwise risk score using weighted components: {weight_text}. This approach is intentionally explainable and is positioned as the primary MVP baseline rather than as a hidden black-box model.

\\subsection{{Spatial Aggregation And Contours}}

Pairwise vessel risk is projected onto a local grid around the own ship using a cell size of {_latex_escape(_fmt(grid_cell_size_m, 1))} m and a spatial kernel sigma of {_latex_escape(_fmt(grid_kernel_sigma_m, 1))} m. Aggregated cell risk is summarized as heatmaps and threshold contours. In this package, the \\texttt{{safe}} threshold is {_latex_escape(_fmt(safe_threshold, 2))} and the \\texttt{{warning}} threshold is {_latex_escape(_fmt(warning_threshold, 2))}. These contours are comparative internal boundaries, not certified safety limits.

\\subsection{{Scenario Design And Evaluation}}

Speed scenarios are evaluated by rescaling own-ship speed while keeping the same traffic snapshot: {scenario_text}. The prediction horizon is {_latex_escape(horizon_minutes)} minutes with a time step of {_latex_escape(time_step_seconds)} seconds. Scenario comparison focuses on max risk, mean risk, warning-area size, dominant sector, and package-level aggregates across recommended evaluation cases.

\\subsection{{Modeling Guardrails}}

\\begin{{itemize}}
\\item The baseline is AIS-only and does not estimate full bridge intent or collision-avoidance commands.
\\item The generated heatmap is intended for risk awareness and decision support, not autonomous control.
\\item ML comparators may be added later, but this section describes the rule-based baseline used for the current MVP and research package.
\\end{{itemize}}
"""


def build_paper_discussion_section(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# Paper Discussion Section Draft

## Discussion

### Main Interpretation

The main value of this package is that it extends AIS risk analysis from pairwise vessel comparison to an own-ship-centric spatial representation. Across `{manifest['case_count']}` recommended cases, the system produced a current average max risk of `{_fmt(float(current_metrics['avg_max_risk']))}` and translated those vessel-level interactions into heatmaps and contours that can be compared by direction and area. This makes the output more suitable for operator-facing risk awareness than a CPA/TCPA list alone.

### Scenario Implication

The package-level scenario comparison shows that `{best_scenario_name}` achieved the smallest average warning area at `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2. This should not be interpreted as a universal speed policy. Instead, it demonstrates that own-ship speed changes can materially reshape the surrounding spatial risk envelope, which supports the use of scenario comparison as a decision-support aid rather than as a fixed rule.

### Explainability Value

The ablation result indicates that `{strongest_ablation_name}` caused the largest absolute warning-area delta relative to baseline (`{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2). This matters because it shows that the baseline is not only producing a score but also exposing which design factors materially alter the resulting contour. That explainability is a stronger MVP property than adding an opaque ML model too early.

### Limitations

- The package is AIS-only and cannot verify intent, radar contacts, visibility, sea state, or bridge commands.
- The generated contours are internal comparative boundaries, not legal safety limits or certified navigation advice.
- The current validation uses recommended cases from the available dataset and does not prove generalization across all sea areas or vessel classes.
- The scenario outcome should be read as a relative comparison within the same traffic snapshot, not as a deterministic maneuver recommendation.

### Future Work

- Validate the same baseline across multiple sea areas and traffic regimes to test spatial generalization.
- Add structured comparison against a lightweight ML classifier only after the rule-based baseline is stable and interpretable.
- Improve narrative outputs by linking dominant sector, encounter mix, and top contributors to clearer operator-facing explanations.
"""


def build_paper_discussion_section_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# 논문 Discussion 초안

## Discussion

### 핵심 해석

이 패키지의 핵심 가치는 AIS 위험 분석을 선박 쌍(pairwise) 비교에서 자선 중심 spatial representation으로 확장했다는 점이다. 추천된 `{manifest['case_count']}`개 사례 전반에서 시스템은 current 평균 max risk `{_fmt(float(current_metrics['avg_max_risk']))}`를 산출했고, 이를 방향성과 면적 단위로 비교 가능한 heatmap과 contour로 변환했다. 따라서 단순 CPA/TCPA 목록보다 operator-facing risk awareness 관점에서 더 직접적인 표현이 가능하다.

### 시나리오 해석

패키지 수준 scenario 비교에서는 `{best_scenario_name}`가 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았다. 이를 보편적 속력 정책으로 해석해서는 안 된다. 대신 자선 속력 변화가 주변 spatial risk envelope의 형상을 실질적으로 바꾼다는 점을 보여주는 근거로 읽는 것이 타당하다. 즉, scenario comparison은 고정 규칙이 아니라 의사결정 지원 수단으로 해석해야 한다.

### 설명 가능성 가치

Ablation 결과에서 `{strongest_ablation_name}`은 baseline 대비 warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 가장 크게 변화시켰다. 이는 baseline이 단순히 score를 내는 것을 넘어, 어떤 설계 요소가 최종 contour를 실질적으로 바꾸는지까지 드러낸다는 뜻이다. 이 설명 가능성은 현 단계에서 불투명한 ML 모델을 성급히 추가하는 것보다 더 강한 MVP 속성이다.

### 한계

- 본 패키지는 AIS-only이므로 intent, radar contact, 시계, 해상 상태, bridge command를 검증할 수 없다.
- 생성된 contour는 내부 비교 경계이며 법적 안전 한계나 인증된 항해 조언이 아니다.
- 현재 검증은 가용 데이터셋에서 추천된 사례 집합 기준이며, 모든 해역과 선종으로의 일반화를 입증하지 않는다.
- 시나리오 결과는 동일 traffic snapshot 내 상대 비교로 읽어야 하며, 결정적 조선 권고로 해석해서는 안 된다.

### 후속 과제

- 서로 다른 해역과 교통 밀도 조건에서 같은 baseline을 검증해 spatial generalization을 점검한다.
- 규칙 기반 baseline의 안정성과 설명 가능성이 확보된 뒤에만 경량 ML comparator를 비교안으로 추가한다.
- dominant sector, encounter mix, top contributor를 더 명확한 operator-facing 설명 문장으로 연결한다.
"""


def build_paper_discussion_section_latex(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""\\section{{Discussion}}

\\subsection{{Main Interpretation}}

The main value of this package is that it extends AIS risk analysis from pairwise vessel comparison to an own-ship-centric spatial representation. Across {_latex_escape(manifest['case_count'])} recommended cases, the system produced a current average max risk of {_latex_escape(_fmt(float(current_metrics['avg_max_risk'])))} and translated vessel-level interactions into heatmaps and contours that can be compared by direction and area. This makes the output more suitable for operator-facing risk awareness than a CPA/TCPA list alone.

\\subsection{{Scenario Implication}}

The package-level scenario comparison shows that \\texttt{{{_latex_escape(best_scenario_name)}}} achieved the smallest average warning area at {_latex_escape(_fmt(float(best_scenario_metrics['avg_warning_area_nm2'])))} nm2. This should not be interpreted as a universal speed policy. Instead, it demonstrates that own-ship speed changes can materially reshape the surrounding spatial risk envelope, which supports the use of scenario comparison as a decision-support aid rather than as a fixed rule.

\\subsection{{Explainability Value}}

The ablation result indicates that \\texttt{{{_latex_escape(strongest_ablation_name)}}} caused the largest absolute warning-area delta relative to baseline ({_latex_escape(_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline'])))} nm2). This matters because it shows that the baseline is not only producing a score but also exposing which design factors materially alter the resulting contour. That explainability is a stronger MVP property than adding an opaque ML model too early.

\\subsection{{Limitations}}

\\begin{{itemize}}
\\item The package is AIS-only and cannot verify intent, radar contacts, visibility, sea state, or bridge commands.
\\item The generated contours are internal comparative boundaries, not legal safety limits or certified navigation advice.
\\item The current validation uses recommended cases from the available dataset and does not prove generalization across all sea areas or vessel classes.
\\item The scenario outcome should be read as a relative comparison within the same traffic snapshot, not as a deterministic maneuver recommendation.
\\end{{itemize}}

\\subsection{{Future Work}}

\\begin{{itemize}}
\\item Validate the same baseline across multiple sea areas and traffic regimes to test spatial generalization.
\\item Add structured comparison against a lightweight ML classifier only after the rule-based baseline is stable and interpretable.
\\item Improve narrative outputs by linking dominant sector, encounter mix, and top contributors to clearer operator-facing explanations.
\\end{{itemize}}
"""


def build_paper_abstract(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# Paper Abstract Draft

## Abstract

This study presents an AIS-only own-ship-centric spatial risk mapping pipeline for maritime decision support. Instead of stopping at pairwise vessel conflict indicators, the proposed baseline converts relative-motion features into grid-based risk heatmaps and threshold contours around the own ship. Across `{manifest['case_count']}` recommended evaluation cases, the `current` scenario produced an average max risk of `{_fmt(float(current_metrics['avg_max_risk']))}` and an average warning area of `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2, while `{best_scenario_name}` yielded the smallest average warning area at `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2. Ablation analysis further showed that `{strongest_ablation_name}` caused the largest warning-area shift relative to the baseline (`{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2), indicating that the rule-based design remains structurally interpretable. The package is intended as an AIS-only risk awareness and scenario-comparison tool, not as an autonomous collision-avoidance controller.
"""


def build_paper_abstract_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# 논문 Abstract 초안

## Abstract

본 연구는 해양 의사결정 지원을 위한 AIS-only 자선 중심 spatial risk mapping pipeline을 제안한다. 제안 baseline은 선박 쌍(pairwise) 충돌 지표에 머무르지 않고, 상대운동 feature를 자선 주변 grid risk heatmap과 threshold contour로 변환한다. 추천된 `{manifest['case_count']}`개 evaluation case 전체에서 `current` 시나리오는 평균 max risk `{_fmt(float(current_metrics['avg_max_risk']))}`와 평균 warning area `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2를 보였고, `{best_scenario_name}` 시나리오는 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았다. 또한 ablation 분석에서 `{strongest_ablation_name}`은 baseline 대비 warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 가장 크게 변화시켜, 규칙 기반 설계가 구조적으로 설명 가능함을 보여주었다. 본 패키지는 AIS-only 위험 인지 및 scenario comparison 도구이며, autonomous collision-avoidance controller가 아니다.
"""


def build_paper_introduction(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
) -> str:
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# Paper Introduction Section Draft

## Introduction

AIS-based maritime risk analysis is often reported as a list of pairwise vessel conflict indicators such as distance, DCPA, TCPA, or encounter type. That view is useful, but it does not directly answer an operator-facing question: which surrounding direction or sea area is currently more hazardous for the own ship. This project addresses that gap by converting AIS-only traffic snapshots into an own-ship-centric spatial risk representation.

The proposed system focuses on a practical MVP baseline that can be implemented with public AIS data. It reconstructs traffic snapshots, computes relative-motion features, scores pairwise interactions with explainable rules, and aggregates them into grid-based heatmaps and contours. In the current sample package, the recommended evaluation set produced an average current max risk of `{_fmt(float(current_metrics['avg_max_risk']))}` and an average current warning area of `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2.

### Contributions

- It extends pairwise AIS risk analysis into an own-ship-centric spatial risk map and contour representation.
- It compares slowdown/current/speedup scenarios within the same traffic snapshot to show how surrounding risk geometry changes.
- It prioritizes an explainable rule-based baseline that is realistic for public AIS-only research and MVP implementation.
"""


def build_paper_introduction_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
) -> str:
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# 논문 Introduction 초안

## Introduction

AIS 기반 해양 위험 분석은 distance, DCPA, TCPA, encounter type과 같은 pairwise conflict indicator 목록으로 제시되는 경우가 많다. 이런 관점은 유용하지만, 항해 실무 관점의 핵심 질문인 “자선 주변 어느 방향 또는 어느 해역이 현재 더 위험한가”에 직접 답하지는 못한다. 본 프로젝트는 이 간극을 메우기 위해 AIS-only 교통 snapshot을 자선 중심 spatial risk representation으로 변환한다.

제안 시스템은 공개 AIS 데이터만으로 구현 가능한 실용적 MVP baseline에 초점을 둔다. 교통 snapshot을 재구성하고, 상대운동 feature를 계산하며, 설명 가능한 규칙 기반 pairwise score를 만든 뒤, 이를 grid heatmap과 contour로 집계한다. 현재 sample package에서 추천된 사례 집합은 current 평균 max risk `{_fmt(float(current_metrics['avg_max_risk']))}`와 평균 warning area `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2를 보였다.

### 기여점

- Pairwise AIS 위험 분석을 자선 중심 spatial risk map 및 contour 표현으로 확장한다.
- 동일 traffic snapshot에서 slowdown/current/speedup 시나리오를 비교해 주변 위험 형상이 어떻게 바뀌는지 보여준다.
- 공개 AIS-only 연구 및 MVP 구현에 적합한 설명 가능한 규칙 기반 baseline을 우선한다.
"""


def build_paper_conclusion(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    return f"""# Paper Conclusion Section Draft

## Conclusion

This package demonstrates that an AIS-only rule-based baseline can support own-ship-centric spatial risk mapping without overclaiming autonomy. The generated heatmaps, contours, and scenario comparisons show a feasible path from public AIS preprocessing to interpretable risk visualization. In the current sample, `{best_scenario_name}` yielded the smallest average warning area at `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2, while `{strongest_ablation_name}` produced the largest warning-area delta relative to baseline (`{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2), reinforcing the structural value of the explainable baseline design.

The main practical implication is not that the system finds a universal maneuver rule, but that it provides a spatially legible comparison layer for maritime decision support. Future work should validate the same baseline over additional sea areas and add lightweight ML comparators only after the AIS-only rule-based reference is stable and well understood.
"""


def build_paper_conclusion_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    return f"""# 논문 Conclusion 초안

## Conclusion

본 패키지는 AIS-only 규칙 기반 baseline만으로도 자선 중심 spatial risk mapping을 과장 없이 구현할 수 있음을 보여준다. 생성된 heatmap, contour, scenario comparison은 공개 AIS 전처리부터 설명 가능한 위험 시각화까지의 현실적인 경로를 제시한다. 현재 sample에서는 `{best_scenario_name}` 시나리오가 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았고, `{strongest_ablation_name}`은 baseline 대비 warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 가장 크게 변화시켜 설명 가능한 baseline 설계의 구조적 가치를 보여주었다.

핵심 실무적 의미는 이 시스템이 보편적 조선 규칙을 찾는 것이 아니라, 해양 의사결정 지원을 위한 공간적 비교 레이어를 제공한다는 점이다. 후속 단계에서는 추가 해역 검증을 통해 baseline의 일반화를 확인하고, AIS-only 규칙 기반 기준선이 충분히 안정화된 이후에만 경량 ML comparator를 비교안으로 추가하는 것이 타당하다.
"""


def build_paper_abstract_latex(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""\\begin{{abstract}}
This study presents an AIS-only own-ship-centric spatial risk mapping pipeline for maritime decision support. Instead of stopping at pairwise vessel conflict indicators, the proposed baseline converts relative-motion features into grid-based risk heatmaps and threshold contours around the own ship. Across {_latex_escape(manifest['case_count'])} recommended evaluation cases, the \\texttt{{current}} scenario produced an average max risk of {_latex_escape(_fmt(float(current_metrics['avg_max_risk'])))} and an average warning area of {_latex_escape(_fmt(float(current_metrics['avg_warning_area_nm2'])))} nm2, while \\texttt{{{_latex_escape(best_scenario_name)}}} yielded the smallest average warning area at {_latex_escape(_fmt(float(best_scenario_metrics['avg_warning_area_nm2'])))} nm2. Ablation analysis further showed that \\texttt{{{_latex_escape(strongest_ablation_name)}}} caused the largest warning-area shift relative to the baseline ({_latex_escape(_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline'])))} nm2), indicating that the rule-based design remains structurally interpretable. The package is intended as an AIS-only risk awareness and scenario-comparison tool, not as an autonomous collision-avoidance controller.
\\end{{abstract}}"""


def build_paper_introduction_latex(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
) -> str:
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""\\section{{Introduction}}

AIS-based maritime risk analysis is often reported as a list of pairwise vessel conflict indicators such as distance, DCPA, TCPA, or encounter type. That view is useful, but it does not directly answer an operator-facing question: which surrounding direction or sea area is currently more hazardous for the own ship. This project addresses that gap by converting AIS-only traffic snapshots into an own-ship-centric spatial risk representation.

The proposed system focuses on a practical MVP baseline that can be implemented with public AIS data. It reconstructs traffic snapshots, computes relative-motion features, scores pairwise interactions with explainable rules, and aggregates them into grid-based heatmaps and contours. In the current sample package, the recommended evaluation set produced an average current max risk of {_latex_escape(_fmt(float(current_metrics['avg_max_risk'])))} and an average current warning area of {_latex_escape(_fmt(float(current_metrics['avg_warning_area_nm2'])))} nm2.

\\subsection{{Contributions}}

\\begin{{itemize}}
\\item It extends pairwise AIS risk analysis into an own-ship-centric spatial risk map and contour representation.
\\item It compares slowdown/current/speedup scenarios within the same traffic snapshot to show how surrounding risk geometry changes.
\\item It prioritizes an explainable rule-based baseline that is realistic for public AIS-only research and MVP implementation.
\\end{{itemize}}
"""


def build_paper_conclusion_latex(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    return f"""\\section{{Conclusion}}

This package demonstrates that an AIS-only rule-based baseline can support own-ship-centric spatial risk mapping without overclaiming autonomy. The generated heatmaps, contours, and scenario comparisons show a feasible path from public AIS preprocessing to interpretable risk visualization. In the current sample, \\texttt{{{_latex_escape(best_scenario_name)}}} yielded the smallest average warning area at {_latex_escape(_fmt(float(best_scenario_metrics['avg_warning_area_nm2'])))} nm2, while \\texttt{{{_latex_escape(strongest_ablation_name)}}} produced the largest warning-area delta relative to baseline ({_latex_escape(_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline'])))} nm2), reinforcing the structural value of the explainable baseline design.

The main practical implication is not that the system finds a universal maneuver rule, but that it provides a spatially legible comparison layer for maritime decision support. Future work should validate the same baseline over additional sea areas and add lightweight ML comparators only after the AIS-only rule-based reference is stable and well understood.
"""


def build_paper_claim_matrix_rows(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> list[dict[str, object]]:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return [
        {
            "claim_id": "C1",
            "claim_type": "supported",
            "claim_text": "AIS-only traffic snapshots can be transformed into own-ship-centric spatial risk heatmaps and contours.",
            "evidence": "figure bundle, case SVGs, results section",
            "evidence_detail": f"current avg max risk {_fmt(float(current_metrics['avg_max_risk']))}, case count {manifest['case_count']}",
            "guardrail": "Comparative decision-support visualization only; not certified navigation advice.",
        },
        {
            "claim_id": "C2",
            "claim_type": "supported",
            "claim_text": "Speed scenarios materially change the surrounding warning-area geometry within the same traffic snapshot.",
            "evidence": "scenario table, results section",
            "evidence_detail": f"{best_scenario_name} avg warning area {_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))} nm2",
            "guardrail": "Do not present as a universal speed policy or maneuver recommendation.",
        },
        {
            "claim_id": "C3",
            "claim_type": "supported",
            "claim_text": "The rule-based baseline remains structurally interpretable through ablation and explicit factor weights.",
            "evidence": "ablation table, methods section",
            "evidence_detail": f"{strongest_ablation_name} delta warning area {_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))} nm2",
            "guardrail": "Interpretable baseline evidence, not proof that ML is unnecessary in all settings.",
        },
        {
            "claim_id": "C4",
            "claim_type": "must_not_overclaim",
            "claim_text": "The package does not estimate intent, radar contacts, legal safety boundaries, or autonomous control actions.",
            "evidence": "methods/discussion guardrails",
            "evidence_detail": "AIS-only scope and non-goal statements",
            "guardrail": "Explicitly keep claims within AIS-only risk awareness and scenario comparison.",
        },
        {
            "claim_id": "C5",
            "claim_type": "limitation",
            "claim_text": "Current validation does not prove generalization across all sea areas, traffic regimes, or vessel classes.",
            "evidence": "discussion limitations",
            "evidence_detail": "sample workflow uses recommended cases from one available dataset",
            "guardrail": "Treat multi-area validation as future work before making broad deployment claims.",
        },
    ]


def build_paper_claim_matrix_rows_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> list[dict[str, object]]:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return [
        {
            "claim_id": "C1",
            "claim_type": "supported",
            "claim_text": "AIS-only 교통 snapshot을 자선 중심 spatial risk heatmap과 contour로 변환할 수 있다.",
            "evidence": "figure bundle, case SVG, results section",
            "evidence_detail": f"current avg max risk {_fmt(float(current_metrics['avg_max_risk']))}, case count {manifest['case_count']}",
            "guardrail": "비교용 의사결정 지원 시각화이지 인증 항해 조언이 아니다.",
        },
        {
            "claim_id": "C2",
            "claim_type": "supported",
            "claim_text": "동일 traffic snapshot 내 속력 시나리오 변화는 주변 warning-area 형상을 실질적으로 바꾼다.",
            "evidence": "scenario table, results section",
            "evidence_detail": f"{best_scenario_name} avg warning area {_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))} nm2",
            "guardrail": "보편적 속력 정책이나 조선 권고로 설명하면 안 된다.",
        },
        {
            "claim_id": "C3",
            "claim_type": "supported",
            "claim_text": "규칙 기반 baseline은 ablation과 명시적 factor weight를 통해 구조적으로 설명 가능하다.",
            "evidence": "ablation table, methods section",
            "evidence_detail": f"{strongest_ablation_name} delta warning area {_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))} nm2",
            "guardrail": "설명 가능한 baseline 근거이지, 모든 상황에서 ML이 불필요하다는 뜻은 아니다.",
        },
        {
            "claim_id": "C4",
            "claim_type": "must_not_overclaim",
            "claim_text": "본 패키지는 intent, radar contact, 법적 안전 경계, autonomous control action을 추정하지 않는다.",
            "evidence": "methods/discussion guardrails",
            "evidence_detail": "AIS-only scope and non-goal statements",
            "guardrail": "주장은 AIS-only 위험 인지 및 scenario comparison 범위로 제한해야 한다.",
        },
        {
            "claim_id": "C5",
            "claim_type": "limitation",
            "claim_text": "현재 검증은 모든 해역, 교통 조건, 선종으로의 일반화를 입증하지 않는다.",
            "evidence": "discussion limitations",
            "evidence_detail": "sample workflow uses recommended cases from one available dataset",
            "guardrail": "다해역 검증 전에는 광범위한 배포 주장을 피해야 한다.",
        },
    ]


def build_paper_reviewer_faq(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    return f"""# Paper Reviewer FAQ

## Q1. What is the practical novelty of this work?

The novelty is not autonomous control. The contribution is an own-ship-centric spatial risk representation that extends pairwise AIS risk indicators into heatmaps and contours that can be compared by direction and area.

## Q2. Why use a rule-based baseline instead of a deep model first?

The project is intentionally scoped to public AIS-only data and prioritizes explanation. The ablation result shows that `{strongest_ablation_name}` changes warning area by `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2, which means the baseline exposes meaningful structural factors rather than hiding them.

## Q3. What can actually be claimed from the scenario comparison?

The supported claim is that speed changes reshape the spatial warning envelope within the same traffic snapshot. In this sample, `{best_scenario_name}` has the smallest average warning area at `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2. It should not be sold as a universal maneuver rule.

## Q4. What are the main limitations of AIS-only validation?

AIS-only validation cannot confirm intent, radar-only contacts, visibility, sea state, or helm actions. The contours are comparative internal indicators, not legal safety boundaries.

## Q5. What is the strongest next step for research?

The next step is cross-area validation of the same rule-based baseline. A lightweight ML comparator is reasonable only after the AIS-only baseline is stable, interpretable, and benchmarked across multiple traffic regimes.
"""


def build_paper_reviewer_faq_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    return f"""# 논문 Reviewer FAQ

## Q1. 이 작업의 실질적 차별점은 무엇인가?

차별점은 autonomous control이 아니다. 핵심 기여는 pairwise AIS 위험 지표를 방향성과 면적 기준으로 비교 가능한 자선 중심 heatmap과 contour로 확장한 spatial representation에 있다.

## Q2. 왜 처음부터 딥러닝이 아니라 규칙 기반 baseline을 썼는가?

본 프로젝트는 공개 AIS-only 데이터 범위에 맞춰 설명 가능성을 우선했다. Ablation 결과에서 `{strongest_ablation_name}`은 warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 변화시켜, baseline이 의미 있는 구조 요소를 드러낸다는 점을 보여준다.

## Q3. 시나리오 비교로 실제로 무엇을 주장할 수 있는가?

지원 가능한 주장은 자선 속력 변화가 동일 traffic snapshot 내 spatial warning envelope를 바꾼다는 점이다. 현재 sample에서는 `{best_scenario_name}`가 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았다. 이를 보편적 조선 규칙으로 설명하면 안 된다.

## Q4. AIS-only 검증의 핵심 한계는 무엇인가?

AIS-only 검증만으로는 intent, radar-only contact, 시계, 해상 상태, helm action을 확인할 수 없다. 생성된 contour도 비교용 내부 지표이지 법적 안전 경계가 아니다.

## Q5. 연구 측면에서 가장 강한 다음 단계는 무엇인가?

다음 단계는 동일한 규칙 기반 baseline을 여러 해역에 적용해 cross-area validation을 수행하는 것이다. 경량 ML comparator는 AIS-only baseline이 충분히 안정적이고 설명 가능하며 다중 traffic regime에서 benchmark된 뒤에야 비교안으로 붙이는 것이 타당하다.
"""


def build_presentation_outline(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# Presentation Outline

## Slide 1. Problem

- Pairwise AIS indicators do not directly show which surrounding sea area is more hazardous for the own ship.
- Operators and reviewers need a spatial representation, not only a ranked vessel list.

## Slide 2. Scope And Guardrails

- Data scope: AIS-only public traffic data.
- Output scope: risk awareness, heatmap, contour, and speed-scenario comparison.
- Non-goals: autonomous control, certified collision avoidance, legal safety boundary estimation.

## Slide 3. Baseline Approach

- Reconstruct traffic snapshots.
- Compute relative-motion features: distance, bearing, relative speed, DCPA, TCPA, encounter type.
- Score pairwise risk with an explainable rule-based baseline.
- Aggregate vessel risk into own-ship-centric grid heatmaps and contours.

## Slide 4. Main Results

- Recommended case count: `{manifest['case_count']}`.
- Current avg max risk: `{_fmt(float(current_metrics['avg_max_risk']))}`.
- Current avg warning area: `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2.
- Use case figures to show directional redistribution rather than only vessel ranking.

## Slide 5. Scenario Comparison

- `{best_scenario_name}` yielded the smallest average warning area: `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2.
- Claim carefully: this is scenario-sensitive comparative evidence, not a universal maneuver rule.

## Slide 6. Explainability And Ablation

- `{strongest_ablation_name}` caused the largest warning-area delta: `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2.
- This supports the argument that the baseline exposes structurally meaningful factors.

## Slide 7. Limitations

- AIS-only validation cannot confirm intent, radar-only contacts, sea state, or helm actions.
- Current sample does not prove generalization across all sea areas and vessel classes.

## Slide 8. Why This Project Matters

- Practical MVP with public AIS only.
- Strong portfolio value because outputs are visual, explainable, and end-to-end reproducible.
- Research value because it extends pairwise risk analysis into spatial risk mapping and scenario comparison.
"""


def build_presentation_outline_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# 발표 개요

## Slide 1. 문제 정의

- Pairwise AIS 지표만으로는 자선 주변 어느 해역이 더 위험한지 직관적으로 보이지 않는다.
- 항해 의사결정과 연구 심사 모두 vessel list보다 spatial representation을 필요로 한다.

## Slide 2. 범위와 가드레일

- 데이터 범위: 공개 AIS-only 교통 데이터.
- 출력 범위: 위험 인지, heatmap, contour, 속력 시나리오 비교.
- 비목표: autonomous control, 인증 충돌회피, 법적 안전 경계 추정.

## Slide 3. Baseline 접근

- 교통 snapshot 재구성.
- 상대운동 feature 계산: distance, bearing, relative speed, DCPA, TCPA, encounter type.
- 설명 가능한 규칙 기반 baseline으로 pairwise risk score 계산.
- vessel risk를 자선 중심 grid heatmap과 contour로 집계.

## Slide 4. 핵심 결과

- 추천 사례 수: `{manifest['case_count']}`.
- Current avg max risk: `{_fmt(float(current_metrics['avg_max_risk']))}`.
- Current avg warning area: `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2.
- 사례 figure는 vessel ranking이 아니라 방향별 spatial redistribution 설명에 사용한다.

## Slide 5. 시나리오 비교

- `{best_scenario_name}` 시나리오는 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았다.
- 단, 이것은 보편적 조선 규칙이 아니라 scenario-sensitive comparative evidence로 설명해야 한다.

## Slide 6. 설명 가능성과 Ablation

- `{strongest_ablation_name}`은 warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 가장 크게 변화시켰다.
- 이는 baseline이 구조적으로 의미 있는 factor를 드러낸다는 근거가 된다.

## Slide 7. 한계

- AIS-only 검증으로는 intent, radar-only contact, sea state, helm action을 확인할 수 없다.
- 현재 sample만으로 모든 해역과 선종에 대한 일반화를 주장할 수 없다.

## Slide 8. 왜 의미 있는 프로젝트인가

- 공개 AIS만으로 구현 가능한 실용적 MVP다.
- 시각적이고 설명 가능한 결과물이 있어 포트폴리오 가치가 높다.
- Pairwise risk 분석을 spatial risk mapping과 scenario comparison으로 확장해 연구 기여도도 갖는다.
"""


def build_demo_talk_track(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# Demo Talk Track

## 1. Opening

This demo focuses on AIS-only maritime decision support. The goal is not autonomous navigation, but a spatial answer to a practical question: which surrounding area is riskier for the own ship right now?

## 2. What The User Sees

The dashboard shows own-ship-centered heatmaps, contours, and slowdown/current/speedup comparisons from the same traffic snapshot. Instead of reading only pairwise CPA/TCPA values, the user can inspect where elevated risk is concentrated in space.

## 3. What The Baseline Does

The system reconstructs traffic snapshots, computes relative-motion features, applies an explainable rule-based risk score, and aggregates those vessel-level interactions into a spatial grid. This keeps the MVP realistic for public AIS data and makes the logic reviewable.

## 4. What The Current Sample Shows

In this sample package, the recommended evaluation set contains `{manifest['case_count']}` cases. The current scenario yields an average max risk of `{_fmt(float(current_metrics['avg_max_risk']))}` and an average warning area of `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2. `{best_scenario_name}` shows the smallest average warning area at `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2.

## 5. Why The Ablation Matters

The explainability check matters because `{strongest_ablation_name}` changes warning area by `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2. That means the baseline is not just outputting a score; it reveals which factors materially reshape the contour.

## 6. What I Would Claim Carefully

I would claim that AIS-only speed scenarios reshape the surrounding spatial warning envelope and that this representation is useful for explainable decision support. I would not claim autonomous control, legal safety advice, or universal maneuver recommendations.

## 7. Closing

The practical value is that the project is implementable with public AIS data, visually compelling for demos, and structured enough for thesis or paper extension. The next step is cross-area validation, not premature escalation to opaque deep learning.
"""


def build_demo_talk_track_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# Demo 발표 스크립트

## 1. 오프닝

이 데모는 AIS-only 해양 의사결정 지원에 초점을 둡니다. 목표는 완전자율운항이 아니라, “지금 자선 주변 어느 방향이 더 위험한가”를 공간적으로 보여주는 것입니다.

## 2. 사용자가 보는 것

대시보드는 같은 traffic snapshot에 대해 자선 중심 heatmap, contour, slowdown/current/speedup 비교를 보여줍니다. 사용자는 pairwise CPA/TCPA 숫자만 읽는 대신, 고위험 영역이 공간적으로 어디에 몰려 있는지 볼 수 있습니다.

## 3. Baseline이 하는 일

시스템은 교통 snapshot을 재구성하고, 상대운동 feature를 계산한 뒤, 설명 가능한 규칙 기반 risk score를 적용하고, 이를 spatial grid로 집계합니다. 이렇게 해야 공개 AIS 데이터만으로도 현실적인 MVP가 되고, 로직 검토도 가능합니다.

## 4. 현재 sample이 보여주는 것

현재 sample package에는 추천 사례 `{manifest['case_count']}`개가 들어 있습니다. Current scenario의 평균 max risk는 `{_fmt(float(current_metrics['avg_max_risk']))}`이고, 평균 warning area는 `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2입니다. `{best_scenario_name}`는 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작게 나타났습니다.

## 5. Ablation이 중요한 이유

설명 가능성 점검에서 `{strongest_ablation_name}`은 warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 변화시켰습니다. 즉 baseline은 단순히 score만 내는 것이 아니라, 어떤 factor가 contour를 실질적으로 바꾸는지도 보여줍니다.

## 6. 무엇을 조심해서 주장할 것인가

저는 AIS-only 속력 시나리오가 주변 spatial warning envelope를 바꾼다고 주장할 것입니다. 그리고 이런 표현이 설명 가능한 의사결정 지원에 유용하다고 설명할 것입니다. 반대로 autonomous control, 법적 안전 조언, 보편적 조선 규칙이라고는 주장하지 않을 것입니다.

## 7. 마무리

이 프로젝트의 실무적 가치는 공개 AIS만으로 구현 가능하고, 시각 결과물이 강하며, 논문과 포트폴리오로 확장 가능한 구조를 가졌다는 점입니다. 다음 단계는 불투명한 딥러닝 확대가 아니라, 다해역 검증입니다.
"""


def build_defense_packet(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
    claim_matrix_rows: list[dict[str, object]],
    reviewer_faq: str,
    presentation_outline: str,
    demo_talk_track: str,
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    supported_claims = [row for row in claim_matrix_rows if row["claim_type"] == "supported"]
    guardrail_claims = [row for row in claim_matrix_rows if row["claim_type"] != "supported"]
    lines = [
        "# Defense Packet",
        "",
        "## 30-Second Pitch",
        "",
        f"This project converts AIS-only traffic snapshots into own-ship-centric spatial risk heatmaps and contours. "
        f"It does not attempt autonomous control; it provides explainable decision-support evidence. "
        f"In the current sample, `{best_scenario_name}` yields the smallest average warning area at `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2, "
        f"and `{strongest_ablation_name}` changes warning area by `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2, showing that the baseline is structurally interpretable.",
        "",
        "## What To Claim",
        "",
    ]
    for row in supported_claims:
        lines.append(f"- {row['claim_id']}: {row['claim_text']}")
        lines.append(f"  Evidence: {row['evidence']} | {row['evidence_detail']}")
    lines.extend(
        [
            "",
            "## What Not To Overclaim",
            "",
        ]
    )
    for row in guardrail_claims:
        lines.append(f"- {row['claim_id']}: {row['claim_text']}")
        lines.append(f"  Guardrail: {row['guardrail']}")
    lines.extend(
        [
            "",
            "## Recommended Demo Flow",
            "",
            "\n".join(_strip_markdown_headings(presentation_outline)).strip(),
            "",
            "## Talk Track",
            "",
            "\n".join(_strip_markdown_headings(demo_talk_track)).strip(),
            "",
            "## Reviewer FAQ",
            "",
            "\n".join(_strip_markdown_headings(reviewer_faq)).strip(),
            "",
        ]
    )
    return "\n".join(lines)


def build_defense_packet_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
    claim_matrix_rows: list[dict[str, object]],
    reviewer_faq_ko: str,
    presentation_outline_ko: str,
    demo_talk_track_ko: str,
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    supported_claims = [row for row in claim_matrix_rows if row["claim_type"] == "supported"]
    guardrail_claims = [row for row in claim_matrix_rows if row["claim_type"] != "supported"]
    lines = [
        "# Defense Packet (KO)",
        "",
        "## 30초 설명",
        "",
        f"이 프로젝트는 AIS-only 교통 snapshot을 자선 중심 spatial risk heatmap과 contour로 변환합니다. "
        f"완전자율 제어를 목표로 하지 않고, 설명 가능한 의사결정 지원 근거를 제공합니다. "
        f"현재 sample에서는 `{best_scenario_name}`가 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았고, "
        f"`{strongest_ablation_name}`은 warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2만큼 변화시켜 baseline의 구조적 설명 가능성을 보여줍니다.",
        "",
        "## 주장해도 되는 것",
        "",
    ]
    for row in supported_claims:
        lines.append(f"- {row['claim_id']}: {row['claim_text']}")
        lines.append(f"  근거: {row['evidence']} | {row['evidence_detail']}")
    lines.extend(
        [
            "",
            "## 과장하면 안 되는 것",
            "",
        ]
    )
    for row in guardrail_claims:
        lines.append(f"- {row['claim_id']}: {row['claim_text']}")
        lines.append(f"  가드레일: {row['guardrail']}")
    lines.extend(
        [
            "",
            "## 추천 발표 흐름",
            "",
            "\n".join(_strip_markdown_headings(presentation_outline_ko)).strip(),
            "",
            "## 발표 스크립트",
            "",
            "\n".join(_strip_markdown_headings(demo_talk_track_ko)).strip(),
            "",
            "## Reviewer FAQ",
            "",
            "\n".join(_strip_markdown_headings(reviewer_faq_ko)).strip(),
            "",
        ]
    )
    return "\n".join(lines)


def build_portfolio_case_study(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# Portfolio Case Study

## Project Snapshot

- Project: `{manifest.get('project_name', manifest['package_name'])}`
- Scope: AIS-only own-ship-centric spatial risk mapping
- Output: heatmap, contour, scenario comparison, explainable baseline, end-to-end dashboard/demo package

## Problem

Most AIS risk demos stop at pairwise vessel indicators. That is useful for analysis, but it does not clearly show which surrounding area is currently riskier for the own ship. I wanted a project that was realistic with public data and still produced a spatially legible decision-support output.

## Constraints

- Public AIS only
- No simulator or private bridge-command data
- Explainability mattered more than black-box accuracy claims
- Needed to be implementable as a solo MVP and expandable into a paper/demo

## Product And Technical Decision

I chose a rule-based baseline first instead of jumping to ML. The system reconstructs traffic snapshots, computes relative-motion features, scores pairwise conflict with explicit weights, and aggregates the result into a local spatial grid around the own ship. This made the MVP feasible, reviewable, and easier to defend.

## What I Built

- Raw AIS preprocessing and schema inspection
- Trajectory reconstruction and own-ship snapshot extraction
- Rule-based pairwise risk scoring with DCPA/TCPA/bearing/density factors
- Grid heatmap and threshold contour generation
- Slowdown/current/speedup scenario comparison
- Experiment, ablation, report, dashboard, and demo package pipeline

## Results

In the current sample package, `{manifest['case_count']}` recommended cases were selected automatically. The `current` scenario produced an average max risk of `{_fmt(float(current_metrics['avg_max_risk']))}` and an average warning area of `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2. `{best_scenario_name}` yielded the smallest average warning area at `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2. The strongest ablation effect came from `{strongest_ablation_name}`, which changed warning area by `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2.

## Why This Is Strong Portfolio Material

- It solves a real domain problem under realistic data constraints.
- The outputs are visual and easy to demo.
- The architecture is end-to-end: ingestion, modeling, experimentation, export, and dashboard.
- The project has clear guardrails and does not overclaim autonomy.

## Limits And Next Steps

The package is AIS-only and cannot validate intent, radar-only contacts, or certified maneuver safety. The strongest next step is cross-area validation of the same baseline, followed by lightweight ML comparison only after the explainable baseline is stable.
"""


def build_portfolio_case_study_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# Portfolio Case Study

## 프로젝트 요약

- 프로젝트: `{manifest.get('project_name', manifest['package_name'])}`
- 범위: AIS-only 자선 중심 spatial risk mapping
- 출력: heatmap, contour, scenario comparison, 설명 가능한 baseline, end-to-end dashboard/demo package

## 문제 정의

대부분의 AIS 위험도 데모는 pairwise vessel indicator 수준에서 멈춘다. 이는 분석에는 유용하지만, 자선 주변 어느 해역이 더 위험한지를 직관적으로 보여주지 못한다. 나는 공개 데이터만으로 현실적으로 구현 가능하면서도 spatially legible한 의사결정 지원 출력을 만드는 프로젝트를 목표로 했다.

## 제약조건

- 공개 AIS만 사용
- 시뮬레이터와 비공개 bridge-command 데이터 없음
- black-box accuracy 주장보다 설명 가능성이 중요
- 1인 MVP로 구현 가능하면서 논문/데모로 확장 가능해야 함

## 제품·기술 의사결정

처음부터 ML로 가지 않고 규칙 기반 baseline을 먼저 선택했다. 시스템은 교통 snapshot을 재구성하고, 상대운동 feature를 계산하며, 명시적 가중치로 pairwise conflict를 점수화한 뒤, 이를 자선 주변 local grid로 집계한다. 이 방식은 MVP를 현실적으로 만들고, 로직 검토와 방어를 쉽게 한다.

## 내가 구현한 것

- Raw AIS 전처리 및 schema inspection
- Trajectory reconstruction 및 own-ship snapshot 추출
- DCPA/TCPA/bearing/density 기반 규칙형 pairwise risk scoring
- Grid heatmap 및 threshold contour 생성
- Slowdown/current/speedup 시나리오 비교
- Experiment, ablation, report, dashboard, demo package 파이프라인

## 결과

현재 sample package에서는 `{manifest['case_count']}`개 추천 사례가 자동 선택되었다. `current` 시나리오는 평균 max risk `{_fmt(float(current_metrics['avg_max_risk']))}`와 평균 warning area `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2를 보였다. `{best_scenario_name}` 시나리오는 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았다. 가장 큰 ablation 효과는 `{strongest_ablation_name}`에서 나왔고, warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2 변화시켰다.

## 왜 포트폴리오 가치가 높은가

- 현실적인 데이터 제약 안에서 실제 도메인 문제를 풀었다.
- 출력이 시각적이라 데모 전달력이 높다.
- ingestion, modeling, experimentation, export, dashboard까지 end-to-end 구조를 갖췄다.
- 자율운항을 과장하지 않고 guardrail이 분명하다.

## 한계와 다음 단계

이 패키지는 AIS-only이므로 intent, radar-only contact, 인증된 maneuver safety를 검증할 수 없다. 가장 강한 다음 단계는 같은 baseline을 여러 해역에서 검증하는 것이고, 그 다음에야 경량 ML comparator를 붙이는 것이 타당하다.
"""


def build_interview_answer_bank(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# Interview Answer Bank

## Q1. Why did you choose this problem?

I wanted a maritime AI project that stays realistic with public AIS data. Instead of overclaiming autonomy, I focused on a useful decision-support question: how to represent surrounding risk spatially around the own ship.

## Q2. Why not start with machine learning?

Because the data and validation scope did not justify a black-box-first approach. A rule-based baseline was the right MVP because it is explainable, implementable with AIS only, and strong enough to benchmark later ML extensions.

## Q3. What is the main technical contribution?

The main contribution is extending pairwise AIS conflict scoring into an own-ship-centric spatial risk map and contour representation, with slowdown/current/speedup scenario comparison on the same traffic snapshot.

## Q4. How did you validate the baseline?

I validated it through case mining, package-level scenario aggregation, ablation analysis, and artifact generation. In the current sample, `current` has avg max risk `{_fmt(float(current_metrics['avg_max_risk']))}` and avg warning area `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2, while `{best_scenario_name}` has the smallest warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2.

## Q5. What made the baseline explainable?

The system uses explicit weights and interpretable factors such as distance, DCPA, TCPA, bearing, encounter type, and density. The ablation result shows that `{strongest_ablation_name}` changes warning area by `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2, which demonstrates structural interpretability.

## Q6. What are the main limits?

The package is AIS-only, so it cannot validate intent, radar-only contacts, weather, sea state, or helm actions. It also does not prove generalization across all sea areas.

## Q7. What would you do next?

I would first validate the same baseline across multiple sea areas and traffic regimes. Only after that would I add a lightweight ML comparator as a comparative extension.

## Q8. Why is this a strong portfolio project?

Because it is end-to-end, visual, domain-grounded, and carefully scoped. It combines product judgment, data engineering, explainable modeling, experimentation, and demo delivery in one artifact chain.
"""


def build_interview_answer_bank_ko(
    manifest: dict[str, object],
    experiment_data: dict[str, object],
    ablation_data: dict[str, object],
) -> str:
    best_scenario_name, best_scenario_metrics = _best_scenario(experiment_data)
    strongest_ablation_name, strongest_ablation_metrics = _strongest_current_ablation(ablation_data)
    current_metrics = experiment_data["scenario_averages"]["current"]
    return f"""# Interview Answer Bank

## Q1. 왜 이 문제를 선택했나요?

공개 AIS 데이터만으로도 현실적으로 구현 가능한 해양 AI 프로젝트를 만들고 싶었습니다. 자율운항을 과장하기보다, 자선 주변 위험을 공간적으로 표현하는 의사결정 지원 문제에 집중했습니다.

## Q2. 왜 처음부터 머신러닝으로 가지 않았나요?

데이터와 검증 범위가 black-box-first 접근을 정당화하지 못했기 때문입니다. 규칙 기반 baseline이야말로 AIS-only 환경에서 설명 가능하고 구현 가능하며, 이후 ML 확장을 비교할 기준선으로도 충분히 강하다고 판단했습니다.

## Q3. 이 프로젝트의 핵심 기술 기여는 무엇인가요?

핵심 기여는 pairwise AIS conflict scoring을 자선 중심 spatial risk map과 contour 표현으로 확장하고, 같은 traffic snapshot에서 slowdown/current/speedup 시나리오를 비교한 점입니다.

## Q4. baseline은 어떻게 검증했나요?

Case mining, package-level scenario aggregation, ablation 분석, 그리고 demo/report artifact 생성으로 검증했습니다. 현재 sample에서는 `current`의 avg max risk가 `{_fmt(float(current_metrics['avg_max_risk']))}`, avg warning area가 `{_fmt(float(current_metrics['avg_warning_area_nm2']))}` nm2이고, `{best_scenario_name}`가 평균 warning area `{_fmt(float(best_scenario_metrics['avg_warning_area_nm2']))}` nm2로 가장 작았습니다.

## Q5. 설명 가능성은 어떻게 확보했나요?

Distance, DCPA, TCPA, bearing, encounter type, density 같은 명시적 factor와 가중치를 사용했습니다. Ablation에서 `{strongest_ablation_name}`이 warning area를 `{_fmt(float(strongest_ablation_metrics['avg_delta_warning_area_vs_baseline']))}` nm2 변화시켰다는 점이 구조적 설명 가능성을 보여줍니다.

## Q6. 주요 한계는 무엇인가요?

이 패키지는 AIS-only이므로 intent, radar-only contact, weather, sea state, helm action을 검증할 수 없습니다. 또한 모든 해역에 대한 일반화도 아직 입증하지 못했습니다.

## Q7. 다음 단계는 무엇인가요?

우선 같은 baseline을 여러 해역과 교통 조건에서 검증할 것입니다. 그 다음에야 경량 ML comparator를 비교 확장안으로 붙이는 것이 타당합니다.

## Q8. 왜 포트폴리오 프로젝트로 강한가요?

End-to-end 구조이고, 시각 결과물이 강하며, 도메인 문제 정의가 분명하고, 제품 판단, 데이터 엔지니어링, 설명 가능한 모델링, 실험, 데모 전달까지 한 프로젝트에 모두 담겨 있기 때문입니다.
"""


def build_artifact_catalog_rows(
    manifest: dict[str, object],
    payload: dict[str, str],
) -> list[dict[str, object]]:
    output_root = Path(str(manifest["output_dir"]))
    catalog_specs = [
        ("demo", "all", "Demo package index", "index_path", "Entry point for the generated package.", "Open first to navigate outputs."),
        ("demo", "all", "Master report", "master_report_path", "Package-level experiment and ablation summary.", "Use for end-to-end technical demo review."),
        ("demo", "all", "Figure bundle", "figure_bundle_html_path", "Scenario SVG gallery for recommended cases.", "Use in visual walkthroughs and slide prep."),
        ("paper", "paper", "Paper full draft (EN)", "paper_full_draft_path", "Complete manuscript draft in markdown.", "Use for thesis/paper writing."),
        ("paper", "paper", "Paper full draft (KO)", "paper_full_draft_ko_path", "Complete manuscript draft in Korean markdown.", "Use for Korean proposal or advisor review."),
        ("paper", "paper", "Paper full draft (LaTeX)", "paper_full_draft_tex_path", "Complete manuscript draft in LaTeX.", "Use for conference or thesis template integration."),
        ("paper", "paper", "Claim matrix", "paper_claim_matrix_md_path", "Supported claims, overclaim guardrails, and evidence map.", "Use before writing abstract, slide claims, or conclusions."),
        ("paper", "paper", "Reviewer FAQ", "paper_reviewer_faq_path", "Likely reviewer questions with concise answers.", "Use for defense and paper revision prep."),
        ("presentation", "presentation", "Presentation outline", "presentation_outline_path", "Slide-by-slide structure for presentation.", "Use to build talk deck."),
        ("presentation", "presentation", "Demo talk track", "demo_talk_track_path", "Script for live dashboard/demo narration.", "Use during demo rehearsal."),
        ("defense", "defense", "Defense packet", "defense_packet_path", "Claims, guardrails, FAQ, and talk flow in one file.", "Use for professor/interviewer defense prep."),
        ("portfolio", "portfolio", "Portfolio case study", "portfolio_case_study_path", "Narrative case study for portfolio or blog.", "Use in portfolio page or README excerpt."),
        ("interview", "interview", "Interview answer bank", "interview_answer_bank_path", "Prepared answers for technical/project interviews.", "Use before interviews."),
    ]
    rows: list[dict[str, object]] = []
    merged_paths: dict[str, object] = {**manifest, **payload}
    for category, audience, artifact_name, key, purpose, recommended_use in catalog_specs:
        raw_path = merged_paths.get(key)
        if raw_path is None and key == "index_path":
            raw_path = output_root / "index.html"
        if raw_path is None:
            continue
        path = Path(str(raw_path))
        rows.append(
            {
                "category": category,
                "audience": audience,
                "artifact_name": artifact_name,
                "filename": path.name,
                "path_key": key,
                "purpose": purpose,
                "recommended_use": recommended_use,
            }
        )
    return rows


def _artifact_filename(references: dict[str, object], key: str) -> str:
    raw_path = references.get(key)
    if raw_path is None and key == "index_path" and "output_dir" in references:
        raw_path = Path(str(references["output_dir"])) / "index.html"
    if raw_path is None:
        return key
    return Path(str(raw_path)).name


def build_audience_guide(references: dict[str, object]) -> str:
    sections = [
        (
            "Professor / Advisor",
            [
                ("artifact_catalog_md_path", "전체 산출물 지도를 먼저 확인한다."),
                ("paper_full_draft_path", "논문 초안 전체를 빠르게 검토한다."),
                ("paper_claim_matrix_md_path", "주장 가능 범위와 guardrail을 확인한다."),
                ("paper_appendix_md_path", "표와 figure inventory를 본다."),
                ("master_report_path", "package-level 결과 요약을 확인한다."),
            ],
        ),
        (
            "Reviewer / Committee",
            [
                ("paper_full_draft_path", "논문 본문 전체를 읽는다."),
                ("paper_reviewer_faq_path", "예상 질문과 답변 포인트를 본다."),
                ("paper_claim_matrix_md_path", "과장 여부와 증거 연결을 확인한다."),
                ("paper_appendix_tex_path", "표/부록 통합용 LaTeX 자산을 본다."),
            ],
        ),
        (
            "Interviewer",
            [
                ("portfolio_case_study_path", "프로젝트를 짧게 파악한다."),
                ("interview_answer_bank_path", "질문 대비 답변을 본다."),
                ("defense_packet_path", "핵심 주장과 주의사항을 확인한다."),
                ("figure_bundle_html_path", "시각 결과를 빠르게 본다."),
            ],
        ),
        (
            "Recruiter / Hiring Manager",
            [
                ("portfolio_case_study_path", "프로젝트 스토리를 본다."),
                ("artifact_catalog_md_path", "산출물 범위를 본다."),
                ("figure_bundle_html_path", "시각 결과를 확인한다."),
            ],
        ),
        (
            "Live Demo Audience",
            [
                ("index_path", "패키지 첫 화면으로 진입한다."),
                ("presentation_outline_path", "발표 흐름을 따른다."),
                ("demo_talk_track_path", "시연 멘트를 맞춘다."),
                ("master_report_path", "질문이 나오면 aggregate 결과를 보여준다."),
            ],
        ),
    ]
    lines = ["# Audience Guide", ""]
    for audience_name, items in sections:
        lines.append(f"## {audience_name}")
        lines.append("")
        for index, (key, reason) in enumerate(items, start=1):
            lines.append(f"{index}. `{_artifact_filename(references, key)}`: {reason}")
        lines.append("")
    return "\n".join(lines)


def build_audience_guide_ko(references: dict[str, object]) -> str:
    sections = [
        (
            "교수 / 지도교수",
            [
                ("artifact_catalog_md_path", "전체 산출물 지도를 먼저 확인한다."),
                ("paper_full_draft_ko_path", "논문 초안 전체를 빠르게 검토한다."),
                ("paper_claim_matrix_ko_md_path", "주장 가능 범위와 guardrail을 확인한다."),
                ("paper_appendix_ko_md_path", "표와 figure inventory를 본다."),
                ("master_report_path", "package-level 결과 요약을 확인한다."),
            ],
        ),
        (
            "심사자 / 리뷰어",
            [
                ("paper_full_draft_path", "영문 논문 본문 전체를 읽는다."),
                ("paper_reviewer_faq_ko_path", "예상 질문과 답변 포인트를 본다."),
                ("paper_claim_matrix_ko_md_path", "과장 여부와 증거 연결을 확인한다."),
                ("paper_appendix_tex_path", "표/부록 통합용 LaTeX 자산을 본다."),
            ],
        ),
        (
            "면접관",
            [
                ("portfolio_case_study_ko_path", "프로젝트를 짧게 파악한다."),
                ("interview_answer_bank_ko_path", "질문 대비 답변을 본다."),
                ("defense_packet_ko_path", "핵심 주장과 주의사항을 확인한다."),
                ("figure_bundle_html_path", "시각 결과를 빠르게 본다."),
            ],
        ),
        (
            "채용 담당자 / 리뷰어",
            [
                ("portfolio_case_study_ko_path", "프로젝트 스토리를 본다."),
                ("artifact_catalog_ko_md_path", "산출물 범위를 본다."),
                ("figure_bundle_html_path", "시각 결과를 확인한다."),
            ],
        ),
        (
            "라이브 데모 청중",
            [
                ("index_path", "패키지 첫 화면으로 진입한다."),
                ("presentation_outline_ko_path", "발표 흐름을 따른다."),
                ("demo_talk_track_ko_path", "시연 멘트를 맞춘다."),
                ("master_report_path", "질문이 나오면 aggregate 결과를 보여준다."),
            ],
        ),
    ]
    lines = ["# Audience Guide (KO)", ""]
    for audience_name, items in sections:
        lines.append(f"## {audience_name}")
        lines.append("")
        for index, (key, reason) in enumerate(items, start=1):
            lines.append(f"{index}. `{_artifact_filename(references, key)}`: {reason}")
        lines.append("")
    return "\n".join(lines)


def build_handoff_checklist(payload: dict[str, str]) -> str:
    sections = [
        (
            "Paper Submission",
            [
                ("paper_full_draft_path", "Draft manuscript exists."),
                ("paper_claim_matrix_md_path", "Claim guardrails are documented."),
                ("paper_appendix_tex_path", "Appendix LaTeX asset exists."),
                ("paper_scenario_tex_path", "Scenario table LaTeX exists."),
                ("paper_ablation_tex_path", "Ablation table LaTeX exists."),
            ],
        ),
        (
            "Presentation",
            [
                ("presentation_outline_path", "Slide outline exists."),
                ("demo_talk_track_path", "Demo narration script exists."),
                ("figure_bundle_html_path", "Visual figure gallery exists."),
                ("defense_packet_path", "Defense summary packet exists."),
            ],
        ),
        (
            "Portfolio / Interview",
            [
                ("portfolio_case_study_path", "Portfolio story exists."),
                ("interview_answer_bank_path", "Interview answer bank exists."),
                ("artifact_catalog_md_path", "Artifact index exists."),
            ],
        ),
        (
            "Technical Demo",
            [
                ("index_path", "Demo package entry page exists."),
                ("master_report_path", "Aggregate master report exists."),
                ("paper_assets_manifest_path", "Paper asset manifest exists."),
            ],
        ),
    ]
    lines = ["# Handoff Checklist", ""]
    for section_name, items in sections:
        lines.append(f"## {section_name}")
        lines.append("")
        for key, description in items:
            filename = _artifact_filename(payload, key)
            lines.append(f"- [x] `{filename}`: {description}")
        lines.append("")
    return "\n".join(lines)


def build_handoff_checklist_ko(payload: dict[str, str]) -> str:
    sections = [
        (
            "논문 제출 준비",
            [
                ("paper_full_draft_ko_path", "논문 초안이 존재한다."),
                ("paper_claim_matrix_ko_md_path", "주장 가드레일이 정리돼 있다."),
                ("paper_appendix_tex_path", "부록 LaTeX 자산이 존재한다."),
                ("paper_scenario_tex_path", "Scenario 표 LaTeX가 존재한다."),
                ("paper_ablation_tex_path", "Ablation 표 LaTeX가 존재한다."),
            ],
        ),
        (
            "발표 준비",
            [
                ("presentation_outline_ko_path", "슬라이드 개요가 존재한다."),
                ("demo_talk_track_ko_path", "데모 발표 스크립트가 존재한다."),
                ("figure_bundle_html_path", "시각 figure gallery가 존재한다."),
                ("defense_packet_ko_path", "방어용 요약 패킷이 존재한다."),
            ],
        ),
        (
            "포트폴리오 / 면접 준비",
            [
                ("portfolio_case_study_ko_path", "포트폴리오 설명문이 존재한다."),
                ("interview_answer_bank_ko_path", "면접 답변집이 존재한다."),
                ("artifact_catalog_ko_md_path", "산출물 인덱스가 존재한다."),
            ],
        ),
        (
            "기술 데모 준비",
            [
                ("index_path", "Demo package 진입 페이지가 존재한다."),
                ("master_report_path", "Aggregate master report가 존재한다."),
                ("paper_assets_manifest_path", "Paper asset manifest가 존재한다."),
            ],
        ),
    ]
    lines = ["# Handoff Checklist (KO)", ""]
    for section_name, items in sections:
        lines.append(f"## {section_name}")
        lines.append("")
        for key, description in items:
            filename = _artifact_filename(payload, key)
            lines.append(f"- [x] `{filename}`: {description}")
        lines.append("")
    return "\n".join(lines)


def build_deliverable_readiness_summary(payload: dict[str, str]) -> str:
    return """# Deliverable Readiness Summary

- Status: ready_for_review
- Paper package: available
- Presentation package: available
- Defense package: available
- Portfolio package: available
- Interview package: available
- Remaining manual work: final wording edits, venue-specific formatting, and real-data validation expansion if needed
"""


def build_deliverable_readiness_summary_ko(payload: dict[str, str]) -> str:
    return """# Deliverable Readiness Summary (KO)

- 상태: ready_for_review
- 논문 패키지: 준비됨
- 발표 패키지: 준비됨
- 방어 패키지: 준비됨
- 포트폴리오 패키지: 준비됨
- 면접 패키지: 준비됨
- 남은 수작업: 최종 문구 다듬기, 제출 양식 맞춤, 필요 시 실제 데이터 검증 확대
"""


def _load_text_if_exists(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.exists():
        return ""
    return candidate.read_text(encoding="utf-8").strip()


def build_audience_pack(title: str, sections: list[tuple[str, str]]) -> str:
    lines = [f"# {title}", ""]
    for section_title, body in sections:
        if not body.strip():
            continue
        lines.append(f"## {section_title}")
        lines.append("")
        lines.append(body.strip())
        lines.append("")
    return "\n".join(lines)


def build_paper_full_draft_markdown(
    title: str,
    abstract_text: str,
    introduction_text: str,
    methods_text: str,
    results_text: str,
    discussion_text: str,
    conclusion_text: str,
) -> str:
    return "\n\n".join(
        [
            f"# {title}",
            _drop_first_markdown_heading(abstract_text),
            _drop_first_markdown_heading(introduction_text),
            _drop_first_markdown_heading(methods_text),
            _drop_first_markdown_heading(results_text),
            _drop_first_markdown_heading(discussion_text),
            _drop_first_markdown_heading(conclusion_text),
        ]
    ).strip() + "\n"


def build_paper_full_draft_latex(
    title: str,
    abstract_latex: str,
    introduction_latex: str,
    methods_latex: str,
    results_latex: str,
    discussion_latex: str,
    conclusion_latex: str,
) -> str:
    return f"""\\documentclass[11pt]{{article}}
\\usepackage[T1]{{fontenc}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{geometry}}
\\usepackage{{booktabs}}
\\usepackage[hidelinks]{{hyperref}}
\\geometry{{margin=1in}}

\\title{{{_latex_escape(title)}}}
\\date{{}}

\\begin{{document}}
\\maketitle

{abstract_latex}

{introduction_latex}

{methods_latex}

{results_latex}

{discussion_latex}

{conclusion_latex}

\\appendix
\\input{{paper_appendix.tex}}

\\end{{document}}
"""


def build_paper_appendix_markdown_ko(
    manifest: dict[str, object],
    case_rows: list[dict[str, object]],
    scenario_rows: list[dict[str, object]],
    ablation_rows: list[dict[str, object]],
    figure_rows: list[dict[str, object]],
    summary_note_ko: str,
    figure_captions_ko: str,
) -> str:
    sections = [
        "# 논문 부록 초안",
        "",
        "## 범위",
        "",
        f"- 패키지명: `{manifest['package_name']}`",
        f"- 사례 수: `{manifest['case_count']}`",
        f"- 반경(NM): `{manifest['radius_nm']:.1f}`",
        f"- 입력 CSV: `{manifest['input_path']}`",
        "",
        "## Figure Inventory",
        "",
        _table_markdown("Figure Inventory", figure_rows).replace("# Figure Inventory\n\n", "", 1).rstrip(),
        "",
        "## 결과 요약",
        "",
        "\n".join(_strip_markdown_headings(summary_note_ko)).strip(),
        "",
        "## 캡션 초안",
        "",
        "\n".join(_strip_markdown_headings(figure_captions_ko)).strip(),
        "",
        "## 부록 표",
        "",
        _table_markdown("Paper Case Table", case_rows).rstrip(),
        "",
        _table_markdown("Paper Scenario Table", scenario_rows).rstrip(),
        "",
        _table_markdown("Paper Current Ablation Table", ablation_rows).rstrip(),
        "",
    ]
    return "\n".join(sections)


def build_paper_assets_from_manifest(
    manifest: dict[str, object],
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    output_root = Path(output_dir) if output_dir is not None else Path(str(manifest["output_dir"]))
    experiment_data = _load_json(str(manifest["experiment_aggregate_path"]))
    ablation_data = _load_json(str(manifest["ablation_aggregate_path"]))

    case_rows = _case_table_rows(manifest)
    scenario_rows = _scenario_table_rows(experiment_data)
    ablation_rows = _ablation_table_rows(ablation_data, scenario_name="current")
    figure_rows = _figure_inventory_rows(manifest)
    figure_captions = build_paper_figure_captions(manifest, experiment_data, ablation_data)
    figure_captions_ko = build_paper_figure_captions_ko(manifest, experiment_data, ablation_data)
    summary_note = build_paper_summary_note(manifest, experiment_data, ablation_data)
    summary_note_ko = build_paper_summary_note_ko(manifest, experiment_data, ablation_data)
    abstract_text = build_paper_abstract(manifest, experiment_data, ablation_data)
    abstract_text_ko = build_paper_abstract_ko(manifest, experiment_data, ablation_data)
    introduction_text = build_paper_introduction(manifest, experiment_data)
    introduction_text_ko = build_paper_introduction_ko(manifest, experiment_data)
    results_section = build_paper_results_section(manifest, experiment_data, ablation_data)
    results_section_ko = build_paper_results_section_ko(manifest, experiment_data, ablation_data)
    methods_section = build_paper_methods_section(manifest)
    methods_section_ko = build_paper_methods_section_ko(manifest)
    discussion_section = build_paper_discussion_section(manifest, experiment_data, ablation_data)
    discussion_section_ko = build_paper_discussion_section_ko(manifest, experiment_data, ablation_data)
    conclusion_text = build_paper_conclusion(manifest, experiment_data, ablation_data)
    conclusion_text_ko = build_paper_conclusion_ko(manifest, experiment_data, ablation_data)
    manuscript_title = str(manifest.get("project_name", manifest["package_name"]))
    claim_matrix_rows = build_paper_claim_matrix_rows(manifest, experiment_data, ablation_data)
    claim_matrix_rows_ko = build_paper_claim_matrix_rows_ko(manifest, experiment_data, ablation_data)
    reviewer_faq = build_paper_reviewer_faq(manifest, experiment_data, ablation_data)
    reviewer_faq_ko = build_paper_reviewer_faq_ko(manifest, experiment_data, ablation_data)
    presentation_outline = build_presentation_outline(manifest, experiment_data, ablation_data)
    presentation_outline_ko = build_presentation_outline_ko(manifest, experiment_data, ablation_data)
    demo_talk_track = build_demo_talk_track(manifest, experiment_data, ablation_data)
    demo_talk_track_ko = build_demo_talk_track_ko(manifest, experiment_data, ablation_data)
    portfolio_case_study = build_portfolio_case_study(manifest, experiment_data, ablation_data)
    portfolio_case_study_ko = build_portfolio_case_study_ko(manifest, experiment_data, ablation_data)
    interview_answer_bank = build_interview_answer_bank(manifest, experiment_data, ablation_data)
    interview_answer_bank_ko = build_interview_answer_bank_ko(manifest, experiment_data, ablation_data)

    paper_case_csv_path = _write_csv(output_root / "paper_case_table.csv", case_rows, list(case_rows[0].keys()))
    paper_case_md_path = _write_text(output_root / "paper_case_table.md", _table_markdown("Paper Case Table", case_rows))
    paper_case_tex_path = _write_text(
        output_root / "paper_case_table.tex",
        _table_latex("Recommended own-ship evaluation cases.", "tab:recommended_cases", case_rows),
    )
    paper_scenario_csv_path = _write_csv(output_root / "paper_scenario_table.csv", scenario_rows, list(scenario_rows[0].keys()))
    paper_scenario_md_path = _write_text(output_root / "paper_scenario_table.md", _table_markdown("Paper Scenario Table", scenario_rows))
    paper_scenario_tex_path = _write_text(
        output_root / "paper_scenario_table.tex",
        _table_latex("Package-level scenario comparison.", "tab:scenario_comparison", scenario_rows),
    )
    paper_ablation_csv_path = _write_csv(output_root / "paper_ablation_current_table.csv", ablation_rows, list(ablation_rows[0].keys()))
    paper_ablation_md_path = _write_text(
        output_root / "paper_ablation_current_table.md",
        _table_markdown("Paper Current Ablation Table", ablation_rows),
    )
    paper_ablation_tex_path = _write_text(
        output_root / "paper_ablation_current_table.tex",
        _table_latex("Current-scenario ablation summary.", "tab:current_ablation", ablation_rows),
    )
    paper_claim_matrix_csv_path = _write_csv(
        output_root / "paper_claim_matrix.csv",
        claim_matrix_rows,
        list(claim_matrix_rows[0].keys()),
    )
    paper_claim_matrix_json_path = _table_json(output_root / "paper_claim_matrix.json", claim_matrix_rows)
    paper_claim_matrix_md_path = _write_text(
        output_root / "paper_claim_matrix.md",
        _table_markdown("Paper Claim Matrix", claim_matrix_rows),
    )
    paper_claim_matrix_ko_md_path = _write_text(
        output_root / "paper_claim_matrix_ko.md",
        _table_markdown("논문 Claim Matrix", claim_matrix_rows_ko),
    )
    paper_reviewer_faq_path = _write_text(
        output_root / "paper_reviewer_faq.md",
        reviewer_faq,
    )
    paper_reviewer_faq_ko_path = _write_text(
        output_root / "paper_reviewer_faq_ko.md",
        reviewer_faq_ko,
    )
    presentation_outline_path = _write_text(
        output_root / "presentation_outline.md",
        presentation_outline,
    )
    presentation_outline_ko_path = _write_text(
        output_root / "presentation_outline_ko.md",
        presentation_outline_ko,
    )
    demo_talk_track_path = _write_text(
        output_root / "demo_talk_track.md",
        demo_talk_track,
    )
    demo_talk_track_ko_path = _write_text(
        output_root / "demo_talk_track_ko.md",
        demo_talk_track_ko,
    )
    defense_packet_path = _write_text(
        output_root / "defense_packet.md",
        build_defense_packet(
            manifest=manifest,
            experiment_data=experiment_data,
            ablation_data=ablation_data,
            claim_matrix_rows=claim_matrix_rows,
            reviewer_faq=reviewer_faq,
            presentation_outline=presentation_outline,
            demo_talk_track=demo_talk_track,
        ),
    )
    defense_packet_ko_path = _write_text(
        output_root / "defense_packet_ko.md",
        build_defense_packet_ko(
            manifest=manifest,
            experiment_data=experiment_data,
            ablation_data=ablation_data,
            claim_matrix_rows=claim_matrix_rows_ko,
            reviewer_faq_ko=reviewer_faq_ko,
            presentation_outline_ko=presentation_outline_ko,
            demo_talk_track_ko=demo_talk_track_ko,
        ),
    )
    portfolio_case_study_path = _write_text(
        output_root / "portfolio_case_study.md",
        portfolio_case_study,
    )
    portfolio_case_study_ko_path = _write_text(
        output_root / "portfolio_case_study_ko.md",
        portfolio_case_study_ko,
    )
    interview_answer_bank_path = _write_text(
        output_root / "interview_answer_bank.md",
        interview_answer_bank,
    )
    interview_answer_bank_ko_path = _write_text(
        output_root / "interview_answer_bank_ko.md",
        interview_answer_bank_ko,
    )
    figure_captions_path = _write_text(
        output_root / "paper_figure_captions.md",
        figure_captions,
    )
    figure_captions_en_path = _write_text(
        output_root / "paper_figure_captions_en.md",
        figure_captions,
    )
    figure_captions_ko_path = _write_text(
        output_root / "paper_figure_captions_ko.md",
        figure_captions_ko,
    )
    paper_summary_path = _write_text(
        output_root / "paper_summary_note.md",
        summary_note,
    )
    paper_summary_en_path = _write_text(
        output_root / "paper_summary_note_en.md",
        summary_note,
    )
    paper_summary_ko_path = _write_text(
        output_root / "paper_summary_note_ko.md",
        summary_note_ko,
    )
    paper_abstract_path = _write_text(
        output_root / "paper_abstract.md",
        abstract_text,
    )
    paper_abstract_en_path = _write_text(
        output_root / "paper_abstract_en.md",
        abstract_text,
    )
    paper_abstract_ko_path = _write_text(
        output_root / "paper_abstract_ko.md",
        abstract_text_ko,
    )
    paper_introduction_path = _write_text(
        output_root / "paper_introduction_section.md",
        introduction_text,
    )
    paper_introduction_en_path = _write_text(
        output_root / "paper_introduction_section_en.md",
        introduction_text,
    )
    paper_introduction_ko_path = _write_text(
        output_root / "paper_introduction_section_ko.md",
        introduction_text_ko,
    )
    paper_results_path = _write_text(
        output_root / "paper_results_section.md",
        results_section,
    )
    paper_results_en_path = _write_text(
        output_root / "paper_results_section_en.md",
        results_section,
    )
    paper_results_ko_path = _write_text(
        output_root / "paper_results_section_ko.md",
        results_section_ko,
    )
    paper_results_tex_path = _write_text(
        output_root / "paper_results_section.tex",
        build_paper_results_section_latex(
            manifest=manifest,
            experiment_data=experiment_data,
            ablation_data=ablation_data,
        ),
    )
    paper_methods_path = _write_text(
        output_root / "paper_methods_section.md",
        methods_section,
    )
    paper_methods_en_path = _write_text(
        output_root / "paper_methods_section_en.md",
        methods_section,
    )
    paper_methods_ko_path = _write_text(
        output_root / "paper_methods_section_ko.md",
        methods_section_ko,
    )
    paper_methods_tex_path = _write_text(
        output_root / "paper_methods_section.tex",
        build_paper_methods_section_latex(manifest),
    )
    paper_discussion_path = _write_text(
        output_root / "paper_discussion_section.md",
        discussion_section,
    )
    paper_discussion_en_path = _write_text(
        output_root / "paper_discussion_section_en.md",
        discussion_section,
    )
    paper_discussion_ko_path = _write_text(
        output_root / "paper_discussion_section_ko.md",
        discussion_section_ko,
    )
    paper_discussion_tex_path = _write_text(
        output_root / "paper_discussion_section.tex",
        build_paper_discussion_section_latex(
            manifest=manifest,
            experiment_data=experiment_data,
            ablation_data=ablation_data,
        ),
    )
    paper_conclusion_path = _write_text(
        output_root / "paper_conclusion_section.md",
        conclusion_text,
    )
    paper_conclusion_en_path = _write_text(
        output_root / "paper_conclusion_section_en.md",
        conclusion_text,
    )
    paper_conclusion_ko_path = _write_text(
        output_root / "paper_conclusion_section_ko.md",
        conclusion_text_ko,
    )
    paper_appendix_md_path = _write_text(
        output_root / "paper_appendix.md",
        build_paper_appendix_markdown(
            manifest=manifest,
            case_rows=case_rows,
            scenario_rows=scenario_rows,
            ablation_rows=ablation_rows,
            figure_rows=figure_rows,
            summary_note=summary_note,
            figure_captions=figure_captions,
        ),
    )
    paper_appendix_en_md_path = _write_text(
        output_root / "paper_appendix_en.md",
        build_paper_appendix_markdown(
            manifest=manifest,
            case_rows=case_rows,
            scenario_rows=scenario_rows,
            ablation_rows=ablation_rows,
            figure_rows=figure_rows,
            summary_note=summary_note,
            figure_captions=figure_captions,
        ),
    )
    paper_appendix_ko_md_path = _write_text(
        output_root / "paper_appendix_ko.md",
        build_paper_appendix_markdown_ko(
            manifest=manifest,
            case_rows=case_rows,
            scenario_rows=scenario_rows,
            ablation_rows=ablation_rows,
            figure_rows=figure_rows,
            summary_note_ko=summary_note_ko,
            figure_captions_ko=figure_captions_ko,
        ),
    )
    paper_appendix_tex_path = _write_text(
        output_root / "paper_appendix.tex",
        build_paper_appendix_latex(
            manifest=manifest,
            figure_rows=figure_rows,
            summary_note=summary_note,
            figure_captions=figure_captions,
        ),
    )
    paper_full_draft_path = _write_text(
        output_root / "paper_full_draft.md",
        build_paper_full_draft_markdown(
            title=manuscript_title,
            abstract_text=abstract_text,
            introduction_text=introduction_text,
            methods_text=methods_section,
            results_text=results_section,
            discussion_text=discussion_section,
            conclusion_text=conclusion_text,
        ),
    )
    paper_full_draft_en_path = _write_text(
        output_root / "paper_full_draft_en.md",
        build_paper_full_draft_markdown(
            title=manuscript_title,
            abstract_text=abstract_text,
            introduction_text=introduction_text,
            methods_text=methods_section,
            results_text=results_section,
            discussion_text=discussion_section,
            conclusion_text=conclusion_text,
        ),
    )
    paper_full_draft_ko_path = _write_text(
        output_root / "paper_full_draft_ko.md",
        build_paper_full_draft_markdown(
            title=f"{manuscript_title} (KO)",
            abstract_text=abstract_text_ko,
            introduction_text=introduction_text_ko,
            methods_text=methods_section_ko,
            results_text=results_section_ko,
            discussion_text=discussion_section_ko,
            conclusion_text=conclusion_text_ko,
        ),
    )
    paper_full_draft_tex_path = _write_text(
        output_root / "paper_full_draft.tex",
        build_paper_full_draft_latex(
            title=manuscript_title,
            abstract_latex=build_paper_abstract_latex(manifest, experiment_data, ablation_data),
            introduction_latex=build_paper_introduction_latex(manifest, experiment_data),
            methods_latex=build_paper_methods_section_latex(manifest),
            results_latex=build_paper_results_section_latex(manifest, experiment_data, ablation_data),
            discussion_latex=build_paper_discussion_section_latex(manifest, experiment_data, ablation_data),
            conclusion_latex=build_paper_conclusion_latex(manifest, experiment_data, ablation_data),
        ),
    )

    payload = {
        "paper_case_csv_path": str(paper_case_csv_path),
        "paper_case_md_path": str(paper_case_md_path),
        "paper_case_tex_path": str(paper_case_tex_path),
        "paper_scenario_csv_path": str(paper_scenario_csv_path),
        "paper_scenario_md_path": str(paper_scenario_md_path),
        "paper_scenario_tex_path": str(paper_scenario_tex_path),
        "paper_ablation_csv_path": str(paper_ablation_csv_path),
        "paper_ablation_md_path": str(paper_ablation_md_path),
        "paper_ablation_tex_path": str(paper_ablation_tex_path),
        "paper_claim_matrix_csv_path": str(paper_claim_matrix_csv_path),
        "paper_claim_matrix_json_path": str(paper_claim_matrix_json_path),
        "paper_claim_matrix_md_path": str(paper_claim_matrix_md_path),
        "paper_claim_matrix_ko_md_path": str(paper_claim_matrix_ko_md_path),
        "paper_reviewer_faq_path": str(paper_reviewer_faq_path),
        "paper_reviewer_faq_ko_path": str(paper_reviewer_faq_ko_path),
        "presentation_outline_path": str(presentation_outline_path),
        "presentation_outline_ko_path": str(presentation_outline_ko_path),
        "demo_talk_track_path": str(demo_talk_track_path),
        "demo_talk_track_ko_path": str(demo_talk_track_ko_path),
        "defense_packet_path": str(defense_packet_path),
        "defense_packet_ko_path": str(defense_packet_ko_path),
        "portfolio_case_study_path": str(portfolio_case_study_path),
        "portfolio_case_study_ko_path": str(portfolio_case_study_ko_path),
        "interview_answer_bank_path": str(interview_answer_bank_path),
        "interview_answer_bank_ko_path": str(interview_answer_bank_ko_path),
        "paper_figure_captions_path": str(figure_captions_path),
        "paper_figure_captions_en_path": str(figure_captions_en_path),
        "paper_figure_captions_ko_path": str(figure_captions_ko_path),
        "paper_summary_note_path": str(paper_summary_path),
        "paper_summary_note_en_path": str(paper_summary_en_path),
        "paper_summary_note_ko_path": str(paper_summary_ko_path),
        "paper_abstract_path": str(paper_abstract_path),
        "paper_abstract_en_path": str(paper_abstract_en_path),
        "paper_abstract_ko_path": str(paper_abstract_ko_path),
        "paper_introduction_section_path": str(paper_introduction_path),
        "paper_introduction_section_en_path": str(paper_introduction_en_path),
        "paper_introduction_section_ko_path": str(paper_introduction_ko_path),
        "paper_results_section_path": str(paper_results_path),
        "paper_results_section_en_path": str(paper_results_en_path),
        "paper_results_section_ko_path": str(paper_results_ko_path),
        "paper_results_section_tex_path": str(paper_results_tex_path),
        "paper_methods_section_path": str(paper_methods_path),
        "paper_methods_section_en_path": str(paper_methods_en_path),
        "paper_methods_section_ko_path": str(paper_methods_ko_path),
        "paper_methods_section_tex_path": str(paper_methods_tex_path),
        "paper_discussion_section_path": str(paper_discussion_path),
        "paper_discussion_section_en_path": str(paper_discussion_en_path),
        "paper_discussion_section_ko_path": str(paper_discussion_ko_path),
        "paper_discussion_section_tex_path": str(paper_discussion_tex_path),
        "paper_conclusion_section_path": str(paper_conclusion_path),
        "paper_conclusion_section_en_path": str(paper_conclusion_en_path),
        "paper_conclusion_section_ko_path": str(paper_conclusion_ko_path),
        "paper_full_draft_path": str(paper_full_draft_path),
        "paper_full_draft_en_path": str(paper_full_draft_en_path),
        "paper_full_draft_ko_path": str(paper_full_draft_ko_path),
        "paper_full_draft_tex_path": str(paper_full_draft_tex_path),
        "paper_appendix_md_path": str(paper_appendix_md_path),
        "paper_appendix_en_md_path": str(paper_appendix_en_md_path),
        "paper_appendix_ko_md_path": str(paper_appendix_ko_md_path),
        "paper_appendix_tex_path": str(paper_appendix_tex_path),
    }
    artifact_catalog_rows = build_artifact_catalog_rows(manifest, payload)
    artifact_catalog_csv_path = _write_csv(
        output_root / "artifact_catalog.csv",
        artifact_catalog_rows,
        list(artifact_catalog_rows[0].keys()),
    )
    artifact_catalog_json_path = _table_json(output_root / "artifact_catalog.json", artifact_catalog_rows)
    artifact_catalog_md_path = _write_text(
        output_root / "artifact_catalog.md",
        _table_markdown("Artifact Catalog", artifact_catalog_rows),
    )
    artifact_catalog_ko_md_path = _write_text(
        output_root / "artifact_catalog_ko.md",
        _table_markdown("Artifact Catalog (KO)", artifact_catalog_rows),
    )
    payload.update(
        {
            "artifact_catalog_csv_path": str(artifact_catalog_csv_path),
            "artifact_catalog_json_path": str(artifact_catalog_json_path),
            "artifact_catalog_md_path": str(artifact_catalog_md_path),
            "artifact_catalog_ko_md_path": str(artifact_catalog_ko_md_path),
        }
    )
    handoff_checklist_path = _write_text(
        output_root / "handoff_checklist.md",
        build_handoff_checklist({**manifest, **payload}),
    )
    handoff_checklist_ko_path = _write_text(
        output_root / "handoff_checklist_ko.md",
        build_handoff_checklist_ko({**manifest, **payload}),
    )
    deliverable_readiness_path = _write_text(
        output_root / "deliverable_readiness.md",
        build_deliverable_readiness_summary({**manifest, **payload}),
    )
    deliverable_readiness_ko_path = _write_text(
        output_root / "deliverable_readiness_ko.md",
        build_deliverable_readiness_summary_ko({**manifest, **payload}),
    )
    payload.update(
        {
            "handoff_checklist_path": str(handoff_checklist_path),
            "handoff_checklist_ko_path": str(handoff_checklist_ko_path),
            "deliverable_readiness_path": str(deliverable_readiness_path),
            "deliverable_readiness_ko_path": str(deliverable_readiness_ko_path),
        }
    )
    guide_references = {**manifest, **payload}
    audience_guide_path = _write_text(
        output_root / "audience_guide.md",
        build_audience_guide(guide_references),
    )
    audience_guide_ko_path = _write_text(
        output_root / "audience_guide_ko.md",
        build_audience_guide_ko(guide_references),
    )
    payload.update(
        {
            "audience_guide_path": str(audience_guide_path),
            "audience_guide_ko_path": str(audience_guide_ko_path),
        }
    )
    advisor_review_pack_path = _write_text(
        output_root / "advisor_review_pack.md",
        build_audience_pack(
            "Advisor Review Pack",
            [
                ("Read First", _load_text_if_exists(audience_guide_path)),
                ("Deliverable Readiness", _load_text_if_exists(deliverable_readiness_path)),
                ("Claim Matrix", _load_text_if_exists(paper_claim_matrix_md_path)),
                ("Paper Full Draft", _load_text_if_exists(paper_full_draft_path)),
                ("Defense Packet", _load_text_if_exists(defense_packet_path)),
            ],
        ),
    )
    advisor_review_pack_ko_path = _write_text(
        output_root / "advisor_review_pack_ko.md",
        build_audience_pack(
            "Advisor Review Pack (KO)",
            [
                ("Read First", _load_text_if_exists(audience_guide_ko_path)),
                ("Deliverable Readiness", _load_text_if_exists(deliverable_readiness_ko_path)),
                ("Claim Matrix", _load_text_if_exists(paper_claim_matrix_ko_md_path)),
                ("Paper Full Draft", _load_text_if_exists(paper_full_draft_ko_path)),
                ("Defense Packet", _load_text_if_exists(defense_packet_ko_path)),
            ],
        ),
    )
    reviewer_pack_path = _write_text(
        output_root / "reviewer_pack.md",
        build_audience_pack(
            "Reviewer Pack",
            [
                ("Deliverable Readiness", _load_text_if_exists(deliverable_readiness_path)),
                ("Paper Full Draft", _load_text_if_exists(paper_full_draft_path)),
                ("Reviewer FAQ", _load_text_if_exists(paper_reviewer_faq_path)),
                ("Claim Matrix", _load_text_if_exists(paper_claim_matrix_md_path)),
            ],
        ),
    )
    reviewer_pack_ko_path = _write_text(
        output_root / "reviewer_pack_ko.md",
        build_audience_pack(
            "Reviewer Pack (KO)",
            [
                ("Deliverable Readiness", _load_text_if_exists(deliverable_readiness_ko_path)),
                ("Paper Full Draft", _load_text_if_exists(paper_full_draft_ko_path)),
                ("Reviewer FAQ", _load_text_if_exists(paper_reviewer_faq_ko_path)),
                ("Claim Matrix", _load_text_if_exists(paper_claim_matrix_ko_md_path)),
            ],
        ),
    )
    interview_pack_path = _write_text(
        output_root / "interview_pack.md",
        build_audience_pack(
            "Interview Pack",
            [
                ("Portfolio Case Study", _load_text_if_exists(portfolio_case_study_path)),
                ("Interview Answer Bank", _load_text_if_exists(interview_answer_bank_path)),
                ("Defense Packet", _load_text_if_exists(defense_packet_path)),
            ],
        ),
    )
    interview_pack_ko_path = _write_text(
        output_root / "interview_pack_ko.md",
        build_audience_pack(
            "Interview Pack (KO)",
            [
                ("Portfolio Case Study", _load_text_if_exists(portfolio_case_study_ko_path)),
                ("Interview Answer Bank", _load_text_if_exists(interview_answer_bank_ko_path)),
                ("Defense Packet", _load_text_if_exists(defense_packet_ko_path)),
            ],
        ),
    )
    portfolio_pack_path = _write_text(
        output_root / "portfolio_pack.md",
        build_audience_pack(
            "Portfolio Pack",
            [
                ("Portfolio Case Study", _load_text_if_exists(portfolio_case_study_path)),
                ("Artifact Catalog", _load_text_if_exists(artifact_catalog_md_path)),
                ("Deliverable Readiness", _load_text_if_exists(deliverable_readiness_path)),
            ],
        ),
    )
    portfolio_pack_ko_path = _write_text(
        output_root / "portfolio_pack_ko.md",
        build_audience_pack(
            "Portfolio Pack (KO)",
            [
                ("Portfolio Case Study", _load_text_if_exists(portfolio_case_study_ko_path)),
                ("Artifact Catalog", _load_text_if_exists(artifact_catalog_ko_md_path)),
                ("Deliverable Readiness", _load_text_if_exists(deliverable_readiness_ko_path)),
            ],
        ),
    )
    payload.update(
        {
            "advisor_review_pack_path": str(advisor_review_pack_path),
            "advisor_review_pack_ko_path": str(advisor_review_pack_ko_path),
            "reviewer_pack_path": str(reviewer_pack_path),
            "reviewer_pack_ko_path": str(reviewer_pack_ko_path),
            "interview_pack_path": str(interview_pack_path),
            "interview_pack_ko_path": str(interview_pack_ko_path),
            "portfolio_pack_path": str(portfolio_pack_path),
            "portfolio_pack_ko_path": str(portfolio_pack_ko_path),
        }
    )
    manifest_path = _write_text(output_root / "paper_assets_manifest.json", json.dumps(payload, indent=2))
    payload["paper_assets_manifest_path"] = str(manifest_path)
    Path(manifest_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def build_paper_assets_from_manifest_path(manifest_path: str | Path, output_dir: str | Path | None = None) -> dict[str, str]:
    manifest = _load_json(manifest_path)
    return build_paper_assets_from_manifest(manifest, output_dir=output_dir)
