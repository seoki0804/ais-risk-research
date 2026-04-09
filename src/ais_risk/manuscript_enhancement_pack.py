from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _escape_xml(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _dataset_to_region(dataset: str) -> str:
    if not dataset:
        return ""
    return dataset.split("_")[0]


@dataclass
class _FamilyBest:
    region: str
    dataset: str
    family: str
    model_name: str
    f1: float
    ece: float
    auroc: float


def _pick_best_by_family(leaderboard_rows: list[dict[str, str]]) -> list[_FamilyBest]:
    families = {"tabular", "regional_raster_cnn"}
    best: dict[tuple[str, str], _FamilyBest] = {}
    for row in leaderboard_rows:
        if row.get("status") != "completed":
            continue
        dataset = str(row.get("dataset", ""))
        family = str(row.get("model_family", ""))
        if family not in families:
            continue
        region = _dataset_to_region(dataset)
        candidate = _FamilyBest(
            region=region,
            dataset=dataset,
            family=family,
            model_name=str(row.get("model_name", "")),
            f1=_to_float(row.get("f1")),
            ece=_to_float(row.get("ece")),
            auroc=_to_float(row.get("auroc")),
        )
        key = (dataset, family)
        prev = best.get(key)
        if prev is None or candidate.f1 > prev.f1:
            best[key] = candidate
    return sorted(best.values(), key=lambda item: (item.dataset, item.family))


def _index_by_dataset_model(leaderboard_rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    index: dict[tuple[str, str], dict[str, str]] = {}
    for row in leaderboard_rows:
        if row.get("status") != "completed":
            continue
        key = (str(row.get("dataset", "")), str(row.get("model_name", "")))
        previous = index.get(key)
        if previous is None or _to_float(row.get("f1")) > _to_float(previous.get("f1")):
            index[key] = row
    return index


def _render_grouped_bar_svg(rows: list[_FamilyBest], output_path: Path) -> None:
    regions = sorted({row.region for row in rows if row.region})
    if not regions:
        output_path.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='800' height='120'></svg>", encoding="utf-8")
        return
    families = ["tabular", "regional_raster_cnn"]
    color_map = {"tabular": "#2B6CB0", "regional_raster_cnn": "#DD6B20"}
    width = 980
    height = 520
    margin_left = 100
    margin_right = 50
    margin_top = 70
    margin_bottom = 120
    chart_w = width - margin_left - margin_right
    chart_h = height - margin_top - margin_bottom
    group_w = chart_w / max(len(regions), 1)
    bar_w = min(44.0, group_w / 3.2)
    y_min = 0.35
    y_max = 0.90

    value_map: dict[tuple[str, str], _FamilyBest] = {(r.region, r.family): r for r in rows}

    parts: list[str] = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Arial,sans-serif;fill:#1A202C} .small{font-size:12px} .axis{font-size:11px;fill:#4A5568} .title{font-size:20px;font-weight:700} .subtitle{font-size:12px;fill:#4A5568}</style>",
        f"<text x='{margin_left}' y='34' class='title'>Figure 1. Region-wise Best Model Family Comparison (F1)</text>",
        f"<text x='{margin_left}' y='54' class='subtitle'>Best tabular vs best raster-CNN per region, using all_models_multiarea_leaderboard.csv</text>",
    ]

    for tick in [0.40, 0.50, 0.60, 0.70, 0.80, 0.90]:
        y = margin_top + chart_h * (1 - ((tick - y_min) / (y_max - y_min)))
        parts.append(f"<line x1='{margin_left}' y1='{y:.2f}' x2='{margin_left + chart_w}' y2='{y:.2f}' stroke='#E2E8F0' stroke-width='1'/>")
        parts.append(f"<text x='{margin_left - 10}' y='{y + 4:.2f}' class='axis' text-anchor='end'>{tick:.2f}</text>")

    parts.append(
        f"<rect x='{margin_left}' y='{margin_top}' width='{chart_w}' height='{chart_h}' fill='none' stroke='#A0AEC0' stroke-width='1'/>"
    )

    for i, region in enumerate(regions):
        gx = margin_left + i * group_w + group_w / 2
        for j, family in enumerate(families):
            row = value_map.get((region, family))
            value = row.f1 if row else y_min
            normalized = max(0.0, min(1.0, (value - y_min) / (y_max - y_min)))
            bar_h = chart_h * normalized
            x = gx + (j - 0.5) * (bar_w + 10) - bar_w / 2
            y = margin_top + chart_h - bar_h
            color = color_map[family]
            parts.append(f"<rect x='{x:.2f}' y='{y:.2f}' width='{bar_w:.2f}' height='{bar_h:.2f}' fill='{color}' rx='3'/>")
            if row:
                label = f"{row.f1:.3f}"
                parts.append(f"<text x='{x + bar_w/2:.2f}' y='{y - 6:.2f}' class='small' text-anchor='middle'>{label}</text>")
        parts.append(f"<text x='{gx:.2f}' y='{margin_top + chart_h + 24}' class='small' text-anchor='middle'>{_escape_xml(region)}</text>")

    legend_x = margin_left + chart_w - 240
    legend_y = margin_top + 10
    parts.append(f"<rect x='{legend_x}' y='{legend_y}' width='14' height='14' fill='{color_map['tabular']}'/>")
    parts.append(f"<text x='{legend_x + 22}' y='{legend_y + 12}' class='small'>tabular (best)</text>")
    parts.append(f"<rect x='{legend_x}' y='{legend_y + 22}' width='14' height='14' fill='{color_map['regional_raster_cnn']}'/>")
    parts.append(f"<text x='{legend_x + 22}' y='{legend_y + 34}' class='small'>regional_raster_cnn (best)</text>")

    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def _delta_to_color(delta: float) -> str:
    if delta < -0.15:
        return "#C53030"
    if delta < -0.05:
        return "#E53E3E"
    if delta < 0.0:
        return "#FC8181"
    if delta < 0.05:
        return "#BEE3F8"
    if delta < 0.15:
        return "#63B3ED"
    return "#2B6CB0"


def _render_transfer_heatmap_svg(
    transfer_rows: list[dict[str, str]],
    output_path: Path,
) -> None:
    regions = sorted(
        {
            str(row.get("source_region", "")).strip()
            for row in transfer_rows
            if str(row.get("source_region", "")).strip()
        }
        | {
            str(row.get("target_region", "")).strip()
            for row in transfer_rows
            if str(row.get("target_region", "")).strip()
        }
    )
    if not regions:
        output_path.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='800' height='120'></svg>", encoding="utf-8")
        return
    value_map: dict[tuple[str, str], float] = {}
    for row in transfer_rows:
        src = str(row.get("source_region", "")).strip()
        dst = str(row.get("target_region", "")).strip()
        if not src or not dst:
            continue
        value_map[(src, dst)] = _to_float(row.get("delta_f1"))

    width = 760
    height = 540
    margin_left = 170
    margin_top = 120
    cell = 120

    parts: list[str] = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Arial,sans-serif;fill:#1A202C}.small{font-size:12px}.title{font-size:20px;font-weight:700}.subtitle{font-size:12px;fill:#4A5568}</style>",
        "<text x='20' y='34' class='title'>Figure 2. Cross-Region Transfer ΔF1 Heatmap</text>",
        "<text x='20' y='54' class='subtitle'>Rows = source region, columns = target region (recommended model transfer)</text>",
    ]

    for i, src in enumerate(regions):
        y = margin_top + i * cell
        parts.append(f"<text x='{margin_left - 14}' y='{y + cell/2 + 4:.2f}' class='small' text-anchor='end'>{_escape_xml(src)}</text>")
    for j, dst in enumerate(regions):
        x = margin_left + j * cell
        parts.append(
            f"<text x='{x + cell/2:.2f}' y='{margin_top - 16}' class='small' text-anchor='middle'>{_escape_xml(dst)}</text>"
        )

    for i, src in enumerate(regions):
        for j, dst in enumerate(regions):
            x = margin_left + j * cell
            y = margin_top + i * cell
            if src == dst:
                color = "#EDF2F7"
                text = "-"
            else:
                value = value_map.get((src, dst), 0.0)
                color = _delta_to_color(value)
                text = f"{value:+.3f}"
            parts.append(f"<rect x='{x}' y='{y}' width='{cell}' height='{cell}' fill='{color}' stroke='white' stroke-width='2'/>")
            parts.append(f"<text x='{x + cell/2:.2f}' y='{y + cell/2 + 4:.2f}' class='small' text-anchor='middle'>{text}</text>")

    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def _render_pipeline_svg(output_path: Path) -> None:
    width = 1060
    height = 340
    boxes = [
        ("AIS Raw/Curated Data", 40, 90, "#2D3748"),
        ("Feature & Pairwise Dataset", 250, 90, "#2B6CB0"),
        ("Multi-Model Training", 500, 90, "#2F855A"),
        ("In/Out-of-Time + Transfer Eval", 730, 90, "#DD6B20"),
        ("Governance + Manuscript Assets", 930, 90, "#6B46C1"),
    ]
    parts: list[str] = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Arial,sans-serif;fill:#1A202C}.title{font-size:20px;font-weight:700}.small{font-size:12px}</style>",
        "<text x='30' y='34' class='title'>Figure 3. End-to-End Research Pipeline</text>",
    ]
    for label, x, y, color in boxes:
        parts.append(f"<rect x='{x}' y='{y}' width='170' height='88' rx='10' fill='{color}'/>")
        parts.append(
            f"<text x='{x + 85}' y='{y + 36}' text-anchor='middle' class='small' fill='white'>{_escape_xml(label)}</text>"
        )
    for i in range(len(boxes) - 1):
        x1 = boxes[i][1] + 170
        x2 = boxes[i + 1][1]
        y = 134
        parts.append(f"<line x1='{x1 + 6}' y1='{y}' x2='{x2 - 10}' y2='{y}' stroke='#4A5568' stroke-width='3'/>")
        parts.append(
            f"<polygon points='{x2 - 10},{y - 6} {x2},{y} {x2 - 10},{y + 6}' fill='#4A5568'/>"
        )
    parts.append("<text x='40' y='250' class='small'>Output: model selection, transfer-risk diagnostics, calibrated risk visualization, and manuscript-ready evidence tables.</text>")
    parts.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")


def _markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join([header, sep, *body])


def run_manuscript_enhancement_pack(
    *,
    results_root: Path,
    output_root: Path,
) -> dict[str, str]:
    leaderboard_csv = results_root / "all_models_multiarea_leaderboard.csv"
    recommendation_csv = results_root / "all_models_seed_sweep_recommendation.csv"
    transfer_csv = results_root / "transfer_recommendation_check.csv"
    scenario_csv = results_root / "external_validity_manuscript_assets_2026-04-05_10seed_scenario_panels.csv"

    leaderboard_rows = _read_csv(leaderboard_csv)
    recommendation_rows = _read_csv(recommendation_csv)
    transfer_rows = _read_csv(transfer_csv)
    scenario_rows = _read_csv(scenario_csv)

    family_best_rows = _pick_best_by_family(leaderboard_rows)
    by_dataset_model = _index_by_dataset_model(leaderboard_rows)

    recommended_summary_rows: list[dict[str, object]] = []
    for row in recommendation_rows:
        dataset = str(row.get("dataset", ""))
        model_name = str(row.get("model_name", ""))
        matched = by_dataset_model.get((dataset, model_name), {})
        recommended_summary_rows.append(
            {
                "region": _dataset_to_region(dataset),
                "dataset": dataset,
                "model_family": row.get("model_family", ""),
                "model_name": model_name,
                "f1_mean_10seed": f"{_to_float(row.get('f1_mean')):.4f}",
                "ece_mean_10seed": f"{_to_float(row.get('ece_mean')):.4f}",
                "f1_single_eval": f"{_to_float(matched.get('f1')):.4f}",
                "ece_single_eval": f"{_to_float(matched.get('ece')):.4f}",
                "auroc_single_eval": f"{_to_float(matched.get('auroc')):.4f}",
                "selection_rule": row.get("selection_rule", ""),
            }
        )

    family_rows_for_table = [
        {
            "region": row.region,
            "dataset": row.dataset,
            "model_family": row.family,
            "model_name": row.model_name,
            "f1": f"{row.f1:.4f}",
            "ece": f"{row.ece:.4f}",
            "auroc": f"{row.auroc:.4f}",
        }
        for row in family_best_rows
    ]

    transfer_rows_for_table = [
        {
            "source_region": r.get("source_region", ""),
            "target_region": r.get("target_region", ""),
            "recommended_model": r.get("recommended_model", ""),
            "delta_f1": f"{_to_float(r.get('delta_f1')):+.4f}",
            "target_ece": f"{_to_float(r.get('target_ece')):.4f}",
            "target_auroc": f"{_to_float(r.get('target_auroc')):.4f}",
        }
        for r in transfer_rows
    ]

    output_root.mkdir(parents=True, exist_ok=True)

    recommended_csv_path = output_root / "recommended_models_summary.csv"
    family_csv_path = output_root / "best_family_by_region_summary.csv"
    transfer_csv_path = output_root / "transfer_core_summary.csv"

    _write_csv(
        recommended_csv_path,
        recommended_summary_rows,
        [
            "region",
            "dataset",
            "model_family",
            "model_name",
            "f1_mean_10seed",
            "ece_mean_10seed",
            "f1_single_eval",
            "ece_single_eval",
            "auroc_single_eval",
            "selection_rule",
        ],
    )
    _write_csv(
        family_csv_path,
        family_rows_for_table,
        ["region", "dataset", "model_family", "model_name", "f1", "ece", "auroc"],
    )
    _write_csv(
        transfer_csv_path,
        transfer_rows_for_table,
        ["source_region", "target_region", "recommended_model", "delta_f1", "target_ece", "target_auroc"],
    )

    fig_model_family = output_root / "figure_1_model_family_comparison.svg"
    fig_transfer_heatmap = output_root / "figure_2_transfer_delta_f1_heatmap.svg"
    fig_pipeline = output_root / "figure_3_pipeline_overview.svg"

    _render_grouped_bar_svg(family_best_rows, fig_model_family)
    _render_transfer_heatmap_svg(transfer_rows, fig_transfer_heatmap)
    _render_pipeline_svg(fig_pipeline)

    scenario_columns = [
        "region",
        "model_name",
        "f1_mean",
        "ece",
        "fp",
        "fn",
        "reliability_figure_path",
        "heatmap_contour_figure_svg_path",
        "calibration_note",
        "error_note",
    ]
    scenario_md_table = _markdown_table(
        [{key: row.get(key, "") for key in scenario_columns} for row in scenario_rows],
        scenario_columns,
    )

    figure_index_path = output_root / "figure_index.md"
    figure_index_path.write_text(
        "\n".join(
            [
                "# Figure Index (Paper Upgrade)",
                "",
                f"- Figure 1: `./{fig_model_family.name}`",
                f"- Figure 2: `./{fig_transfer_heatmap.name}`",
                f"- Figure 3: `./{fig_pipeline.name}`",
                "- Existing scenario visuals:",
                "  - `../../results/2026-04-04-expanded-10seed/houston_report_figure.svg`",
                "  - `../../results/2026-04-04-expanded-10seed/nola_report_figure.svg`",
                "  - `../../results/2026-04-04-expanded-10seed/seattle_report_figure.svg`",
                "",
                "## Scenario Panel Table",
                "",
                scenario_md_table,
                "",
            ]
        ),
        encoding="utf-8",
    )

    recommended_md_table = _markdown_table(
        recommended_summary_rows,
        [
            "region",
            "model_family",
            "model_name",
            "f1_mean_10seed",
            "ece_mean_10seed",
            "f1_single_eval",
            "ece_single_eval",
        ],
    )
    transfer_md_table = _markdown_table(
        transfer_rows_for_table,
        ["source_region", "target_region", "recommended_model", "delta_f1", "target_ece"],
    )

    manuscript_draft_path = output_root / "manuscript_draft_v0.2_2026-04-09.md"
    manuscript_draft_path.write_text(
        "\n".join(
            [
                "# AIS 기반 충돌위험 히트맵 논문 초안 v0.2",
                "",
                "## 1. 연구 목적",
                "본 연구는 AIS 시계열 기반 모델 학습을 통해 해역별 충돌위험도를 추정하고, 이를 heatmap+contour 형태로 시각화하여 운항 의사결정에 활용 가능한지를 검증한다.",
                "",
                "## 2. 데이터/실험 설정",
                "- 데이터셋: Houston, NOLA, Seattle pooled pairwise",
                "- 모델군: tabular + regional_raster_cnn + rule baseline",
                "- 검증: in-time, out-of-time, cross-region transfer, calibration(ECE)",
                "",
                "## 3. 모델 선택 결과 (10-seed 기준)",
                "",
                recommended_md_table,
                "",
                "해석: 3개 지역 모두 ECE gate를 만족한 후보 중 성능과 분산을 고려해 최종 모델이 선택되었고, Houston/NOLA는 `hgbt`, Seattle은 `extra_trees`가 채택됐다.",
                "",
                "## 4. 전이 성능 핵심 결과",
                "",
                transfer_md_table,
                "",
                "해석: Houston source 전이는 음수 ΔF1이 관찰되며(domain shift), NOLA/Seattle source에서는 양수 또는 완만한 결과가 나타난다.",
                "",
                "## 5. 그림 도식 구성",
                f"- Figure 1: ![model-family]({fig_model_family.name})",
                f"- Figure 2: ![transfer-heatmap]({fig_transfer_heatmap.name})",
                f"- Figure 3: ![pipeline]({fig_pipeline.name})",
                "",
                "## 6. 시나리오 시각화 근거",
                "- Houston scenario: `../../results/2026-04-04-expanded-10seed/houston_report_figure.svg`",
                "- NOLA scenario: `../../results/2026-04-04-expanded-10seed/nola_report_figure.svg`",
                "- Seattle scenario: `../../results/2026-04-04-expanded-10seed/seattle_report_figure.svg`",
                "",
                "## 7. 제출 포맷 메모",
                "- 네, 현재 단계에서는 `docs`에 원고를 작성/버전관리하는 방식이 적합하다.",
                "- 최종 제출은 저널/학회 템플릿(Word/LaTeX)으로 변환하되, 내용 원천은 `docs/manuscript`를 single source로 유지한다.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "recommended_summary_csv_path": str(recommended_csv_path),
        "family_summary_csv_path": str(family_csv_path),
        "transfer_summary_csv_path": str(transfer_csv_path),
        "figure_1_model_family_comparison_svg_path": str(fig_model_family),
        "figure_2_transfer_delta_f1_heatmap_svg_path": str(fig_transfer_heatmap),
        "figure_3_pipeline_overview_svg_path": str(fig_pipeline),
        "figure_index_md_path": str(figure_index_path),
        "manuscript_draft_md_path": str(manuscript_draft_path),
    }
