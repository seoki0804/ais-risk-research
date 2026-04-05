from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


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


def _extract_loo_f1(study_summary: dict[str, Any]) -> float | None:
    validation_path = study_summary.get("validation_suite_summary_json_path")
    if not validation_path:
        validation_file = None
    else:
        validation_file = Path(str(validation_path))

    if validation_file is not None and validation_file.exists():
        validation_summary = _read_json(validation_file)
        best = validation_summary.get("strategies", {}).get("own_ship_loo", {}).get("best_model", {})
        value = _safe_float(best.get("f1_mean"))
        if value is not None:
            return value

    own_ship_loo_summary_path = study_summary.get("own_ship_loo_summary_json_path")
    if not own_ship_loo_summary_path:
        return None
    own_ship_loo_file = Path(str(own_ship_loo_summary_path))
    if not own_ship_loo_file.exists():
        return None
    own_ship_loo_summary = _read_json(own_ship_loo_file)
    aggregate_models = own_ship_loo_summary.get("aggregate_models", {})
    best_f1 = None
    for metrics in aggregate_models.values():
        if not isinstance(metrics, dict):
            continue
        f1_mean = _safe_float(metrics.get("f1_mean"))
        if f1_mean is None:
            continue
        if best_f1 is None or f1_mean > best_f1:
            best_f1 = float(f1_mean)
    return best_f1


def _extract_error_overview(study_summary: dict[str, Any]) -> tuple[int | None, dict[str, Any]]:
    error_summary_path = study_summary.get("error_analysis_summary_json_path")
    if not error_summary_path:
        return None, {}
    error_file = Path(str(error_summary_path))
    if not error_file.exists():
        return None, {}
    error_summary = _read_json(error_file)
    return int(error_summary.get("selected_error_row_count", 0)), error_summary.get("models", {})


def _extract_calibration_overview(study_summary: dict[str, Any]) -> tuple[str | None, float | None, float | None]:
    calibration_summary_path = study_summary.get("calibration_eval_summary_json_path")
    if not calibration_summary_path:
        return None, None, None
    calibration_file = Path(str(calibration_summary_path))
    if not calibration_file.exists():
        return None, None, None
    calibration_summary = _read_json(calibration_file)
    models = calibration_summary.get("models", {})
    best_model = None
    best_ece = None
    best_brier = None
    for model_name, metrics in models.items():
        if metrics.get("status") != "completed":
            continue
        ece = _safe_float(metrics.get("ece"))
        brier = _safe_float(metrics.get("brier_score"))
        if ece is None:
            continue
        if best_ece is None or ece < best_ece:
            best_model = str(model_name)
            best_ece = float(ece)
            best_brier = float(brier) if brier is not None else None
    return best_model, best_ece, best_brier


def _extract_own_ship_case_overview(
    study_summary: dict[str, Any],
) -> tuple[str | None, float | None, float | None, float | None]:
    own_ship_case_summary_path = study_summary.get("own_ship_case_eval_summary_json_path")
    if not own_ship_case_summary_path:
        return None, None, None, None
    own_ship_case_file = Path(str(own_ship_case_summary_path))
    if not own_ship_case_file.exists():
        return None, None, None, None

    own_ship_case_summary = _read_json(own_ship_case_file)
    aggregate_models = own_ship_case_summary.get("aggregate_models", {})
    best_model = None
    best_f1_mean = None
    best_f1_std = None
    best_f1_ci95_width = None
    for model_name, metrics in aggregate_models.items():
        f1_mean = _safe_float(metrics.get("f1_mean"))
        f1_std = _safe_float(metrics.get("f1_std"))
        f1_ci95_width = _safe_float(metrics.get("f1_ci95_width"))
        if f1_mean is None:
            continue
        if best_f1_mean is None or f1_mean > best_f1_mean:
            best_model = str(model_name)
            best_f1_mean = float(f1_mean)
            best_f1_std = float(f1_std) if f1_std is not None else None
            best_f1_ci95_width = float(f1_ci95_width) if f1_ci95_width is not None else None
    return best_model, best_f1_mean, best_f1_std, best_f1_ci95_width


def _annotate_alert_flags(
    dataset_row: dict[str, Any],
    own_ship_case_f1_std_threshold: float = 0.10,
    own_ship_case_f1_ci95_width_threshold: float = 0.20,
    calibration_ece_threshold: float = 0.15,
) -> None:
    own_ship_case_f1_std = _safe_float(dataset_row.get("best_own_ship_case_f1_std"))
    own_ship_case_f1_ci95_width = _safe_float(dataset_row.get("best_own_ship_case_f1_ci95_width"))
    calibration_ece = _safe_float(dataset_row.get("best_calibration_ece"))
    own_ship_case_alert = own_ship_case_f1_std is not None and own_ship_case_f1_std > float(own_ship_case_f1_std_threshold)
    own_ship_case_ci95_alert = own_ship_case_f1_ci95_width is not None and own_ship_case_f1_ci95_width > float(
        own_ship_case_f1_ci95_width_threshold
    )
    calibration_alert = calibration_ece is not None and calibration_ece > float(calibration_ece_threshold)
    alert_count = int(own_ship_case_alert) + int(own_ship_case_ci95_alert) + int(calibration_alert)
    if alert_count >= 2:
        alert_level = "high"
    elif alert_count == 1:
        alert_level = "medium"
    else:
        alert_level = "none"
    notes: list[str] = []
    if own_ship_case_alert:
        notes.append(f"own_ship_case_f1_std>{own_ship_case_f1_std_threshold:.3f}")
    if own_ship_case_ci95_alert:
        notes.append(f"own_ship_case_f1_ci95_width>{own_ship_case_f1_ci95_width_threshold:.3f}")
    if calibration_alert:
        notes.append(f"calibration_best_ece>{calibration_ece_threshold:.3f}")
    dataset_row["alert_level"] = alert_level
    dataset_row["alert_count"] = alert_count
    dataset_row["alert_notes"] = "; ".join(notes)


def _dataset_row_from_study_summary(
    study_summary: dict[str, Any],
    study_summary_json_path: str,
    own_ship_case_f1_std_threshold: float,
    own_ship_case_f1_ci95_width_threshold: float,
    calibration_ece_threshold: float,
) -> dict[str, Any]:
    loo_f1 = _extract_loo_f1(study_summary)
    error_count, _ = _extract_error_overview(study_summary)
    best_calibration_model, best_calibration_ece, best_calibration_brier = _extract_calibration_overview(study_summary)
    best_own_ship_case_model, best_own_ship_case_f1_mean, best_own_ship_case_f1_std, best_own_ship_case_f1_ci95_width = (
        _extract_own_ship_case_overview(study_summary)
    )
    row: dict[str, Any] = {
        "dataset_id": str(study_summary.get("dataset_id", "unknown")),
        "pairwise_row_count": int(study_summary.get("pairwise", {}).get("row_count", 0)),
        "pairwise_positive_rate": _safe_float(study_summary.get("pairwise", {}).get("positive_rate")),
        "pairwise_split_strategy": str(study_summary.get("pairwise_split_strategy", "timestamp")),
        "own_ship_loo_f1_mean": loo_f1,
        "error_case_count": error_count,
        "best_calibration_model": best_calibration_model,
        "best_calibration_ece": best_calibration_ece,
        "best_calibration_brier": best_calibration_brier,
        "best_own_ship_case_model": best_own_ship_case_model,
        "best_own_ship_case_f1_mean": best_own_ship_case_f1_mean,
        "best_own_ship_case_f1_std": best_own_ship_case_f1_std,
        "best_own_ship_case_f1_ci95_width": best_own_ship_case_f1_ci95_width,
        "study_summary_json_path": str(study_summary_json_path),
    }
    _annotate_alert_flags(
        dataset_row=row,
        own_ship_case_f1_std_threshold=float(own_ship_case_f1_std_threshold),
        own_ship_case_f1_ci95_width_threshold=float(own_ship_case_f1_ci95_width_threshold),
        calibration_ece_threshold=float(calibration_ece_threshold),
    )
    return row


def _collect_dataset_rows_from_batch_summary(
    batch_summary: dict[str, Any],
    own_ship_case_f1_std_threshold: float,
    own_ship_case_f1_ci95_width_threshold: float,
    calibration_ece_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = batch_summary.get("items", [])
    completed_items = [item for item in items if item.get("status") == "completed"]
    failed_items = [item for item in items if item.get("status") == "failed"]

    dataset_rows: list[dict[str, Any]] = []
    for item in completed_items:
        study_summary_path = item.get("study_summary_json_path")
        if not study_summary_path:
            continue
        study_file = Path(str(study_summary_path))
        if not study_file.exists():
            continue
        study_summary = _read_json(study_file)
        dataset_rows.append(
            _dataset_row_from_study_summary(
                study_summary=study_summary,
                study_summary_json_path=str(study_file),
                own_ship_case_f1_std_threshold=float(own_ship_case_f1_std_threshold),
                own_ship_case_f1_ci95_width_threshold=float(own_ship_case_f1_ci95_width_threshold),
                calibration_ece_threshold=float(calibration_ece_threshold),
            )
        )
    return dataset_rows, failed_items


def collect_dataset_rows_from_batch_summary(
    batch_summary: dict[str, Any],
    own_ship_case_f1_std_threshold: float = 0.10,
    own_ship_case_f1_ci95_width_threshold: float = 0.20,
    calibration_ece_threshold: float = 0.15,
) -> list[dict[str, Any]]:
    rows, _ = _collect_dataset_rows_from_batch_summary(
        batch_summary=batch_summary,
        own_ship_case_f1_std_threshold=float(own_ship_case_f1_std_threshold),
        own_ship_case_f1_ci95_width_threshold=float(own_ship_case_f1_ci95_width_threshold),
        calibration_ece_threshold=float(calibration_ece_threshold),
    )
    return rows


def _propose_actions(
    dataset_rows: list[dict[str, Any]],
    failed_count: int,
    own_ship_case_f1_std_threshold: float = 0.10,
    own_ship_case_f1_ci95_width_threshold: float = 0.20,
) -> list[str]:
    actions: list[str] = []
    if failed_count > 0:
        actions.append("[확정] 실패한 dataset부터 raw 경로/merge glob/manifest 날짜를 우선 점검한다.")

    low_row_count = [item["dataset_id"] for item in dataset_rows if (item.get("pairwise_row_count") or 0) < 100]
    if low_row_count:
        actions.append(
            "[합리적 가정] pairwise row가 적은 dataset({})은 기간 확장 또는 해역 확장으로 샘플 수를 늘린다.".format(
                ", ".join(low_row_count[:3])
            )
        )

    imbalance = [
        item["dataset_id"]
        for item in dataset_rows
        if item.get("pairwise_positive_rate") is not None
        and (float(item["pairwise_positive_rate"]) < 0.05 or float(item["pairwise_positive_rate"]) > 0.95)
    ]
    if imbalance:
        actions.append(
            "[리스크] class imbalance가 큰 dataset({})은 label distance/horizon과 sampling 규칙을 재검토한다.".format(
                ", ".join(imbalance[:3])
            )
        )

    missing_loo = [item["dataset_id"] for item in dataset_rows if item.get("own_ship_loo_f1_mean") is None]
    if missing_loo:
        actions.append("[추가 검증 필요] own_ship_loo 결과가 없는 dataset은 `--run-validation-suite`로 재실행한다.")

    poor_calibration = [
        item["dataset_id"] for item in dataset_rows if item.get("best_calibration_ece") is not None and item["best_calibration_ece"] > 0.15
    ]
    if poor_calibration:
        actions.append(
            "[추가 검증 필요] calibration ECE가 큰 dataset({})은 threshold 이전에 점수 보정(calibration) 또는 규칙 가중치 재조정을 우선 검토한다.".format(
                ", ".join(poor_calibration[:3])
            )
        )

    unstable_own_ship_case = [
        item["dataset_id"]
        for item in dataset_rows
        if item.get("best_own_ship_case_f1_std") is not None
        and item["best_own_ship_case_f1_std"] > float(own_ship_case_f1_std_threshold)
    ]
    if unstable_own_ship_case:
        actions.append(
            "[추가 검증 필요] own-ship case F1 std가 큰 dataset({})은 선박별 실패 케이스를 분리해 규칙 보강 우선순위를 재설정한다.".format(
                ", ".join(unstable_own_ship_case[:3])
            )
        )
    wide_own_ship_case_ci95 = [
        item["dataset_id"]
        for item in dataset_rows
        if item.get("best_own_ship_case_f1_ci95_width") is not None
        and item["best_own_ship_case_f1_ci95_width"] > float(own_ship_case_f1_ci95_width_threshold)
    ]
    if wide_own_ship_case_ci95:
        actions.append(
            "[추가 검증 필요] own-ship case F1 CI95 폭이 큰 dataset({})은 데이터 분할/표본 수를 재점검하고 repeat split을 늘려 안정성을 재평가한다.".format(
                ", ".join(wide_own_ship_case_ci95[:3])
            )
        )

    high_alert = [item["dataset_id"] for item in dataset_rows if item.get("alert_level") == "high"]
    if high_alert:
        actions.append(
            "[리스크] high alert dataset({})은 다음 실험 사이클에서 최우선 triage 대상으로 고정한다.".format(
                ", ".join(high_alert[:3])
            )
        )

    worsening_alerts = [
        item["dataset_id"]
        for item in dataset_rows
        if _safe_float(item.get("delta_alert_count")) is not None and float(item["delta_alert_count"]) > 0
    ]
    if worsening_alerts:
        actions.append(
            "[리스크] alert_count가 증가한 dataset({})은 직전 대비 성능/신뢰도 저하 요인부터 우선 점검한다.".format(
                ", ".join(worsening_alerts[:3])
            )
        )

    if not actions:
        actions.append("[확정] 현재 배치 결과는 즉시 비교 가능한 상태이며, 다음 실험은 error case 기반 feature 보강으로 진행한다.")
    return actions


def build_study_batch_review_markdown(
    batch_summary: dict[str, Any],
    review_date: str | None = None,
    author: str = "Codex",
    own_ship_case_f1_std_threshold: float = 0.10,
    own_ship_case_f1_ci95_width_threshold: float = 0.20,
    calibration_ece_threshold: float = 0.15,
    previous_batch_summary: dict[str, Any] | None = None,
) -> str:
    date_text = review_date or datetime.now().date().isoformat()
    dataset_rows, failed_items = _collect_dataset_rows_from_batch_summary(
        batch_summary=batch_summary,
        own_ship_case_f1_std_threshold=float(own_ship_case_f1_std_threshold),
        own_ship_case_f1_ci95_width_threshold=float(own_ship_case_f1_ci95_width_threshold),
        calibration_ece_threshold=float(calibration_ece_threshold),
    )

    previous_rows_by_dataset: dict[str, dict[str, Any]] = {}
    if previous_batch_summary is not None:
        previous_rows, _ = _collect_dataset_rows_from_batch_summary(
            batch_summary=previous_batch_summary,
            own_ship_case_f1_std_threshold=float(own_ship_case_f1_std_threshold),
            own_ship_case_f1_ci95_width_threshold=float(own_ship_case_f1_ci95_width_threshold),
            calibration_ece_threshold=float(calibration_ece_threshold),
        )
        previous_rows_by_dataset = {str(item.get("dataset_id")): item for item in previous_rows}

    for row in dataset_rows:
        previous = previous_rows_by_dataset.get(str(row.get("dataset_id")))
        if previous is None:
            row["delta_own_ship_loo_f1_mean"] = None
            row["delta_best_calibration_ece"] = None
            row["delta_best_own_ship_case_f1_std"] = None
            row["delta_best_own_ship_case_f1_ci95_width"] = None
            row["delta_alert_count"] = None
            row["prev_alert_level"] = ""
            continue

        current_loo = _safe_float(row.get("own_ship_loo_f1_mean"))
        prev_loo = _safe_float(previous.get("own_ship_loo_f1_mean"))
        current_cal_ece = _safe_float(row.get("best_calibration_ece"))
        prev_cal_ece = _safe_float(previous.get("best_calibration_ece"))
        current_case_std = _safe_float(row.get("best_own_ship_case_f1_std"))
        prev_case_std = _safe_float(previous.get("best_own_ship_case_f1_std"))
        current_case_ci95_width = _safe_float(row.get("best_own_ship_case_f1_ci95_width"))
        prev_case_ci95_width = _safe_float(previous.get("best_own_ship_case_f1_ci95_width"))
        current_alert_count = _safe_float(row.get("alert_count"))
        prev_alert_count = _safe_float(previous.get("alert_count"))

        row["delta_own_ship_loo_f1_mean"] = (current_loo - prev_loo) if (current_loo is not None and prev_loo is not None) else None
        row["delta_best_calibration_ece"] = (current_cal_ece - prev_cal_ece) if (current_cal_ece is not None and prev_cal_ece is not None) else None
        row["delta_best_own_ship_case_f1_std"] = (current_case_std - prev_case_std) if (current_case_std is not None and prev_case_std is not None) else None
        row["delta_best_own_ship_case_f1_ci95_width"] = (
            (current_case_ci95_width - prev_case_ci95_width)
            if (current_case_ci95_width is not None and prev_case_ci95_width is not None)
            else None
        )
        row["delta_alert_count"] = (current_alert_count - prev_alert_count) if (current_alert_count is not None and prev_alert_count is not None) else None
        row["prev_alert_level"] = str(previous.get("alert_level") or "")

    dataset_rows.sort(
        key=lambda item: item["own_ship_loo_f1_mean"] if item["own_ship_loo_f1_mean"] is not None else -1.0,
        reverse=True,
    )
    high_alert_rows = [item for item in dataset_rows if item.get("alert_level") == "high"]
    high_alert_rows.sort(key=lambda item: int(item.get("alert_count", 0)), reverse=True)

    lines = [
        f"# {date_text} Study Batch Review",
        "",
        "## 0. 기본 정보",
        "",
        f"- 날짜: {date_text}",
        f"- 작성자: {author}",
        f"- manifest_glob: `{batch_summary.get('manifest_glob', 'n/a')}`",
        f"- total_manifests: `{batch_summary.get('total_manifests', 0)}`",
        f"- completed: `{batch_summary.get('completed_count', 0)}`",
        f"- failed: `{batch_summary.get('failed_count', 0)}`",
        f"- own_ship_case_f1_std threshold: `{own_ship_case_f1_std_threshold}`",
        f"- own_ship_case_f1_ci95_width threshold: `{own_ship_case_f1_ci95_width_threshold}`",
        f"- calibration_best_ece threshold: `{calibration_ece_threshold}`",
        "",
        "## 1. High Alert 우선 대상",
        "",
    ]
    if high_alert_rows:
        lines.extend(
            [
                "| dataset_id | alert_level | alert_count | alert_notes | delta_alert_count | summary_path |",
                "|---|---|---:|---|---:|---|",
            ]
        )
        for row in high_alert_rows:
            lines.append(
                "| {dataset_id} | {alert_level} | {alert_count} | {alert_notes} | {delta_alert_count} | `{path}` |".format(
                    dataset_id=row["dataset_id"],
                    alert_level=row.get("alert_level", "none"),
                    alert_count=row.get("alert_count", 0),
                    alert_notes=row.get("alert_notes", "") or "n/a",
                    delta_alert_count=_fmt_delta(row.get("delta_alert_count"), digits=0),
                    path=row.get("study_summary_json_path", "n/a"),
                )
            )
    else:
        lines.append("- high alert dataset 없음")

    lines.extend(
        [
            "",
            "## 2. dataset별 핵심 지표",
            "",
            "| dataset_id | rows | positive_rate | split_strategy | own_ship_loo_f1_mean | delta_loo_f1 | own_ship_case_f1_mean | own_ship_case_f1_std | delta_case_std | own_ship_case_f1_ci95_width | delta_case_ci95_width | error_cases | best_calibration_model | best_calibration_ece | delta_cal_ece | best_calibration_brier | prev_alert_level | alert_level | delta_alert_count |",
            "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|---|---:|",
        ]
    )
    for row in dataset_rows:
        lines.append(
            "| {dataset_id} | {rows} | {pr} | {split} | {loo} | {delta_loo} | {case_f1} | {case_std} | {delta_case_std} | {case_ci95_width} | {delta_case_ci95_width} | {ec} | {cal_model} | {cal_ece} | {delta_cal} | {cal_brier} | {prev_alert} | {alert_level} | {delta_alert_count} |".format(
                dataset_id=row["dataset_id"],
                rows=row["pairwise_row_count"],
                pr=_fmt(row["pairwise_positive_rate"]),
                split=row["pairwise_split_strategy"],
                loo=_fmt(row["own_ship_loo_f1_mean"]),
                delta_loo=_fmt_delta(row.get("delta_own_ship_loo_f1_mean")),
                case_f1=_fmt(row["best_own_ship_case_f1_mean"]),
                case_std=_fmt(row["best_own_ship_case_f1_std"]),
                delta_case_std=_fmt_delta(row.get("delta_best_own_ship_case_f1_std")),
                case_ci95_width=_fmt(row.get("best_own_ship_case_f1_ci95_width")),
                delta_case_ci95_width=_fmt_delta(row.get("delta_best_own_ship_case_f1_ci95_width")),
                ec=str(row["error_case_count"]) if row["error_case_count"] is not None else "n/a",
                cal_model=row["best_calibration_model"] or "n/a",
                cal_ece=_fmt(row["best_calibration_ece"]),
                delta_cal=_fmt_delta(row.get("delta_best_calibration_ece")),
                cal_brier=_fmt(row["best_calibration_brier"]),
                prev_alert=row.get("prev_alert_level", "") or "n/a",
                alert_level=row["alert_level"],
                delta_alert_count=_fmt_delta(row.get("delta_alert_count"), digits=0),
            )
        )

    if failed_items:
        lines.extend(["", "## 3. 실패 항목", ""])
        for item in failed_items:
            lines.append(
                "- `{dataset}`: `{error}`".format(
                    dataset=item.get("dataset_id", "unknown"),
                    error=item.get("error", "n/a"),
                )
            )

    lines.extend(["", "## 4. 다음 액션 제안", ""])
    for index, action in enumerate(
        _propose_actions(
            dataset_rows,
            len(failed_items),
            own_ship_case_f1_std_threshold=float(own_ship_case_f1_std_threshold),
            own_ship_case_f1_ci95_width_threshold=float(own_ship_case_f1_ci95_width_threshold),
        ),
        start=1,
    ):
        lines.append(f"{index}. {action}")

    lines.extend(["", "## 5. 참고 경로", ""])
    for row in dataset_rows[:5]:
        lines.append(f"- `{row['dataset_id']}` summary: `{row['study_summary_json_path']}`")
    lines.append("")
    return "\n".join(lines)


def build_study_batch_review_from_summary(
    batch_summary_path: str | Path,
    output_path: str | Path,
    review_date: str | None = None,
    author: str = "Codex",
    own_ship_case_f1_std_threshold: float = 0.10,
    own_ship_case_f1_ci95_width_threshold: float = 0.20,
    calibration_ece_threshold: float = 0.15,
    previous_batch_summary_path: str | Path | None = None,
) -> str:
    batch_summary = _read_json(batch_summary_path)
    previous_batch_summary = None
    if previous_batch_summary_path is not None:
        previous_file = Path(str(previous_batch_summary_path))
        if previous_file.exists():
            previous_batch_summary = _read_json(previous_file)
    text = build_study_batch_review_markdown(
        batch_summary=batch_summary,
        review_date=review_date,
        author=author,
        own_ship_case_f1_std_threshold=own_ship_case_f1_std_threshold,
        own_ship_case_f1_ci95_width_threshold=own_ship_case_f1_ci95_width_threshold,
        calibration_ece_threshold=calibration_ece_threshold,
        previous_batch_summary=previous_batch_summary,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return str(destination)


def build_study_batch_review_from_payload(
    batch_summary: dict[str, Any],
    output_path: str | Path,
    review_date: str | None = None,
    author: str = "Codex",
    own_ship_case_f1_std_threshold: float = 0.10,
    own_ship_case_f1_ci95_width_threshold: float = 0.20,
    calibration_ece_threshold: float = 0.15,
    previous_batch_summary: dict[str, Any] | None = None,
) -> str:
    text = build_study_batch_review_markdown(
        batch_summary=batch_summary,
        review_date=review_date,
        author=author,
        own_ship_case_f1_std_threshold=own_ship_case_f1_std_threshold,
        own_ship_case_f1_ci95_width_threshold=own_ship_case_f1_ci95_width_threshold,
        calibration_ece_threshold=calibration_ece_threshold,
        previous_batch_summary=previous_batch_summary,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return str(destination)
