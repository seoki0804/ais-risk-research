from __future__ import annotations

import json
from pathlib import Path


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _fmt(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def _find_best_scenario(experiment_data: dict) -> tuple[str, dict]:
    scenario_items = experiment_data["scenario_averages"].items()
    return min(
        scenario_items,
        key=lambda item: (
            item[1]["avg_warning_area_nm2"],
            item[1]["avg_max_risk"],
        ),
    )


def _scenario_rows_markdown(experiment_data: dict) -> str:
    lines = [
        "| Scenario | Avg Max Risk | Avg Mean Risk | Avg Warning Area (nm2) | Avg Delta Max Risk vs Current | Avg Delta Warning Area vs Current |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for scenario_name, metrics in experiment_data["scenario_averages"].items():
        lines.append(
            f"| {scenario_name} | {_fmt(metrics['avg_max_risk'])} | {_fmt(metrics['avg_mean_risk'])} | "
            f"{_fmt(metrics['avg_warning_area_nm2'])} | {_fmt(metrics['avg_delta_max_risk_vs_current'])} | "
            f"{_fmt(metrics['avg_delta_warning_area_vs_current'])} |"
        )
    return "\n".join(lines)


def _ablation_rows_markdown(ablation_data: dict) -> str:
    lines = [
        "| Ablation | Scenario | Avg Max Risk | Avg Warning Area (nm2) | Avg Delta Max Risk vs Baseline | Avg Delta Warning Area vs Baseline |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for ablation_label, scenario_map in ablation_data["ablations"].items():
        for scenario_name, metrics in scenario_map.items():
            lines.append(
                f"| {ablation_label} | {scenario_name} | {_fmt(metrics['avg_max_risk'])} | "
                f"{_fmt(metrics['avg_warning_area_nm2'])} | {_fmt(metrics['avg_delta_max_risk_vs_baseline'])} | "
                f"{_fmt(metrics['avg_delta_warning_area_vs_baseline'])} |"
            )
    return "\n".join(lines)


def _scenario_findings(experiment_data: dict) -> list[str]:
    best_name, best_metrics = _find_best_scenario(experiment_data)
    current = experiment_data["scenario_averages"]["current"]
    findings = [
        f"`{best_name}`가 평균 warning area 기준으로 가장 작은 시나리오였다.",
        f"`current` 대비 `{best_name}`의 평균 warning area는 {_fmt(best_metrics['avg_warning_area_nm2'] - current['avg_warning_area_nm2'])} nm2 차이를 보였다.",
        f"`current`의 평균 max risk는 {_fmt(current['avg_max_risk'])}, 평균 warning area는 {_fmt(current['avg_warning_area_nm2'])} nm2였다.",
    ]
    return findings


def _ablation_findings(ablation_data: dict) -> list[str]:
    effects: list[tuple[str, float, float]] = []
    for ablation_label, scenario_map in ablation_data["ablations"].items():
        if ablation_label == "baseline":
            continue
        current = scenario_map.get("current")
        if current is None:
            continue
        effects.append(
            (
                ablation_label,
                float(current["avg_delta_warning_area_vs_baseline"]),
                float(current["avg_delta_max_risk_vs_baseline"]),
            )
        )
    if not effects:
        return ["Ablation 결과가 없어 baseline만 보고서를 생성했다."]

    strongest_warning = max(effects, key=lambda item: abs(item[1]))
    strongest_risk = max(effects, key=lambda item: abs(item[2]))
    findings = [
        f"Current scenario 기준 warning area 변화가 가장 큰 ablation은 `{strongest_warning[0]}`였고, 평균 delta는 {_fmt(strongest_warning[1])} nm2였다.",
        f"Current scenario 기준 max risk 변화가 가장 큰 ablation은 `{strongest_risk[0]}`였고, 평균 delta는 {_fmt(strongest_risk[2])}였다.",
    ]
    return findings


def build_markdown_summary_from_data(experiment_data: dict, ablation_data: dict) -> str:
    scenario_findings = _scenario_findings(experiment_data)
    ablation_findings = _ablation_findings(ablation_data)

    markdown = f"""# Baseline Experiment Findings

## Scope

- Own ship MMSI: `{experiment_data['own_mmsi']}`
- Case count: `{experiment_data['case_count']}`
- Radius: `{experiment_data['radius_nm']}` NM

## Scenario Summary

{_scenario_rows_markdown(experiment_data)}

## Scenario Findings

- {scenario_findings[0]}
- {scenario_findings[1]}
- {scenario_findings[2]}

## Ablation Summary

{_ablation_rows_markdown(ablation_data)}

## Ablation Findings

- {ablation_findings[0]}
- {ablation_findings[1]}

## Notes

- 본 요약은 AIS-only, constant-velocity baseline에 기반한 proxy risk 결과다.
- `warning area`와 `max risk`는 시나리오 비교와 ablation 상대효과를 설명하기 위한 내부 지표다.
- 실제 조타 또는 법적 안전 보장을 의미하지 않는다.
"""
    return markdown


def build_markdown_summary(experiment_json_path: str | Path, ablation_json_path: str | Path) -> str:
    experiment_data = _load_json(experiment_json_path)
    ablation_data = _load_json(ablation_json_path)
    return build_markdown_summary_from_data(experiment_data, ablation_data)


def save_markdown_summary(output_path: str | Path, markdown_text: str) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(markdown_text, encoding="utf-8")
