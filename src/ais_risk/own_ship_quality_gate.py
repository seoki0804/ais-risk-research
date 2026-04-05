from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except Exception:
        return None


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except Exception:
        return None


def load_own_ship_candidate_rows(path_value: str | Path) -> list[dict[str, str]]:
    path = Path(path_value)
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)
    rows.sort(key=lambda row: (_safe_int(row.get("rank")) or 999999, str(row.get("mmsi") or "")))
    return rows


def apply_own_ship_quality_gate(
    candidate_rows: list[dict[str, str]],
    min_row_count: int = 80,
    min_observed_row_count: int = 40,
    max_interpolation_ratio: float = 0.70,
    min_heading_coverage_ratio: float = 0.50,
    min_movement_ratio: float = 0.30,
    min_active_window_ratio: float = 0.10,
    min_average_nearby_targets: float = 0.50,
    max_segment_break_count: int = 50,
    min_candidate_score: float = 0.20,
    min_recommended_target_count: int = 1,
) -> list[dict[str, Any]]:
    gated_rows: list[dict[str, Any]] = []
    for row in candidate_rows:
        row_count = _safe_int(row.get("row_count")) or 0
        observed_row_count = _safe_int(row.get("observed_row_count")) or 0
        heading_coverage_ratio = _safe_float(row.get("heading_coverage_ratio")) or 0.0
        movement_ratio = _safe_float(row.get("movement_ratio")) or 0.0
        active_window_ratio = _safe_float(row.get("active_window_ratio")) or 0.0
        average_nearby_targets = _safe_float(row.get("average_nearby_targets")) or 0.0
        segment_break_count = _safe_int(row.get("segment_break_count")) or 0
        candidate_score = _safe_float(row.get("candidate_score")) or 0.0
        recommended_target_count = _safe_int(row.get("recommended_target_count"))
        interpolation_ratio = 0.0
        if row_count > 0:
            interpolation_ratio = max(0.0, min(1.0, 1.0 - (observed_row_count / row_count)))

        fail_reasons: list[str] = []
        if row_count < int(min_row_count):
            fail_reasons.append(f"row_count<{int(min_row_count)}")
        if observed_row_count < int(min_observed_row_count):
            fail_reasons.append(f"observed_row_count<{int(min_observed_row_count)}")
        if interpolation_ratio > float(max_interpolation_ratio):
            fail_reasons.append(f"interpolation_ratio>{float(max_interpolation_ratio):.2f}")
        if heading_coverage_ratio < float(min_heading_coverage_ratio):
            fail_reasons.append(f"heading_coverage<{float(min_heading_coverage_ratio):.2f}")
        if movement_ratio < float(min_movement_ratio):
            fail_reasons.append(f"movement_ratio<{float(min_movement_ratio):.2f}")
        if active_window_ratio < float(min_active_window_ratio):
            fail_reasons.append(f"active_window_ratio<{float(min_active_window_ratio):.2f}")
        if average_nearby_targets < float(min_average_nearby_targets):
            fail_reasons.append(f"avg_nearby_targets<{float(min_average_nearby_targets):.2f}")
        if segment_break_count > int(max_segment_break_count):
            fail_reasons.append(f"segment_break_count>{int(max_segment_break_count)}")
        if candidate_score < float(min_candidate_score):
            fail_reasons.append(f"candidate_score<{float(min_candidate_score):.2f}")
        if recommended_target_count is not None and recommended_target_count < int(min_recommended_target_count):
            fail_reasons.append(f"recommended_target_count<{int(min_recommended_target_count)}")

        quality_score = (
            0.20 * candidate_score
            + 0.15 * heading_coverage_ratio
            + 0.15 * movement_ratio
            + 0.20 * active_window_ratio
            + 0.15 * min(1.0, average_nearby_targets / max(float(min_average_nearby_targets), 1.0))
            + 0.15 * (1.0 - interpolation_ratio)
        )

        gated_rows.append(
            {
                **row,
                "interpolation_ratio": interpolation_ratio,
                "quality_score": quality_score,
                "gate_passed": len(fail_reasons) == 0,
                "fail_reasons": fail_reasons,
                "fail_reason_text": "; ".join(fail_reasons),
            }
        )

    gated_rows.sort(
        key=lambda item: (
            1 if bool(item.get("gate_passed")) else 0,
            _safe_float(item.get("quality_score")) or -999.0,
            _safe_float(item.get("candidate_score")) or -999.0,
            -(_safe_float(item.get("interpolation_ratio")) or 999.0),
            str(item.get("mmsi") or ""),
        ),
        reverse=True,
    )
    return gated_rows


def build_own_ship_quality_gate_summary(
    gated_rows: list[dict[str, Any]],
    *,
    input_path: str | Path,
    min_row_count: int,
    min_observed_row_count: int,
    max_interpolation_ratio: float,
    min_heading_coverage_ratio: float,
    min_movement_ratio: float,
    min_active_window_ratio: float,
    min_average_nearby_targets: float,
    max_segment_break_count: int,
    min_candidate_score: float,
    min_recommended_target_count: int,
) -> dict[str, Any]:
    passed_rows = [row for row in gated_rows if bool(row.get("gate_passed"))]
    recommended = passed_rows[0] if passed_rows else (gated_rows[0] if gated_rows else None)
    return {
        "input_path": str(input_path),
        "candidate_count": len(gated_rows),
        "passed_count": len(passed_rows),
        "failed_count": max(0, len(gated_rows) - len(passed_rows)),
        "pass_ratio": (len(passed_rows) / len(gated_rows)) if gated_rows else 0.0,
        "recommended_mmsi": (recommended or {}).get("mmsi"),
        "recommended_quality_score": (recommended or {}).get("quality_score"),
        "recommended_gate_passed": (recommended or {}).get("gate_passed"),
        "thresholds": {
            "min_row_count": int(min_row_count),
            "min_observed_row_count": int(min_observed_row_count),
            "max_interpolation_ratio": float(max_interpolation_ratio),
            "min_heading_coverage_ratio": float(min_heading_coverage_ratio),
            "min_movement_ratio": float(min_movement_ratio),
            "min_active_window_ratio": float(min_active_window_ratio),
            "min_average_nearby_targets": float(min_average_nearby_targets),
            "max_segment_break_count": int(max_segment_break_count),
            "min_candidate_score": float(min_candidate_score),
            "min_recommended_target_count": int(min_recommended_target_count),
        },
    }


def save_own_ship_quality_gate_outputs(
    output_prefix: str | Path,
    summary: dict[str, Any],
    gated_rows: list[dict[str, Any]],
) -> tuple[Path, Path, Path]:
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(prefix.name + "_summary.json")
    summary_md_path = prefix.with_name(prefix.name + "_summary.md")
    rows_csv_path = prefix.with_name(prefix.name + "_rows.csv")

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_own_ship_quality_gate_markdown(summary, gated_rows), encoding="utf-8")

    fieldnames = [
        "mmsi",
        "rank",
        "gate_passed",
        "quality_score",
        "candidate_score",
        "row_count",
        "observed_row_count",
        "interpolation_ratio",
        "heading_coverage_ratio",
        "movement_ratio",
        "active_window_ratio",
        "average_nearby_targets",
        "segment_break_count",
        "recommended_target_count",
        "fail_reason_text",
        "reason_summary",
    ]
    with rows_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in gated_rows:
            writer.writerow({key: row.get(key) for key in fieldnames})

    return summary_json_path, summary_md_path, rows_csv_path


def build_own_ship_quality_gate_markdown(summary: dict[str, Any], gated_rows: list[dict[str, Any]]) -> str:
    top_rows = gated_rows[:10]
    row_lines = "\n".join(
        "| {mmsi} | {passed} | {qscore:.3f} | {cscore:.3f} | {rows} | {observed} | {interp:.3f} | {heading:.3f} | {active:.3f} | {nearby:.3f} | {reasons} |".format(
            mmsi=row.get("mmsi", ""),
            passed="yes" if bool(row.get("gate_passed")) else "no",
            qscore=float(row.get("quality_score") or 0.0),
            cscore=float(row.get("candidate_score") or 0.0),
            rows=int(_safe_int(row.get("row_count")) or 0),
            observed=int(_safe_int(row.get("observed_row_count")) or 0),
            interp=float(row.get("interpolation_ratio") or 0.0),
            heading=float(row.get("heading_coverage_ratio") or 0.0),
            active=float(row.get("active_window_ratio") or 0.0),
            nearby=float(row.get("average_nearby_targets") or 0.0),
            reasons=row.get("fail_reason_text", "") or "-",
        )
        for row in top_rows
    ) or "| - | - | - | - | - | - | - | - | - | - | - |"

    thresholds = summary.get("thresholds", {})
    return "\n".join(
        [
            "# Own Ship Quality Gate Summary",
            "",
            "## Overview",
            "",
            f"- input_path: `{summary.get('input_path', 'n/a')}`",
            f"- candidate_count: `{summary.get('candidate_count', 0)}`",
            f"- passed_count: `{summary.get('passed_count', 0)}`",
            f"- failed_count: `{summary.get('failed_count', 0)}`",
            f"- pass_ratio: `{float(summary.get('pass_ratio', 0.0)):.3f}`",
            f"- recommended_mmsi: `{summary.get('recommended_mmsi', 'n/a')}`",
            f"- recommended_quality_score: `{float(summary.get('recommended_quality_score') or 0.0):.3f}`",
            f"- recommended_gate_passed: `{'yes' if bool(summary.get('recommended_gate_passed')) else 'no'}`",
            "",
            "## Thresholds",
            "",
            f"- min_row_count: `{thresholds.get('min_row_count', 'n/a')}`",
            f"- min_observed_row_count: `{thresholds.get('min_observed_row_count', 'n/a')}`",
            f"- max_interpolation_ratio: `{thresholds.get('max_interpolation_ratio', 'n/a')}`",
            f"- min_heading_coverage_ratio: `{thresholds.get('min_heading_coverage_ratio', 'n/a')}`",
            f"- min_movement_ratio: `{thresholds.get('min_movement_ratio', 'n/a')}`",
            f"- min_active_window_ratio: `{thresholds.get('min_active_window_ratio', 'n/a')}`",
            f"- min_average_nearby_targets: `{thresholds.get('min_average_nearby_targets', 'n/a')}`",
            f"- max_segment_break_count: `{thresholds.get('max_segment_break_count', 'n/a')}`",
            f"- min_candidate_score: `{thresholds.get('min_candidate_score', 'n/a')}`",
            f"- min_recommended_target_count: `{thresholds.get('min_recommended_target_count', 'n/a')}`",
            "",
            "## Top Rows",
            "",
            "| MMSI | Passed | Quality | Candidate | Rows | Observed | Interp | Heading | Active | Nearby | Fail Reasons |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
            row_lines,
            "",
        ]
    )
