from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


TRANSFER_SUPPLEMENT_FIELDS = [
    "source_region",
    "target_region",
    "model_name",
    "transfer_threshold",
    "delta_f1_fixed_threshold",
    "delta_f1_bootstrap_ci_low",
    "delta_f1_bootstrap_ci_high",
    "target_retune_gain_f1",
    "target_best_threshold",
    "delta_f1_if_target_retuned",
    "delta_f1_ci_excludes_zero_negative",
]

SCENARIO_PANEL_FIELDS = [
    "region",
    "dataset",
    "model_name",
    "f1_mean",
    "ece",
    "fp",
    "fn",
    "fp_rate",
    "fn_rate",
    "reliability_figure_path",
    "heatmap_contour_figure_svg_path",
    "case_id",
    "timestamp",
    "own_mmsi",
    "target_count",
    "max_risk_mean",
    "calibration_note",
    "error_note",
]


def _parse_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def _region_from_dataset(dataset: str) -> str:
    return str(dataset).replace("_pooled_pairwise", "")


def _parse_region_json_map(raw: str) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for token in str(raw).split(","):
        item = token.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"Invalid region json map token: {item}. expected region:path")
        region, path = item.split(":", 1)
        region_name = region.strip()
        path_value = path.strip()
        if not region_name or not path_value:
            raise ValueError(f"Invalid region json map token: {item}")
        mapping[region_name] = Path(path_value).resolve()
    if not mapping:
        raise ValueError("No region json mapping parsed.")
    return mapping


def _build_transfer_table_rows(detail_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in detail_rows:
        if str(row.get("status", "")).strip() != "completed":
            continue
        payload = {field: row.get(field, "") for field in TRANSFER_SUPPLEMENT_FIELDS}
        rows.append(payload)
    rows.sort(key=lambda item: (str(item.get("source_region", "")), str(item.get("target_region", ""))))
    return rows


def _calibration_note(ece_value: float | None) -> str:
    if ece_value is None:
        return "Calibration evidence missing."
    if ece_value <= 0.03:
        return "Well-calibrated probability profile (ECE <= 0.03)."
    if ece_value <= 0.05:
        return "Acceptable calibration (ECE <= 0.05), monitor drift."
    if ece_value <= 0.10:
        return "Within gate but requires cautious interpretation (ECE <= 0.10)."
    return "Calibration gate exceeded; avoid deployment claim."


def _error_note(fp_value: float | None, fn_value: float | None) -> str:
    if fp_value is None or fn_value is None:
        return "FP/FN evidence missing."
    if fn_value > fp_value:
        return "FN pressure dominates; discuss missed-risk implications."
    if fp_value > fn_value:
        return "FP pressure dominates; discuss alert fatigue tradeoff."
    return "FP/FN are balanced."


def _build_scenario_panel_rows(
    recommendation_rows: list[dict[str, str]],
    reliability_rows: list[dict[str, str]],
    taxonomy_rows: list[dict[str, str]],
    contour_summary_by_region: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    reliability_by_region = {str(row.get("region", "")).strip(): row for row in reliability_rows}
    taxonomy_by_region = {str(row.get("region", "")).strip(): row for row in taxonomy_rows}

    rows: list[dict[str, Any]] = []
    for rec in recommendation_rows:
        dataset = str(rec.get("dataset", "")).strip()
        if not dataset:
            continue
        region = _region_from_dataset(dataset)
        rel = reliability_by_region.get(region, {})
        tax = taxonomy_by_region.get(region, {})
        contour = contour_summary_by_region.get(region, {})

        ece_value = _safe_float(rel.get("ece"))
        fp_value = _safe_float(tax.get("fp"))
        fn_value = _safe_float(tax.get("fn"))
        rows.append(
            {
                "region": region,
                "dataset": dataset,
                "model_name": rec.get("model_name", ""),
                "f1_mean": rec.get("f1_mean", ""),
                "ece": rel.get("ece", rec.get("ece_mean", "")),
                "fp": tax.get("fp", ""),
                "fn": tax.get("fn", ""),
                "fp_rate": tax.get("fp_rate", ""),
                "fn_rate": tax.get("fn_rate", ""),
                "reliability_figure_path": rel.get("figure_path", ""),
                "heatmap_contour_figure_svg_path": contour.get("figure_svg_path", ""),
                "case_id": contour.get("case_id", ""),
                "timestamp": contour.get("timestamp", ""),
                "own_mmsi": contour.get("own_mmsi", ""),
                "target_count": contour.get("target_count", ""),
                "max_risk_mean": contour.get("max_risk_mean", ""),
                "calibration_note": _calibration_note(ece_value),
                "error_note": _error_note(fp_value, fn_value),
            }
        )
    rows.sort(key=lambda item: str(item.get("region", "")))
    return rows


def run_external_validity_manuscript_assets(
    transfer_gap_detail_csv_path: str | Path,
    recommendation_csv_path: str | Path,
    reliability_region_summary_csv_path: str | Path,
    taxonomy_region_summary_csv_path: str | Path,
    contour_report_summary_json_by_region: dict[str, str | Path],
    output_prefix: str | Path,
) -> dict[str, Any]:
    transfer_detail_rows = _parse_csv_rows(transfer_gap_detail_csv_path)
    recommendation_rows = _parse_csv_rows(recommendation_csv_path)
    reliability_rows = _parse_csv_rows(reliability_region_summary_csv_path)
    taxonomy_rows = _parse_csv_rows(taxonomy_region_summary_csv_path)
    contour_summary_by_region = {
        str(region): json.loads(Path(path).resolve().read_text(encoding="utf-8"))
        for region, path in contour_report_summary_json_by_region.items()
    }

    transfer_rows = _build_transfer_table_rows(transfer_detail_rows)
    scenario_rows = _build_scenario_panel_rows(
        recommendation_rows=recommendation_rows,
        reliability_rows=reliability_rows,
        taxonomy_rows=taxonomy_rows,
        contour_summary_by_region=contour_summary_by_region,
    )

    output_prefix_path = Path(output_prefix).resolve()
    output_prefix_path.parent.mkdir(parents=True, exist_ok=True)
    transfer_csv_path = output_prefix_path.with_name(f"{output_prefix_path.name}_transfer_uncertainty_table").with_suffix(".csv")
    transfer_md_path = output_prefix_path.with_name(f"{output_prefix_path.name}_transfer_uncertainty_table").with_suffix(".md")
    scenario_csv_path = output_prefix_path.with_name(f"{output_prefix_path.name}_scenario_panels").with_suffix(".csv")
    scenario_md_path = output_prefix_path.with_name(f"{output_prefix_path.name}_scenario_panels").with_suffix(".md")
    integration_md_path = output_prefix_path.with_suffix(".md")
    summary_json_path = output_prefix_path.with_suffix(".json")

    _write_csv(transfer_csv_path, transfer_rows, TRANSFER_SUPPLEMENT_FIELDS)
    _write_csv(scenario_csv_path, scenario_rows, SCENARIO_PANEL_FIELDS)

    transfer_md_lines = [
        "# Supplementary Transfer-Uncertainty Table",
        "",
        "This table is intended for the external-validity supplement and reports all transfer directions.",
        "",
        "| Source | Target | Model | Fixed-th ΔF1 | CI95(low,high) | Retune Gain | Best Target-th | Retuned ΔF1 |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in transfer_rows:
        transfer_md_lines.append(
            "| {src} | {tgt} | {model} | {d_fixed} | ({ci_low}, {ci_high}) | {gain} | {best_th} | {d_retuned} |".format(
                src=row.get("source_region", ""),
                tgt=row.get("target_region", ""),
                model=row.get("model_name", ""),
                d_fixed=_fmt(row.get("delta_f1_fixed_threshold")),
                ci_low=_fmt(row.get("delta_f1_bootstrap_ci_low")),
                ci_high=_fmt(row.get("delta_f1_bootstrap_ci_high")),
                gain=_fmt(row.get("target_retune_gain_f1")),
                best_th=_fmt(row.get("target_best_threshold")),
                d_retuned=_fmt(row.get("delta_f1_if_target_retuned")),
            )
        )
    transfer_md_lines.extend(
        [
            "",
            "Main-text citation sentence:",
            "See Supplementary Table S-Transfer-1 for fixed-threshold transfer ΔF1, bootstrap CI95, and target-threshold retune gains across all directions.",
            "",
        ]
    )
    transfer_md_path.write_text("\n".join(transfer_md_lines), encoding="utf-8")

    scenario_md_lines = [
        "# Three-Region Heatmap/Scenario Evidence Panels",
        "",
        "Each panel links one representative heatmap+contour figure with region-level error taxonomy and calibration evidence.",
        "",
    ]
    for row in scenario_rows:
        scenario_md_lines.extend(
            [
                f"## Panel: {row.get('region', '')}",
                "",
                f"- model / F1 / ECE: `{row.get('model_name', '')}` / `{_fmt(row.get('f1_mean'))}` / `{_fmt(row.get('ece'))}`",
                f"- FP / FN (seed-42 taxonomy snapshot): `{row.get('fp', '')}` / `{row.get('fn', '')}`",
                f"- calibration note: {row.get('calibration_note', '')}",
                f"- error interpretation: {row.get('error_note', '')}",
                f"- reliability figure: `{row.get('reliability_figure_path', '')}`",
                f"- heatmap+contour figure: `{row.get('heatmap_contour_figure_svg_path', '')}`",
                (
                    f"- representative case: `{row.get('case_id', '')}` "
                    f"(own_mmsi `{row.get('own_mmsi', '')}`, timestamp `{row.get('timestamp', '')}`, "
                    f"target_count `{row.get('target_count', '')}`, max_risk_mean `{_fmt(row.get('max_risk_mean'))}`)"
                ),
                "",
            ]
        )
    scenario_md_path.write_text("\n".join(scenario_md_lines), encoding="utf-8")

    integration_md_lines = [
        "# External-Validity Manuscript Integration Note",
        "",
        "## Main-Text Insert (External Validity Section)",
        "",
        "Cross-region transfer uncertainty is summarized in Supplementary Table S-Transfer-1, which reports fixed-threshold ΔF1, bootstrap CI95, and target-threshold retune gains for all evaluated directions.",
        "",
        "To connect quantitative model quality with spatial interpretation, we additionally provide three region-level scenario panels (Houston/NOLA/Seattle) that pair representative heatmap+contour figures with calibration evidence (ECE) and FP/FN taxonomy diagnostics.",
        "",
        "## Assets",
        "",
        f"- transfer_uncertainty_table_csv: `{transfer_csv_path}`",
        f"- transfer_uncertainty_table_md: `{transfer_md_path}`",
        f"- scenario_panels_csv: `{scenario_csv_path}`",
        f"- scenario_panels_md: `{scenario_md_path}`",
        f"- summary_json: `{summary_json_path}`",
        "",
    ]
    integration_md_path.write_text("\n".join(integration_md_lines), encoding="utf-8")

    summary = {
        "status": "completed",
        "transfer_gap_detail_csv_path": str(Path(transfer_gap_detail_csv_path).resolve()),
        "recommendation_csv_path": str(Path(recommendation_csv_path).resolve()),
        "reliability_region_summary_csv_path": str(Path(reliability_region_summary_csv_path).resolve()),
        "taxonomy_region_summary_csv_path": str(Path(taxonomy_region_summary_csv_path).resolve()),
        "contour_report_summary_json_by_region": {region: str(Path(path).resolve()) for region, path in contour_report_summary_json_by_region.items()},
        "transfer_direction_count": len(transfer_rows),
        "scenario_panel_count": len(scenario_rows),
        "transfer_uncertainty_table_csv_path": str(transfer_csv_path),
        "transfer_uncertainty_table_md_path": str(transfer_md_path),
        "scenario_panels_csv_path": str(scenario_csv_path),
        "scenario_panels_md_path": str(scenario_md_path),
        "integration_note_md_path": str(integration_md_path),
        "summary_json_path": str(summary_json_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


__all__ = ["_parse_region_json_map", "run_external_validity_manuscript_assets"]
