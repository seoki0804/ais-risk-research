from __future__ import annotations

import csv
import glob
import json
from pathlib import Path
from typing import Any


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def _threshold_enabled(value: float | None) -> bool:
    numeric = _safe_float(value)
    return numeric is not None and numeric >= 0.0


def _extract_strategy_metrics(validation_summary: dict[str, Any], strategy_key: str) -> dict[str, Any]:
    strategy = validation_summary.get("strategies", {}).get(strategy_key, {})
    payload = {
        "status": strategy.get("status", "missing"),
        "best_model_name": "",
        "f1": None,
        "auroc": None,
        "auprc": None,
    }
    if payload["status"] != "completed":
        return payload

    best_model = strategy.get("best_model", {})
    payload["best_model_name"] = str(best_model.get("name") or "")
    if strategy_key == "own_ship_loo":
        payload["f1"] = _safe_float(best_model.get("f1_mean"))
        payload["auroc"] = _safe_float(best_model.get("auroc_mean"))
        payload["auprc"] = _safe_float(best_model.get("auprc_mean"))
    else:
        payload["f1"] = _safe_float(best_model.get("f1"))
        payload["auroc"] = _safe_float(best_model.get("auroc"))
        payload["auprc"] = _safe_float(best_model.get("auprc"))
    return payload


def _extract_best_benchmark_metrics(study_summary: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "best_model_name": "",
        "f1": None,
        "auroc": None,
        "auprc": None,
    }
    benchmark = study_summary.get("benchmark", {})
    if not isinstance(benchmark, dict):
        return payload
    models = benchmark.get("models", {})
    if not isinstance(models, dict):
        return payload

    best_model_name = ""
    best_f1 = None
    best_auroc = None
    best_auprc = None
    for model_name, metrics in models.items():
        if not isinstance(metrics, dict):
            continue
        if metrics.get("status") == "skipped":
            continue
        f1 = _safe_float(metrics.get("f1"))
        if f1 is None:
            continue
        if best_f1 is None or f1 > best_f1:
            best_model_name = str(model_name)
            best_f1 = float(f1)
            best_auroc = _safe_float(metrics.get("auroc"))
            best_auprc = _safe_float(metrics.get("auprc"))

    payload["best_model_name"] = best_model_name
    payload["f1"] = best_f1
    payload["auroc"] = best_auroc
    payload["auprc"] = best_auprc
    return payload


def _extract_own_ship_loo_fallback_metrics(study_summary: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "status": "missing",
        "best_model_name": "",
        "f1": None,
        "auroc": None,
        "auprc": None,
    }
    own_ship_loo_path = study_summary.get("own_ship_loo_summary_json_path")
    if not own_ship_loo_path:
        return payload
    own_ship_loo_file = Path(str(own_ship_loo_path))
    if not own_ship_loo_file.exists():
        return payload

    own_ship_loo_summary = _read_json(own_ship_loo_file)
    aggregate_models = own_ship_loo_summary.get("aggregate_models", {})
    if not isinstance(aggregate_models, dict):
        return payload

    best_model_name = ""
    best_f1 = None
    best_auroc = None
    best_auprc = None
    for model_name, metrics in aggregate_models.items():
        if not isinstance(metrics, dict):
            continue
        f1_mean = _safe_float(metrics.get("f1_mean"))
        if f1_mean is None:
            continue
        if best_f1 is None or f1_mean > best_f1:
            best_model_name = str(model_name)
            best_f1 = float(f1_mean)
            best_auroc = _safe_float(metrics.get("auroc_mean"))
            best_auprc = _safe_float(metrics.get("auprc_mean"))

    if best_f1 is not None:
        payload["status"] = "completed"
        payload["best_model_name"] = best_model_name
        payload["f1"] = best_f1
        payload["auroc"] = best_auroc
        payload["auprc"] = best_auprc
    return payload


def _extract_calibration_metrics(study_summary: dict[str, Any]) -> dict[str, Any]:
    output = {
        "calibration_best_model": "",
        "calibration_best_ece": None,
        "calibration_best_brier": None,
        "calibration_own_ship_loo_model_ece": None,
        "calibration_own_ship_loo_model_brier": None,
    }
    calibration_path = study_summary.get("calibration_eval_summary_json_path")
    if not calibration_path:
        return output
    calibration_file = Path(str(calibration_path))
    if not calibration_file.exists():
        return output

    calibration_summary = _read_json(calibration_file)
    models = calibration_summary.get("models", {})
    if not isinstance(models, dict):
        return output

    best_model_name = ""
    best_ece: float | None = None
    best_brier: float | None = None
    for model_name, metrics in models.items():
        if not isinstance(metrics, dict):
            continue
        if metrics.get("status") != "completed":
            continue
        ece = _safe_float(metrics.get("ece"))
        brier = _safe_float(metrics.get("brier_score"))
        if ece is None:
            continue
        if best_ece is None or ece < best_ece:
            best_model_name = str(model_name)
            best_ece = float(ece)
            best_brier = float(brier) if brier is not None else None

    output["calibration_best_model"] = best_model_name
    output["calibration_best_ece"] = best_ece
    output["calibration_best_brier"] = best_brier

    own_ship_loo_best_model = str(study_summary.get("validation_own_ship_loo_best_model") or "")
    if own_ship_loo_best_model and own_ship_loo_best_model in models and isinstance(models[own_ship_loo_best_model], dict):
        loo_metrics = models[own_ship_loo_best_model]
        output["calibration_own_ship_loo_model_ece"] = _safe_float(loo_metrics.get("ece"))
        output["calibration_own_ship_loo_model_brier"] = _safe_float(loo_metrics.get("brier_score"))
    return output


def _extract_own_ship_case_metrics(study_summary: dict[str, Any]) -> dict[str, Any]:
    output = {
        "own_ship_case_best_model": "",
        "own_ship_case_f1_mean": None,
        "own_ship_case_f1_std": None,
        "own_ship_case_f1_ci95_low": None,
        "own_ship_case_f1_ci95_high": None,
        "own_ship_case_f1_ci95_width": None,
        "own_ship_case_f1_std_repeat_mean": None,
        "own_ship_case_f1_std_repeat_max": None,
        "own_ship_case_auroc_mean": None,
        "own_ship_case_ship_count": None,
    }
    case_eval_path = study_summary.get("own_ship_case_eval_summary_json_path")
    if not case_eval_path:
        return output
    case_eval_file = Path(str(case_eval_path))
    if not case_eval_file.exists():
        return output

    case_eval_summary = _read_json(case_eval_file)
    aggregate_models = case_eval_summary.get("aggregate_models", {})
    if not isinstance(aggregate_models, dict):
        return output

    best_model_name = ""
    best_f1_mean: float | None = None
    best_f1_std: float | None = None
    best_f1_ci95_low: float | None = None
    best_f1_ci95_high: float | None = None
    best_f1_ci95_width: float | None = None
    best_f1_std_repeat_mean: float | None = None
    best_f1_std_repeat_max: float | None = None
    best_auroc_mean: float | None = None
    best_ship_count: int | None = None
    for model_name, metrics in aggregate_models.items():
        if not isinstance(metrics, dict):
            continue
        f1_mean = _safe_float(metrics.get("f1_mean"))
        if f1_mean is None:
            continue
        if best_f1_mean is None or f1_mean > best_f1_mean:
            best_model_name = str(model_name)
            best_f1_mean = float(f1_mean)
            best_f1_std = _safe_float(metrics.get("f1_std"))
            best_f1_ci95_low = _safe_float(metrics.get("f1_ci95_low"))
            best_f1_ci95_high = _safe_float(metrics.get("f1_ci95_high"))
            best_f1_ci95_width = _safe_float(metrics.get("f1_ci95_width"))
            best_f1_std_repeat_mean = _safe_float(metrics.get("f1_std_repeat_mean"))
            best_f1_std_repeat_max = _safe_float(metrics.get("f1_std_repeat_max"))
            best_auroc_mean = _safe_float(metrics.get("auroc_mean"))
            ship_count = metrics.get("ship_count")
            try:
                best_ship_count = int(ship_count) if ship_count is not None else None
            except Exception:
                best_ship_count = None

    output["own_ship_case_best_model"] = best_model_name
    output["own_ship_case_f1_mean"] = best_f1_mean
    output["own_ship_case_f1_std"] = best_f1_std
    output["own_ship_case_f1_ci95_low"] = best_f1_ci95_low
    output["own_ship_case_f1_ci95_high"] = best_f1_ci95_high
    output["own_ship_case_f1_ci95_width"] = best_f1_ci95_width
    output["own_ship_case_f1_std_repeat_mean"] = best_f1_std_repeat_mean
    output["own_ship_case_f1_std_repeat_max"] = best_f1_std_repeat_max
    output["own_ship_case_auroc_mean"] = best_auroc_mean
    output["own_ship_case_ship_count"] = best_ship_count
    return output


def _annotate_alerts(
    row: dict[str, Any],
    own_ship_case_f1_std_threshold: float | None,
    calibration_best_ece_threshold: float | None,
    own_ship_case_f1_ci95_width_threshold: float | None,
) -> None:
    own_ship_case_std = _safe_float(row.get("own_ship_case_f1_std"))
    calibration_best_ece = _safe_float(row.get("calibration_best_ece"))
    own_ship_case_ci95_width = _safe_float(row.get("own_ship_case_f1_ci95_width"))

    own_ship_case_alert = False
    calibration_alert = False
    own_ship_case_ci95_alert = False
    notes: list[str] = []
    if _threshold_enabled(own_ship_case_f1_std_threshold):
        threshold = float(own_ship_case_f1_std_threshold)
        own_ship_case_alert = own_ship_case_std is not None and own_ship_case_std > threshold
        if own_ship_case_alert:
            notes.append(f"own_ship_case_f1_std>{threshold:.3f}")
    if _threshold_enabled(calibration_best_ece_threshold):
        threshold = float(calibration_best_ece_threshold)
        calibration_alert = calibration_best_ece is not None and calibration_best_ece > threshold
        if calibration_alert:
            notes.append(f"calibration_best_ece>{threshold:.3f}")
    if _threshold_enabled(own_ship_case_f1_ci95_width_threshold):
        threshold = float(own_ship_case_f1_ci95_width_threshold)
        own_ship_case_ci95_alert = own_ship_case_ci95_width is not None and own_ship_case_ci95_width > threshold
        if own_ship_case_ci95_alert:
            notes.append(f"own_ship_case_f1_ci95_width>{threshold:.3f}")

    alert_count = int(own_ship_case_alert) + int(calibration_alert) + int(own_ship_case_ci95_alert)
    if alert_count >= 2:
        alert_level = "high"
    elif alert_count == 1:
        alert_level = "medium"
    else:
        alert_level = "none"

    row["alert_own_ship_case_unstable"] = bool(own_ship_case_alert)
    row["alert_calibration_poor"] = bool(calibration_alert)
    row["alert_own_ship_case_ci95_wide"] = bool(own_ship_case_ci95_alert)
    row["alert_count"] = alert_count
    row["alert_level"] = alert_level
    row["alert_notes"] = "; ".join(notes)


def _load_study_summary_with_validation(path: str | Path) -> dict[str, Any] | None:
    study_summary = _read_json(path)
    empty_strategy = {
        "status": "missing",
        "best_model_name": "",
        "f1": None,
        "auroc": None,
        "auprc": None,
    }
    timestamp_metrics = dict(empty_strategy)
    own_ship_metrics = dict(empty_strategy)
    own_ship_loo_metrics = dict(empty_strategy)

    validation_file = None
    validation_path = study_summary.get("validation_suite_summary_json_path")
    if validation_path:
        validation_file = Path(str(validation_path))
        if validation_file.exists():
            validation_summary = _read_json(validation_file)
            timestamp_metrics = _extract_strategy_metrics(validation_summary, "timestamp_split")
            own_ship_metrics = _extract_strategy_metrics(validation_summary, "own_ship_split")
            own_ship_loo_metrics = _extract_strategy_metrics(validation_summary, "own_ship_loo")

    fallback_own_ship_loo = _extract_own_ship_loo_fallback_metrics(study_summary)
    if own_ship_loo_metrics.get("f1") is None and fallback_own_ship_loo.get("f1") is not None:
        own_ship_loo_metrics = fallback_own_ship_loo

    benchmark_best = _extract_best_benchmark_metrics(study_summary)
    split_strategy = str(study_summary.get("pairwise_split_strategy") or "timestamp")
    if split_strategy == "own_ship":
        if own_ship_metrics.get("f1") is None and benchmark_best.get("f1") is not None:
            own_ship_metrics = {
                "status": "completed",
                "best_model_name": str(benchmark_best.get("best_model_name") or ""),
                "f1": benchmark_best.get("f1"),
                "auroc": benchmark_best.get("auroc"),
                "auprc": benchmark_best.get("auprc"),
            }
    else:
        if timestamp_metrics.get("f1") is None and benchmark_best.get("f1") is not None:
            timestamp_metrics = {
                "status": "completed",
                "best_model_name": str(benchmark_best.get("best_model_name") or ""),
                "f1": benchmark_best.get("f1"),
                "auroc": benchmark_best.get("auroc"),
                "auprc": benchmark_best.get("auprc"),
            }

    study_summary["validation_own_ship_loo_best_model"] = own_ship_loo_metrics["best_model_name"]
    calibration_metrics = _extract_calibration_metrics(study_summary)
    own_ship_case_metrics = _extract_own_ship_case_metrics(study_summary)

    pairwise = study_summary.get("pairwise", {})
    row = {
        "dataset_id": str(study_summary.get("dataset_id", Path(path).stem)),
        "manifest_path": str(study_summary.get("manifest_path", "")),
        "study_summary_json_path": str(path),
        "validation_suite_summary_json_path": str(validation_file) if validation_file is not None and validation_file.exists() else "",
        "pairwise_row_count": int(pairwise.get("row_count", 0)),
        "pairwise_positive_rate": _safe_float(pairwise.get("positive_rate")),
        "timestamp_best_model": timestamp_metrics["best_model_name"],
        "timestamp_f1": timestamp_metrics["f1"],
        "timestamp_auroc": timestamp_metrics["auroc"],
        "timestamp_auprc": timestamp_metrics["auprc"],
        "own_ship_best_model": own_ship_metrics["best_model_name"],
        "own_ship_f1": own_ship_metrics["f1"],
        "own_ship_auroc": own_ship_metrics["auroc"],
        "own_ship_auprc": own_ship_metrics["auprc"],
        "own_ship_loo_best_model": own_ship_loo_metrics["best_model_name"],
        "own_ship_loo_f1_mean": own_ship_loo_metrics["f1"],
        "own_ship_loo_auroc_mean": own_ship_loo_metrics["auroc"],
        "own_ship_loo_auprc_mean": own_ship_loo_metrics["auprc"],
        "calibration_best_model": calibration_metrics["calibration_best_model"],
        "calibration_best_ece": calibration_metrics["calibration_best_ece"],
        "calibration_best_brier": calibration_metrics["calibration_best_brier"],
        "calibration_own_ship_loo_model_ece": calibration_metrics["calibration_own_ship_loo_model_ece"],
        "calibration_own_ship_loo_model_brier": calibration_metrics["calibration_own_ship_loo_model_brier"],
        "own_ship_case_best_model": own_ship_case_metrics["own_ship_case_best_model"],
        "own_ship_case_f1_mean": own_ship_case_metrics["own_ship_case_f1_mean"],
        "own_ship_case_f1_std": own_ship_case_metrics["own_ship_case_f1_std"],
        "own_ship_case_f1_ci95_low": own_ship_case_metrics["own_ship_case_f1_ci95_low"],
        "own_ship_case_f1_ci95_high": own_ship_case_metrics["own_ship_case_f1_ci95_high"],
        "own_ship_case_f1_ci95_width": own_ship_case_metrics["own_ship_case_f1_ci95_width"],
        "own_ship_case_f1_std_repeat_mean": own_ship_case_metrics["own_ship_case_f1_std_repeat_mean"],
        "own_ship_case_f1_std_repeat_max": own_ship_case_metrics["own_ship_case_f1_std_repeat_max"],
        "own_ship_case_auroc_mean": own_ship_case_metrics["own_ship_case_auroc_mean"],
        "own_ship_case_ship_count": own_ship_case_metrics["own_ship_case_ship_count"],
    }
    return row


def build_validation_leaderboard(
    study_summary_glob: str = "outputs/**/*_study_summary.json",
    output_csv_path: str | Path = "outputs/validation_leaderboard.csv",
    output_md_path: str | Path = "outputs/validation_leaderboard.md",
    sort_by: str = "own_ship_loo_f1_mean",
    descending: bool = True,
    deduplicate_dataset_id: bool = True,
    own_ship_case_f1_std_threshold: float | None = 0.10,
    calibration_best_ece_threshold: float | None = 0.15,
    own_ship_case_f1_ci95_width_threshold: float | None = 0.20,
) -> dict[str, Any]:
    paths = sorted(Path(path) for path in glob.glob(study_summary_glob, recursive=True))
    rows: list[dict[str, Any]] = []
    for path in paths:
        row = _load_study_summary_with_validation(path)
        if row is not None:
            _annotate_alerts(
                row=row,
                own_ship_case_f1_std_threshold=own_ship_case_f1_std_threshold,
                calibration_best_ece_threshold=calibration_best_ece_threshold,
                own_ship_case_f1_ci95_width_threshold=own_ship_case_f1_ci95_width_threshold,
            )
            rows.append(row)

    def metric_value(item: dict[str, Any]) -> float | None:
        return _safe_float(item.get(sort_by))

    def sort_key(item: dict[str, Any]) -> float:
        value = metric_value(item)
        if value is None:
            return float("-inf") if descending else float("inf")
        return value

    def is_better(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
        candidate_value = metric_value(candidate)
        current_value = metric_value(current)
        if candidate_value is None and current_value is None:
            return False
        if candidate_value is None:
            return False
        if current_value is None:
            return True
        if descending:
            return candidate_value > current_value
        return candidate_value < current_value

    if deduplicate_dataset_id:
        deduped: dict[str, dict[str, Any]] = {}
        for row in rows:
            dataset_id = str(row.get("dataset_id") or "")
            if not dataset_id:
                continue
            current = deduped.get(dataset_id)
            if current is None:
                deduped[dataset_id] = row
                continue
            if is_better(row, current):
                deduped[dataset_id] = row
                continue
            current_score = metric_value(current)
            candidate_score = metric_value(row)
            if candidate_score == current_score:
                current_path = Path(str(current.get("study_summary_json_path", "")))
                candidate_path = Path(str(row.get("study_summary_json_path", "")))
                current_mtime = current_path.stat().st_mtime if current_path.exists() else 0.0
                candidate_mtime = candidate_path.stat().st_mtime if candidate_path.exists() else 0.0
                if candidate_mtime > current_mtime:
                    deduped[dataset_id] = row
        rows = list(deduped.values())

    rows.sort(key=sort_key, reverse=descending)

    csv_path = Path(output_csv_path)
    md_path = Path(output_md_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "dataset_id",
        "pairwise_row_count",
        "pairwise_positive_rate",
        "timestamp_best_model",
        "timestamp_f1",
        "timestamp_auroc",
        "timestamp_auprc",
        "own_ship_best_model",
        "own_ship_f1",
        "own_ship_auroc",
        "own_ship_auprc",
        "own_ship_loo_best_model",
        "own_ship_loo_f1_mean",
        "own_ship_loo_auroc_mean",
        "own_ship_loo_auprc_mean",
        "calibration_best_model",
        "calibration_best_ece",
        "calibration_best_brier",
        "calibration_own_ship_loo_model_ece",
        "calibration_own_ship_loo_model_brier",
        "own_ship_case_best_model",
        "own_ship_case_f1_mean",
        "own_ship_case_f1_std",
        "own_ship_case_f1_ci95_low",
        "own_ship_case_f1_ci95_high",
        "own_ship_case_f1_ci95_width",
        "own_ship_case_f1_std_repeat_mean",
        "own_ship_case_f1_std_repeat_max",
        "own_ship_case_auroc_mean",
        "own_ship_case_ship_count",
        "alert_own_ship_case_unstable",
        "alert_calibration_poor",
        "alert_own_ship_case_ci95_wide",
        "alert_count",
        "alert_level",
        "alert_notes",
        "study_summary_json_path",
        "validation_suite_summary_json_path",
        "manifest_path",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    lines = [
        "# Validation Leaderboard",
        "",
        f"- study summary glob: `{study_summary_glob}`",
        f"- total rows: `{len(rows)}`",
        f"- sort by: `{sort_by}` ({'desc' if descending else 'asc'})",
        f"- own_ship_case_f1_std threshold: `{own_ship_case_f1_std_threshold}`",
        f"- own_ship_case_f1_ci95_width threshold: `{own_ship_case_f1_ci95_width_threshold}`",
        f"- calibration_best_ece threshold: `{calibration_best_ece_threshold}`",
        "",
        "| Rank | Dataset | Rows | PosRate | Timestamp F1 | OwnShip F1 | OwnShip LOO F1(mean) | OwnShip Case F1(mean) | OwnShip Case F1 CI95 Width | OwnShip Case F1 Repeat Std(mean) | Best Calibration ECE | Alert Level | Alert Count |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for index, row in enumerate(rows, start=1):
        lines.append(
            "| {rank} | {dataset} | {rows} | {pr} | {f1_t} | {f1_o} | {f1_loo} | {f1_case} | {f1_case_ci95_width} | {f1_case_repeat_std_mean} | {ece} | {alert_level} | {alert_count} |".format(
                rank=index,
                dataset=row["dataset_id"],
                rows=row["pairwise_row_count"],
                pr=_fmt(row["pairwise_positive_rate"]),
                f1_t=_fmt(row["timestamp_f1"]),
                f1_o=_fmt(row["own_ship_f1"]),
                f1_loo=_fmt(row["own_ship_loo_f1_mean"]),
                f1_case=_fmt(row["own_ship_case_f1_mean"]),
                f1_case_ci95_width=_fmt(row.get("own_ship_case_f1_ci95_width")),
                f1_case_repeat_std_mean=_fmt(row.get("own_ship_case_f1_std_repeat_mean")),
                ece=_fmt(row["calibration_best_ece"]),
                alert_level=row.get("alert_level", "none"),
                alert_count=row.get("alert_count", 0),
            )
        )
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "status": "completed",
        "study_summary_glob": study_summary_glob,
        "row_count": len(rows),
        "sort_by": sort_by,
        "descending": bool(descending),
        "deduplicate_dataset_id": bool(deduplicate_dataset_id),
        "own_ship_case_f1_std_threshold": own_ship_case_f1_std_threshold,
        "own_ship_case_f1_ci95_width_threshold": own_ship_case_f1_ci95_width_threshold,
        "calibration_best_ece_threshold": calibration_best_ece_threshold,
        "output_csv_path": str(csv_path),
        "output_md_path": str(md_path),
    }
