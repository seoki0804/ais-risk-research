from __future__ import annotations

import csv
import glob
import json
from pathlib import Path
from typing import Any

from .batch_review import collect_dataset_rows_from_batch_summary


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


def _tail_values(entries: list[dict[str, Any]], key: str, window: int) -> list[float]:
    if window <= 0:
        return []
    output: list[float] = []
    for item in entries[-window:]:
        numeric = _safe_float(item.get(key))
        if numeric is not None:
            output.append(float(numeric))
    return output


def _moving_average(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _harmful_delta_component(delta_value: float | None, threshold: float, direction: str) -> float:
    if delta_value is None:
        return 0.0
    if direction == "lower_is_worse":
        harmful_delta = max(0.0, -float(delta_value))
    else:
        harmful_delta = max(0.0, float(delta_value))
    if harmful_delta <= 0.0:
        return 0.0
    threshold_abs = abs(float(threshold))
    if threshold_abs <= 0.0:
        return harmful_delta
    return float(harmful_delta / threshold_abs)


def _alert_rank(alert_level: str) -> int:
    if alert_level == "high":
        return 2
    if alert_level == "medium":
        return 1
    return 0


def _resolve_history_paths(
    history_batch_summary_glob: str | None,
    current_batch_summary_path: str | Path | None,
    max_history: int | None,
) -> list[Path]:
    candidates: dict[str, Path] = {}
    if history_batch_summary_glob:
        for path in glob.glob(history_batch_summary_glob, recursive=True):
            candidate = Path(path)
            candidates[str(candidate.resolve())] = candidate
    if current_batch_summary_path:
        candidate = Path(current_batch_summary_path)
        candidates[str(candidate.resolve())] = candidate

    paths = [path for path in candidates.values() if path.exists()]
    paths.sort(key=lambda item: item.stat().st_mtime if item.exists() else 0.0)
    if max_history is not None and int(max_history) > 0:
        paths = paths[-int(max_history) :]
    return paths


def _build_dataset_timeline(
    batch_summary_paths: list[Path],
    own_ship_case_f1_std_threshold: float,
    own_ship_case_f1_ci95_width_threshold: float,
    calibration_ece_threshold: float,
) -> dict[str, list[dict[str, Any]]]:
    timeline: dict[str, list[dict[str, Any]]] = {}
    for index, batch_summary_path in enumerate(batch_summary_paths):
        batch_summary = _read_json(batch_summary_path)
        rows = collect_dataset_rows_from_batch_summary(
            batch_summary=batch_summary,
            own_ship_case_f1_std_threshold=float(own_ship_case_f1_std_threshold),
            own_ship_case_f1_ci95_width_threshold=float(own_ship_case_f1_ci95_width_threshold),
            calibration_ece_threshold=float(calibration_ece_threshold),
        )
        for row in rows:
            dataset_id = str(row.get("dataset_id") or "unknown")
            item = dict(row)
            item["batch_index"] = index
            item["batch_summary_path"] = str(batch_summary_path)
            item["batch_mtime"] = batch_summary_path.stat().st_mtime if batch_summary_path.exists() else 0.0
            timeline.setdefault(dataset_id, []).append(item)

    for entries in timeline.values():
        entries.sort(key=lambda item: int(item.get("batch_index", 0)))
    return timeline


def _delta(current: dict[str, Any], previous: dict[str, Any] | None, key: str) -> float | None:
    current_value = _safe_float(current.get(key))
    if previous is None:
        return None
    previous_value = _safe_float(previous.get(key))
    if current_value is None or previous_value is None:
        return None
    return float(current_value - previous_value)


def _is_worsening(
    current: dict[str, Any],
    previous: dict[str, Any] | None,
    delta_loo_f1_drop_threshold: float,
    delta_calibration_ece_rise_threshold: float,
    delta_own_ship_case_std_rise_threshold: float,
    delta_own_ship_case_ci95_width_rise_threshold: float,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    current_alert_level = str(current.get("alert_level") or "none")
    if previous is None:
        if current_alert_level == "high":
            reasons.append("new_high_alert")
        return len(reasons) > 0, reasons

    previous_alert_level = str(previous.get("alert_level") or "none")
    if _alert_rank(current_alert_level) > _alert_rank(previous_alert_level):
        reasons.append(f"alert_escalation:{previous_alert_level}->{current_alert_level}")

    delta_alert_count = _delta(current, previous, "alert_count")
    if delta_alert_count is not None and delta_alert_count > 0:
        reasons.append("alert_count_increase")

    delta_loo_f1 = _delta(current, previous, "own_ship_loo_f1_mean")
    if delta_loo_f1 is not None and delta_loo_f1 < -abs(float(delta_loo_f1_drop_threshold)):
        reasons.append("loo_f1_drop")

    delta_cal_ece = _delta(current, previous, "best_calibration_ece")
    if delta_cal_ece is not None and delta_cal_ece > abs(float(delta_calibration_ece_rise_threshold)):
        reasons.append("calibration_ece_rise")

    delta_case_std = _delta(current, previous, "best_own_ship_case_f1_std")
    if delta_case_std is not None and delta_case_std > abs(float(delta_own_ship_case_std_rise_threshold)):
        reasons.append("own_ship_case_std_rise")
    delta_case_ci95_width = _delta(current, previous, "best_own_ship_case_f1_ci95_width")
    if delta_case_ci95_width is not None and delta_case_ci95_width > abs(float(delta_own_ship_case_ci95_width_rise_threshold)):
        reasons.append("own_ship_case_ci95_width_rise")

    return len(reasons) > 0, reasons


def build_batch_trend_report_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Study Batch Trend Report",
        "",
        "## Inputs",
        "",
        f"- history_batch_summary_glob: `{summary.get('history_batch_summary_glob', 'n/a')}`",
        f"- current_batch_summary_path: `{summary.get('current_batch_summary_path', 'n/a')}`",
        f"- history_count: `{summary['history_count']}`",
        f"- own_ship_case_f1_std_threshold: `{summary['own_ship_case_f1_std_threshold']}`",
        f"- own_ship_case_f1_ci95_width_threshold: `{summary['own_ship_case_f1_ci95_width_threshold']}`",
        f"- calibration_ece_threshold: `{summary['calibration_ece_threshold']}`",
        f"- delta_loo_f1_drop_threshold: `{summary['delta_loo_f1_drop_threshold']}`",
        f"- delta_calibration_ece_rise_threshold: `{summary['delta_calibration_ece_rise_threshold']}`",
        f"- delta_own_ship_case_std_rise_threshold: `{summary['delta_own_ship_case_std_rise_threshold']}`",
        f"- delta_own_ship_case_ci95_width_rise_threshold: `{summary['delta_own_ship_case_ci95_width_rise_threshold']}`",
        f"- moving_average_window: `{summary['moving_average_window']}`",
        "",
        "## Top Moving-Average Deviation (Top 3, Risk Direction)",
        "",
        f"- top_mavg_deviation_dataset_count: `{len(summary.get('top_mavg_deviation_rows', []))}`",
        "",
        "| Rank | Dataset | Deviation Score | Break Count | Delta vs MA LOO F1 | Delta vs MA Calibration ECE | Delta vs MA OwnShip Case Std | Delta vs MA OwnShip Case CI95 Width | Latest Alert |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for index, row in enumerate(summary.get("top_mavg_deviation_rows", []), start=1):
        lines.append(
            "| {rank} | {dataset_id} | {score} | {break_count} | {delta_loo} | {delta_ece} | {delta_std} | {delta_ci95_width} | {latest_alert} |".format(
                rank=index,
                dataset_id=row.get("dataset_id", "unknown"),
                score=_fmt(row.get("mavg_deviation_score")),
                break_count=int(row.get("mavg_deviation_break_count", 0)),
                delta_loo=_fmt_delta(row.get("delta_vs_mavg_own_ship_loo_f1_mean")),
                delta_ece=_fmt_delta(row.get("delta_vs_mavg_best_calibration_ece")),
                delta_std=_fmt_delta(row.get("delta_vs_mavg_best_own_ship_case_f1_std")),
                delta_ci95_width=_fmt_delta(row.get("delta_vs_mavg_best_own_ship_case_f1_ci95_width")),
                latest_alert=row.get("latest_alert_level", "none"),
            )
        )

    lines.extend(
        [
            "",
        "## Priority Triage (High Alert or Worsening)",
        "",
        f"- priority_dataset_count: `{summary['priority_dataset_count']}`",
        "",
        "| Rank | Dataset | Latest Alert | Latest Alert Count | Delta Alert Count | Worsening | Reasons | Latest Batch |",
        "|---|---|---|---:|---:|---|---|---|",
        ]
    )
    for index, row in enumerate(summary.get("priority_rows", []), start=1):
        lines.append(
            "| {rank} | {dataset_id} | {alert_level} | {alert_count} | {delta_alert_count} | {worsening} | {reasons} | `{batch}` |".format(
                rank=index,
                dataset_id=row.get("dataset_id", "unknown"),
                alert_level=row.get("latest_alert_level", "none"),
                alert_count=row.get("latest_alert_count", 0),
                delta_alert_count=_fmt_delta(row.get("delta_alert_count"), digits=0),
                worsening="yes" if row.get("worsening") else "no",
                reasons=", ".join(row.get("worsening_reasons", [])) if row.get("worsening_reasons") else "n/a",
                batch=row.get("latest_batch_summary_path", "n/a"),
            )
        )

    lines.extend(
        [
            "",
            "## Dataset Trend Table",
            "",
            "| Dataset | History Points | Latest Alert | Previous Alert | Delta Alert Count | Latest LOO F1 | MovingAvg LOO F1 | Delta vs MA LOO | Delta LOO F1 | Latest Calibration ECE | MovingAvg Calibration ECE | Delta vs MA Calibration ECE | Delta Calibration ECE | Latest OwnShip Case Std | MovingAvg OwnShip Case Std | Delta vs MA OwnShip Case Std | Delta OwnShip Case Std | Latest OwnShip Case CI95 Width | MovingAvg OwnShip Case CI95 Width | Delta vs MA OwnShip Case CI95 Width | Delta OwnShip Case CI95 Width |",
            "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary.get("dataset_rows", []):
        lines.append(
            "| {dataset_id} | {history_points} | {latest_alert} | {previous_alert} | {delta_alert_count} | {latest_loo} | {mavg_loo} | {delta_vs_mavg_loo} | {delta_loo} | {latest_ece} | {mavg_ece} | {delta_vs_mavg_ece} | {delta_ece} | {latest_std} | {mavg_std} | {delta_vs_mavg_std} | {delta_std} | {latest_ci95_width} | {mavg_ci95_width} | {delta_vs_mavg_ci95_width} | {delta_ci95_width} |".format(
                dataset_id=row.get("dataset_id", "unknown"),
                history_points=row.get("history_points", 0),
                latest_alert=row.get("latest_alert_level", "none"),
                previous_alert=row.get("previous_alert_level", "n/a"),
                delta_alert_count=_fmt_delta(row.get("delta_alert_count"), digits=0),
                latest_loo=_fmt(row.get("latest_own_ship_loo_f1_mean")),
                mavg_loo=_fmt(row.get("moving_avg_own_ship_loo_f1_mean")),
                delta_vs_mavg_loo=_fmt_delta(row.get("delta_vs_mavg_own_ship_loo_f1_mean")),
                delta_loo=_fmt_delta(row.get("delta_own_ship_loo_f1_mean")),
                latest_ece=_fmt(row.get("latest_best_calibration_ece")),
                mavg_ece=_fmt(row.get("moving_avg_best_calibration_ece")),
                delta_vs_mavg_ece=_fmt_delta(row.get("delta_vs_mavg_best_calibration_ece")),
                delta_ece=_fmt_delta(row.get("delta_best_calibration_ece")),
                latest_std=_fmt(row.get("latest_best_own_ship_case_f1_std")),
                mavg_std=_fmt(row.get("moving_avg_best_own_ship_case_f1_std")),
                delta_vs_mavg_std=_fmt_delta(row.get("delta_vs_mavg_best_own_ship_case_f1_std")),
                delta_std=_fmt_delta(row.get("delta_best_own_ship_case_f1_std")),
                latest_ci95_width=_fmt(row.get("latest_best_own_ship_case_f1_ci95_width")),
                mavg_ci95_width=_fmt(row.get("moving_avg_best_own_ship_case_f1_ci95_width")),
                delta_vs_mavg_ci95_width=_fmt_delta(row.get("delta_vs_mavg_best_own_ship_case_f1_ci95_width")),
                delta_ci95_width=_fmt_delta(row.get("delta_best_own_ship_case_f1_ci95_width")),
            )
        )
    lines.append("")
    return "\n".join(lines)


def build_batch_trend_report(
    output_prefix: str | Path,
    history_batch_summary_glob: str | None = None,
    current_batch_summary_path: str | Path | None = None,
    max_history: int | None = 8,
    own_ship_case_f1_std_threshold: float = 0.10,
    own_ship_case_f1_ci95_width_threshold: float = 0.20,
    calibration_ece_threshold: float = 0.15,
    delta_loo_f1_drop_threshold: float = 0.02,
    delta_calibration_ece_rise_threshold: float = 0.02,
    delta_own_ship_case_std_rise_threshold: float = 0.02,
    delta_own_ship_case_ci95_width_rise_threshold: float = 0.02,
    moving_average_window: int = 3,
) -> dict[str, Any]:
    batch_summary_paths = _resolve_history_paths(
        history_batch_summary_glob=history_batch_summary_glob,
        current_batch_summary_path=current_batch_summary_path,
        max_history=max_history,
    )
    if len(batch_summary_paths) < 1:
        raise ValueError("No batch summary files found for trend report.")

    timeline = _build_dataset_timeline(
        batch_summary_paths=batch_summary_paths,
        own_ship_case_f1_std_threshold=float(own_ship_case_f1_std_threshold),
        own_ship_case_f1_ci95_width_threshold=float(own_ship_case_f1_ci95_width_threshold),
        calibration_ece_threshold=float(calibration_ece_threshold),
    )

    dataset_rows: list[dict[str, Any]] = []
    for dataset_id, entries in timeline.items():
        ma_window = max(1, int(moving_average_window))
        latest = entries[-1]
        previous = entries[-2] if len(entries) >= 2 else None
        worsening, reasons = _is_worsening(
            current=latest,
            previous=previous,
            delta_loo_f1_drop_threshold=float(delta_loo_f1_drop_threshold),
            delta_calibration_ece_rise_threshold=float(delta_calibration_ece_rise_threshold),
            delta_own_ship_case_std_rise_threshold=float(delta_own_ship_case_std_rise_threshold),
            delta_own_ship_case_ci95_width_rise_threshold=float(delta_own_ship_case_ci95_width_rise_threshold),
        )
        moving_avg_loo = _moving_average(_tail_values(entries, "own_ship_loo_f1_mean", window=ma_window))
        moving_avg_cal_ece = _moving_average(_tail_values(entries, "best_calibration_ece", window=ma_window))
        moving_avg_case_std = _moving_average(_tail_values(entries, "best_own_ship_case_f1_std", window=ma_window))
        moving_avg_case_ci95_width = _moving_average(_tail_values(entries, "best_own_ship_case_f1_ci95_width", window=ma_window))
        latest_loo = _safe_float(latest.get("own_ship_loo_f1_mean"))
        latest_cal_ece = _safe_float(latest.get("best_calibration_ece"))
        latest_case_std = _safe_float(latest.get("best_own_ship_case_f1_std"))
        latest_case_ci95_width = _safe_float(latest.get("best_own_ship_case_f1_ci95_width"))
        delta_vs_mavg_loo = (latest_loo - moving_avg_loo) if (latest_loo is not None and moving_avg_loo is not None) else None
        delta_vs_mavg_cal_ece = (
            (latest_cal_ece - moving_avg_cal_ece) if (latest_cal_ece is not None and moving_avg_cal_ece is not None) else None
        )
        delta_vs_mavg_case_std = (
            (latest_case_std - moving_avg_case_std) if (latest_case_std is not None and moving_avg_case_std is not None) else None
        )
        delta_vs_mavg_case_ci95_width = (
            (latest_case_ci95_width - moving_avg_case_ci95_width)
            if (latest_case_ci95_width is not None and moving_avg_case_ci95_width is not None)
            else None
        )
        mavg_loo_component = _harmful_delta_component(
            delta_value=delta_vs_mavg_loo,
            threshold=float(delta_loo_f1_drop_threshold),
            direction="lower_is_worse",
        )
        mavg_cal_ece_component = _harmful_delta_component(
            delta_value=delta_vs_mavg_cal_ece,
            threshold=float(delta_calibration_ece_rise_threshold),
            direction="higher_is_worse",
        )
        mavg_case_std_component = _harmful_delta_component(
            delta_value=delta_vs_mavg_case_std,
            threshold=float(delta_own_ship_case_std_rise_threshold),
            direction="higher_is_worse",
        )
        mavg_case_ci95_width_component = _harmful_delta_component(
            delta_value=delta_vs_mavg_case_ci95_width,
            threshold=float(delta_own_ship_case_ci95_width_rise_threshold),
            direction="higher_is_worse",
        )
        mavg_deviation_break_count = (
            int(mavg_loo_component > 0.0)
            + int(mavg_cal_ece_component > 0.0)
            + int(mavg_case_std_component > 0.0)
            + int(mavg_case_ci95_width_component > 0.0)
        )
        mavg_deviation_score = float(
            mavg_loo_component + mavg_cal_ece_component + mavg_case_std_component + mavg_case_ci95_width_component
        )

        if delta_vs_mavg_loo is not None and delta_vs_mavg_loo < -abs(float(delta_loo_f1_drop_threshold)):
            reasons.append("loo_f1_below_mavg")
        if delta_vs_mavg_cal_ece is not None and delta_vs_mavg_cal_ece > abs(float(delta_calibration_ece_rise_threshold)):
            reasons.append("calibration_ece_above_mavg")
        if delta_vs_mavg_case_std is not None and delta_vs_mavg_case_std > abs(float(delta_own_ship_case_std_rise_threshold)):
            reasons.append("own_ship_case_std_above_mavg")
        if delta_vs_mavg_case_ci95_width is not None and delta_vs_mavg_case_ci95_width > abs(
            float(delta_own_ship_case_ci95_width_rise_threshold)
        ):
            reasons.append("own_ship_case_ci95_width_above_mavg")
        if reasons:
            # Keep insertion order and remove duplicates from mixed rule checks.
            reasons = list(dict.fromkeys(reasons))
            worsening = True

        latest_alert_level = str(latest.get("alert_level") or "none")
        row = {
            "dataset_id": dataset_id,
            "history_points": len(entries),
            "latest_batch_summary_path": latest.get("batch_summary_path"),
            "previous_batch_summary_path": previous.get("batch_summary_path") if previous else "",
            "latest_alert_level": latest_alert_level,
            "latest_alert_count": int(latest.get("alert_count", 0)),
            "previous_alert_level": str(previous.get("alert_level")) if previous else "n/a",
            "previous_alert_count": int(previous.get("alert_count", 0)) if previous else None,
            "delta_alert_count": _delta(latest, previous, "alert_count"),
            "latest_own_ship_loo_f1_mean": _safe_float(latest.get("own_ship_loo_f1_mean")),
            "delta_own_ship_loo_f1_mean": _delta(latest, previous, "own_ship_loo_f1_mean"),
            "latest_best_calibration_ece": _safe_float(latest.get("best_calibration_ece")),
            "delta_best_calibration_ece": _delta(latest, previous, "best_calibration_ece"),
            "latest_best_own_ship_case_f1_std": _safe_float(latest.get("best_own_ship_case_f1_std")),
            "delta_best_own_ship_case_f1_std": _delta(latest, previous, "best_own_ship_case_f1_std"),
            "latest_best_own_ship_case_f1_ci95_width": _safe_float(latest.get("best_own_ship_case_f1_ci95_width")),
            "delta_best_own_ship_case_f1_ci95_width": _delta(latest, previous, "best_own_ship_case_f1_ci95_width"),
            "moving_avg_own_ship_loo_f1_mean": moving_avg_loo,
            "moving_avg_best_calibration_ece": moving_avg_cal_ece,
            "moving_avg_best_own_ship_case_f1_std": moving_avg_case_std,
            "moving_avg_best_own_ship_case_f1_ci95_width": moving_avg_case_ci95_width,
            "delta_vs_mavg_own_ship_loo_f1_mean": delta_vs_mavg_loo,
            "delta_vs_mavg_best_calibration_ece": delta_vs_mavg_cal_ece,
            "delta_vs_mavg_best_own_ship_case_f1_std": delta_vs_mavg_case_std,
            "delta_vs_mavg_best_own_ship_case_f1_ci95_width": delta_vs_mavg_case_ci95_width,
            "mavg_deviation_loo_component": mavg_loo_component,
            "mavg_deviation_calibration_ece_component": mavg_cal_ece_component,
            "mavg_deviation_own_ship_case_std_component": mavg_case_std_component,
            "mavg_deviation_own_ship_case_ci95_width_component": mavg_case_ci95_width_component,
            "mavg_deviation_break_count": mavg_deviation_break_count,
            "mavg_deviation_score": mavg_deviation_score,
            "latest_study_summary_json_path": latest.get("study_summary_json_path"),
            "worsening": bool(worsening),
            "worsening_reasons": reasons,
        }
        row["priority"] = (latest_alert_level == "high") or bool(worsening)
        dataset_rows.append(row)

    def priority_sort_key(item: dict[str, Any]) -> tuple[float, float, float, str]:
        return (
            float(_alert_rank(str(item.get("latest_alert_level") or "none"))),
            float(item.get("latest_alert_count") or 0),
            float(_safe_float(item.get("delta_alert_count")) or 0.0),
            str(item.get("dataset_id") or ""),
        )

    priority_rows = [item for item in dataset_rows if item.get("priority")]
    priority_rows.sort(key=priority_sort_key, reverse=True)
    dataset_rows.sort(key=lambda item: str(item.get("dataset_id") or ""))
    top_mavg_deviation_rows = sorted(
        dataset_rows,
        key=lambda item: (
            float(_safe_float(item.get("mavg_deviation_score")) or 0.0),
            int(item.get("mavg_deviation_break_count") or 0),
            float(_alert_rank(str(item.get("latest_alert_level") or "none"))),
            str(item.get("dataset_id") or ""),
        ),
        reverse=True,
    )[:3]

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    dataset_trends_csv_path = prefix.with_name(f"{prefix.name}_dataset_trends.csv")

    with dataset_trends_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "dataset_id",
            "history_points",
            "latest_batch_summary_path",
            "previous_batch_summary_path",
            "latest_alert_level",
            "latest_alert_count",
            "previous_alert_level",
            "previous_alert_count",
            "delta_alert_count",
            "latest_own_ship_loo_f1_mean",
            "delta_own_ship_loo_f1_mean",
            "latest_best_calibration_ece",
            "delta_best_calibration_ece",
            "latest_best_own_ship_case_f1_std",
            "delta_best_own_ship_case_f1_std",
            "latest_best_own_ship_case_f1_ci95_width",
            "delta_best_own_ship_case_f1_ci95_width",
            "moving_avg_own_ship_loo_f1_mean",
            "moving_avg_best_calibration_ece",
            "moving_avg_best_own_ship_case_f1_std",
            "moving_avg_best_own_ship_case_f1_ci95_width",
            "delta_vs_mavg_own_ship_loo_f1_mean",
            "delta_vs_mavg_best_calibration_ece",
            "delta_vs_mavg_best_own_ship_case_f1_std",
            "delta_vs_mavg_best_own_ship_case_f1_ci95_width",
            "mavg_deviation_loo_component",
            "mavg_deviation_calibration_ece_component",
            "mavg_deviation_own_ship_case_std_component",
            "mavg_deviation_own_ship_case_ci95_width_component",
            "mavg_deviation_break_count",
            "mavg_deviation_score",
            "worsening",
            "worsening_reasons",
            "priority",
            "latest_study_summary_json_path",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in dataset_rows:
            writer.writerow(
                {
                    **row,
                    "worsening_reasons": "; ".join(row.get("worsening_reasons", [])),
                }
            )

    summary: dict[str, Any] = {
        "status": "completed",
        "history_batch_summary_glob": history_batch_summary_glob,
        "current_batch_summary_path": str(current_batch_summary_path) if current_batch_summary_path else "",
        "history_count": len(batch_summary_paths),
        "history_batch_summary_paths": [str(path) for path in batch_summary_paths],
        "own_ship_case_f1_std_threshold": float(own_ship_case_f1_std_threshold),
        "own_ship_case_f1_ci95_width_threshold": float(own_ship_case_f1_ci95_width_threshold),
        "calibration_ece_threshold": float(calibration_ece_threshold),
        "delta_loo_f1_drop_threshold": float(delta_loo_f1_drop_threshold),
        "delta_calibration_ece_rise_threshold": float(delta_calibration_ece_rise_threshold),
        "delta_own_ship_case_std_rise_threshold": float(delta_own_ship_case_std_rise_threshold),
        "delta_own_ship_case_ci95_width_rise_threshold": float(delta_own_ship_case_ci95_width_rise_threshold),
        "moving_average_window": max(1, int(moving_average_window)),
        "dataset_count": len(dataset_rows),
        "priority_dataset_count": len(priority_rows),
        "dataset_rows": dataset_rows,
        "priority_rows": priority_rows,
        "top_mavg_deviation_rows": top_mavg_deviation_rows,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "dataset_trends_csv_path": str(dataset_trends_csv_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_batch_trend_report_markdown(summary), encoding="utf-8")
    return summary
