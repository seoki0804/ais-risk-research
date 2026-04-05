from __future__ import annotations

import json
from datetime import date
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


def _read_optional_json(path_value: Any) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(str(path_value))
    if not path.exists():
        return {}
    try:
        return _read_json(path)
    except Exception:
        return {}


def _best_model_by_metric(
    models: dict[str, Any],
    metric_key: str,
    higher_is_better: bool = True,
) -> tuple[str | None, float | None]:
    best_name: str | None = None
    best_value: float | None = None
    for model_name, metrics in models.items():
        if not isinstance(metrics, dict):
            continue
        if metrics.get("status") == "skipped":
            continue
        value = _safe_float(metrics.get(metric_key))
        if value is None:
            continue
        if best_value is None:
            best_name = str(model_name)
            best_value = float(value)
            continue
        if higher_is_better and value > best_value:
            best_name = str(model_name)
            best_value = float(value)
        if not higher_is_better and value < best_value:
            best_name = str(model_name)
            best_value = float(value)
    return best_name, best_value


def build_study_journal_markdown(
    study_summary: dict[str, Any],
    calibration_summary: dict[str, Any] | None = None,
    own_ship_loo_summary: dict[str, Any] | None = None,
    own_ship_case_summary: dict[str, Any] | None = None,
    author: str = "Codex",
    date_text: str | None = None,
    topic: str | None = None,
    note: str | None = None,
) -> str:
    calibration_summary = calibration_summary or {}
    own_ship_loo_summary = own_ship_loo_summary or {}
    own_ship_case_summary = own_ship_case_summary or {}

    dataset_id = str(study_summary.get("dataset_id") or "unknown_dataset")
    topic_value = topic or f"{dataset_id}_study_iteration"
    journal_date = date_text or date.today().isoformat()
    pairwise = study_summary.get("pairwise", {})
    benchmark = study_summary.get("benchmark", {})
    benchmark_models = benchmark.get("models", {}) if isinstance(benchmark, dict) else {}

    benchmark_best_name, benchmark_best_f1 = _best_model_by_metric(
        benchmark_models,
        metric_key="f1",
        higher_is_better=True,
    )
    benchmark_best_elapsed = None
    benchmark_best_device = None
    if benchmark_best_name:
        benchmark_best_metrics = benchmark_models.get(benchmark_best_name, {})
        if isinstance(benchmark_best_metrics, dict):
            benchmark_best_elapsed = _safe_float(benchmark_best_metrics.get("elapsed_seconds"))
            if benchmark_best_metrics.get("device"):
                benchmark_best_device = str(benchmark_best_metrics.get("device"))
    benchmark_total_elapsed = _safe_float((benchmark or {}).get("benchmark_elapsed_seconds"))
    calibration_best_name, calibration_best_ece = _best_model_by_metric(
        calibration_summary.get("models", {}),
        metric_key="ece",
        higher_is_better=False,
    )
    loo_best_name, loo_best_f1 = _best_model_by_metric(
        own_ship_loo_summary.get("aggregate_models", {}),
        metric_key="f1_mean",
        higher_is_better=True,
    )
    case_best_name, case_best_f1 = _best_model_by_metric(
        own_ship_case_summary.get("aggregate_models", {}),
        metric_key="f1_mean",
        higher_is_better=True,
    )
    case_best_std = None
    case_best_ci95_low = None
    case_best_ci95_high = None
    case_best_ci95_width = None
    case_best_repeat_std_mean = None
    if case_best_name:
        case_metrics = own_ship_case_summary.get("aggregate_models", {}).get(case_best_name, {})
        if isinstance(case_metrics, dict):
            case_best_std = _safe_float(case_metrics.get("f1_std"))
            case_best_ci95_low = _safe_float(case_metrics.get("f1_ci95_low"))
            case_best_ci95_high = _safe_float(case_metrics.get("f1_ci95_high"))
            case_best_ci95_width = _safe_float(case_metrics.get("f1_ci95_width"))
            case_best_repeat_std_mean = _safe_float(case_metrics.get("f1_std_repeat_mean"))
    case_evaluated_ships = own_ship_case_summary.get("evaluated_own_ship_count")
    case_completed_ships = own_ship_case_summary.get("completed_own_ship_count")
    case_completed_repeats = own_ship_case_summary.get("completed_repeats_total")
    case_metric_cell = (
        f"`{case_best_name or 'n/a'}` (F1 mean `{_fmt(case_best_f1)}`, "
        f"F1 std `{_fmt(case_best_std)}`, "
        f"CI95 `{_fmt(case_best_ci95_low)}`~`{_fmt(case_best_ci95_high)}`, "
        f"CI width `{_fmt(case_best_ci95_width)}`)"
    )
    if case_best_name is None and own_ship_case_summary:
        case_metric_cell = (
            "`skipped` (completed ships `{completed}` / `{evaluated}`, completed repeats `{repeats}`)".format(
                completed=case_completed_ships if case_completed_ships is not None else "n/a",
                evaluated=case_evaluated_ships if case_evaluated_ships is not None else "n/a",
                repeats=case_completed_repeats if case_completed_repeats is not None else "n/a",
            )
        )

    start_date = study_summary.get("start_date") or "[추가 검증 필요]"
    end_date = study_summary.get("end_date") or "[추가 검증 필요]"
    split_strategy = study_summary.get("pairwise_split_strategy") or "timestamp"

    case_interpretation_line = (
        f"- [확정] own-ship fixed case 기준 best F1 mean/std는 `{_fmt(case_best_f1)}` / `{_fmt(case_best_std)}`이고, CI95 폭은 `{_fmt(case_best_ci95_width)}`이다."
    )
    if case_best_name is None and own_ship_case_summary:
        case_interpretation_line = (
            "- [추가 검증 필요] own-ship fixed case 유효 결과가 없어(`completed ships` 부족), "
            "`--own-ship-case-eval-min-rows` 또는 데이터 규모를 조정해야 한다."
        )

    lines = [
        f"# {journal_date} {topic_value}",
        "",
        "## 0. 기본 정보",
        "",
        f"- 날짜: {journal_date}",
        f"- 작성자: {author}",
        "- 로그 유형: `daily`",
        f"- dataset_id: `{dataset_id}`",
        f"- 해역: {study_summary.get('source_slug', '[추가 검증 필요]')}",
        f"- 기간: `{start_date}` ~ `{end_date}`",
        f"- split strategy: `{split_strategy}`",
        f"- study summary: `{study_summary.get('summary_json_path', 'n/a')}`",
        "",
        "## 1. 오늘의 목표",
        "",
        "- 공개 AIS 기반 파이프라인 실행 결과를 기준으로 검증 지표를 고정하고, 다음 반복 실험 의사결정 근거를 남긴다.",
        "- 단일 지표 과신을 피하고 benchmark/LOO/case/calibration을 함께 점검한다.",
        "",
        "## 2. 실행 내용",
        "",
        "| 항목 | 내용 |",
        "|---|---|",
        f"| pairwise row count | `{pairwise.get('row_count', 'n/a')}` |",
        f"| positive rate | `{_fmt(pairwise.get('positive_rate'))}` |",
        f"| benchmark best | `{benchmark_best_name or 'n/a'}` (F1 `{_fmt(benchmark_best_f1)}`) |",
        f"| benchmark elapsed | total `{_fmt(benchmark_total_elapsed)}` sec / best model `{_fmt(benchmark_best_elapsed)}` sec ({benchmark_best_device or 'n/a'}) |",
        f"| own_ship_loo best | `{loo_best_name or 'n/a'}` (F1 mean `{_fmt(loo_best_f1)}`) |",
        f"| own_ship_case best | {case_metric_cell} |",
        f"| calibration best | `{calibration_best_name or 'n/a'}` (ECE `{_fmt(calibration_best_ece)}`) |",
        "",
        "## 3. 핵심 결과 해석",
        "",
        f"- [확정] benchmark 최고 F1은 `{_fmt(benchmark_best_f1)}`이며 best model은 `{benchmark_best_name or 'n/a'}`이다.",
        f"- [확정] benchmark elapsed는 total `{_fmt(benchmark_total_elapsed)}` sec, best model elapsed는 `{_fmt(benchmark_best_elapsed)}` sec이다.",
        f"- [확정] own-ship LOO 기준 best F1 mean은 `{_fmt(loo_best_f1)}`이다.",
        f"- [확정] calibration best ECE는 `{_fmt(calibration_best_ece)}`이다.",
        case_interpretation_line,
        f"- [확정] own-ship fixed case 기준 반복 표준편차 평균은 `{_fmt(case_best_repeat_std_mean)}`이다.",
        "- [합리적 가정] 단일 split 고성능이라도 LOO/case std가 불안정하면 일반화 주장을 보수적으로 해야 한다.",
        "- [리스크] AIS-only 라벨은 realized future separation 정의에 의존하므로 운영 안전성으로 직접 일반화할 수 없다.",
        "",
        "## 4. 다음 액션",
        "",
        "1. [확정] 동일 dataset에서 own_ship_case repeat_count를 늘려 분산 변화를 확인한다.",
        "2. [확정] validation_leaderboard/batch_trend에 반영해 악화 지표를 주기적으로 추적한다.",
        "3. [추가 검증 필요] 해역 변경(다른 dataset_id) 후 동일 설정 재현성 확인.",
    ]
    if note:
        lines.extend(
            [
                "",
                "## 5. 메모",
                "",
                f"- {note}",
            ]
        )

    lines.extend(
        [
            "",
            "## 6. 교수/면접관 설명 포인트",
            "",
            "- \"단일 모델 성능이 아니라 split 전략별 안정성과 calibration까지 묶어 검증했고, 지표 악화는 batch trend로 추적했다.\"",
            "",
        ]
    )
    return "\n".join(lines)


def build_study_journal_from_summary(
    study_summary_path: str | Path,
    output_path: str | Path,
    author: str = "Codex",
    date_text: str | None = None,
    topic: str | None = None,
    note: str | None = None,
) -> str:
    study_summary = _read_json(study_summary_path)
    calibration_summary = _read_optional_json(study_summary.get("calibration_eval_summary_json_path"))
    own_ship_loo_summary = _read_optional_json(study_summary.get("own_ship_loo_summary_json_path"))
    own_ship_case_summary = _read_optional_json(study_summary.get("own_ship_case_eval_summary_json_path"))

    text = build_study_journal_markdown(
        study_summary=study_summary,
        calibration_summary=calibration_summary,
        own_ship_loo_summary=own_ship_loo_summary,
        own_ship_case_summary=own_ship_case_summary,
        author=author,
        date_text=date_text,
        topic=topic,
        note=note,
    )
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return str(destination)
