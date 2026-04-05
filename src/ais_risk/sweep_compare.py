from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

CORE_METRIC_SPECS: list[tuple[str, bool]] = [
    ("best_benchmark_f1", True),
    ("best_loo_f1_mean", True),
    ("best_case_f1_mean", True),
    ("best_case_f1_std", False),
    ("best_case_f1_ci95_width", False),
    ("best_case_f1_std_repeat_mean", False),
    ("best_calibration_ece", False),
]

AUX_METRIC_SPECS: list[tuple[str, bool]] = [
    ("benchmark_elapsed_seconds", False),
    ("torch_mlp_elapsed_seconds", False),
]


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def _fmt_delta(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    sign = "+" if numeric >= 0 else ""
    return f"{sign}{numeric:.{digits}f}"


def _modelset_rows_by_key(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = summary.get("rows", [])
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("modelset_key") or "")
        if not key:
            continue
        output[key] = row
    return output


def _compare_metric(
    focus_value: float | None,
    baseline_value: float | None,
    higher_is_better: bool,
    epsilon: float,
) -> tuple[float | None, str]:
    if focus_value is None or baseline_value is None:
        return None, "n/a"
    delta = float(focus_value - baseline_value)
    if abs(delta) <= abs(epsilon):
        return delta, "same"
    if higher_is_better:
        return delta, "focus_better" if delta > 0 else "baseline_better"
    return delta, "focus_better" if delta < 0 else "baseline_better"


def _judgement(focus_better_count: int, baseline_better_count: int, compared_metric_count: int) -> str:
    if compared_metric_count <= 0:
        return "insufficient_metrics"
    if focus_better_count >= 4 and baseline_better_count == 0:
        return "focus_advantage"
    if baseline_better_count >= 4 and focus_better_count == 0:
        return "baseline_advantage"
    if focus_better_count > baseline_better_count:
        return "focus_leaning"
    if baseline_better_count > focus_better_count:
        return "baseline_leaning"
    return "mixed"


def build_sweep_compare_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Study Sweep Compare Report",
        "",
        "## Inputs",
        "",
        f"- focus_label: `{summary.get('focus_label', 'focus')}`",
        f"- baseline_label: `{summary.get('baseline_label', 'baseline')}`",
        f"- focus_summary_path: `{summary.get('focus_summary_path', 'n/a')}`",
        f"- baseline_summary_path: `{summary.get('baseline_summary_path', 'n/a')}`",
        f"- focus_own_ship_case_eval_mmsis: `{summary.get('focus_own_ship_case_eval_mmsis', [])}`",
        f"- baseline_own_ship_case_eval_mmsis: `{summary.get('baseline_own_ship_case_eval_mmsis', [])}`",
        f"- modelset_count: `{summary.get('modelset_count', 0)}`",
        "",
        "## Comparison",
        "",
        "| Modelset | Focus Case F1 | Base Case F1 | Delta Case F1 | Focus Case Std | Base Case Std | Delta Case Std | Focus Repeat Std Mean | Base Repeat Std Mean | Delta Repeat Std Mean | Focus Cal ECE | Base Cal ECE | Delta Cal ECE | Focus Better | Baseline Better | Compared Metrics | Judgement |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary.get("rows", []):
        lines.append(
            "| {modelset} | {focus_case_f1} | {base_case_f1} | {delta_case_f1} | {focus_case_std} | {base_case_std} | {delta_case_std} | {focus_repeat_std} | {base_repeat_std} | {delta_repeat_std} | {focus_ece} | {base_ece} | {delta_ece} | {focus_better} | {base_better} | {compared} | {judgement} |".format(
                modelset=row.get("modelset_key", "unknown"),
                focus_case_f1=_fmt(row.get("focus_best_case_f1_mean")),
                base_case_f1=_fmt(row.get("baseline_best_case_f1_mean")),
                delta_case_f1=_fmt_delta(row.get("delta_best_case_f1_mean")),
                focus_case_std=_fmt(row.get("focus_best_case_f1_std")),
                base_case_std=_fmt(row.get("baseline_best_case_f1_std")),
                delta_case_std=_fmt_delta(row.get("delta_best_case_f1_std")),
                focus_repeat_std=_fmt(row.get("focus_best_case_f1_std_repeat_mean")),
                base_repeat_std=_fmt(row.get("baseline_best_case_f1_std_repeat_mean")),
                delta_repeat_std=_fmt_delta(row.get("delta_best_case_f1_std_repeat_mean")),
                focus_ece=_fmt(row.get("focus_best_calibration_ece")),
                base_ece=_fmt(row.get("baseline_best_calibration_ece")),
                delta_ece=_fmt_delta(row.get("delta_best_calibration_ece")),
                focus_better=int(row.get("focus_better_count", 0)),
                base_better=int(row.get("baseline_better_count", 0)),
                compared=int(row.get("compared_metric_count", 0)),
                judgement=row.get("judgement", "n/a"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def compare_study_sweep_summaries(
    focus_summary_path: str | Path,
    baseline_summary_path: str | Path,
    output_prefix: str | Path,
    focus_label: str = "focus",
    baseline_label: str = "baseline",
    epsilon: float = 1e-9,
) -> dict[str, Any]:
    focus_summary = _read_json(focus_summary_path)
    baseline_summary = _read_json(baseline_summary_path)

    focus_rows = _modelset_rows_by_key(focus_summary)
    baseline_rows = _modelset_rows_by_key(baseline_summary)
    modelset_keys = sorted(set(focus_rows.keys()) | set(baseline_rows.keys()))

    rows: list[dict[str, Any]] = []
    for modelset_key in modelset_keys:
        focus_row = focus_rows.get(modelset_key)
        baseline_row = baseline_rows.get(modelset_key)
        payload: dict[str, Any] = {
            "modelset_key": modelset_key,
            "focus_status": str((focus_row or {}).get("status") or "missing"),
            "baseline_status": str((baseline_row or {}).get("status") or "missing"),
            "focus_study_summary_json_path": (focus_row or {}).get("study_summary_json_path"),
            "baseline_study_summary_json_path": (baseline_row or {}).get("study_summary_json_path"),
        }

        focus_better_count = 0
        baseline_better_count = 0
        tie_count = 0
        compared_metric_count = 0

        for metric_key, higher_is_better in CORE_METRIC_SPECS + AUX_METRIC_SPECS:
            focus_value = _safe_float((focus_row or {}).get(metric_key))
            baseline_value = _safe_float((baseline_row or {}).get(metric_key))
            delta, flag = _compare_metric(
                focus_value=focus_value,
                baseline_value=baseline_value,
                higher_is_better=higher_is_better,
                epsilon=float(epsilon),
            )
            payload[f"focus_{metric_key}"] = focus_value
            payload[f"baseline_{metric_key}"] = baseline_value
            payload[f"delta_{metric_key}"] = delta
            payload[f"compare_{metric_key}"] = flag

            if metric_key in {key for key, _ in CORE_METRIC_SPECS} and flag != "n/a":
                compared_metric_count += 1
                if flag == "focus_better":
                    focus_better_count += 1
                elif flag == "baseline_better":
                    baseline_better_count += 1
                else:
                    tie_count += 1

        payload["compared_metric_count"] = compared_metric_count
        payload["focus_better_count"] = focus_better_count
        payload["baseline_better_count"] = baseline_better_count
        payload["tie_count"] = tie_count
        payload["judgement"] = _judgement(
            focus_better_count=focus_better_count,
            baseline_better_count=baseline_better_count,
            compared_metric_count=compared_metric_count,
        )
        rows.append(payload)

    rows.sort(
        key=lambda item: (
            int(item.get("focus_better_count", 0)) - int(item.get("baseline_better_count", 0)),
            int(item.get("compared_metric_count", 0)),
            str(item.get("modelset_key", "")),
        ),
        reverse=True,
    )

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    summary_csv_path = prefix.with_name(f"{prefix.name}_rows.csv")

    fieldnames = [
        "modelset_key",
        "focus_status",
        "baseline_status",
        "focus_study_summary_json_path",
        "baseline_study_summary_json_path",
        "compared_metric_count",
        "focus_better_count",
        "baseline_better_count",
        "tie_count",
        "judgement",
    ]
    for metric_key, _ in CORE_METRIC_SPECS + AUX_METRIC_SPECS:
        fieldnames.extend(
            [
                f"focus_{metric_key}",
                f"baseline_{metric_key}",
                f"delta_{metric_key}",
                f"compare_{metric_key}",
            ]
        )
    with summary_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    summary: dict[str, Any] = {
        "status": "completed",
        "focus_label": focus_label,
        "baseline_label": baseline_label,
        "focus_summary_path": str(focus_summary_path),
        "baseline_summary_path": str(baseline_summary_path),
        "focus_modelset_count": len(focus_rows),
        "baseline_modelset_count": len(baseline_rows),
        "modelset_count": len(modelset_keys),
        "focus_own_ship_case_eval_mmsis": focus_summary.get("own_ship_case_eval_mmsis", []),
        "baseline_own_ship_case_eval_mmsis": baseline_summary.get("own_ship_case_eval_mmsis", []),
        "rows": rows,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "summary_csv_path": str(summary_csv_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_sweep_compare_markdown(summary), encoding="utf-8")
    return summary

