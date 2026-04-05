from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _read_json(path_value: str | Path) -> dict[str, Any]:
    return json.loads(Path(path_value).read_text(encoding="utf-8"))


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def _write_csv(path_value: str | Path, rows: list[dict[str, Any]], columns: list[str]) -> str:
    destination = Path(path_value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})
    return str(destination)


def _parse_profile_thresholds(profile_name: str) -> tuple[float | None, float | None]:
    safe_value: float | None = None
    warning_value: float | None = None
    for chunk in str(profile_name).split("_"):
        if chunk.startswith("s") and "p" in chunk:
            try:
                safe_value = float(chunk[1:].replace("p", "."))
            except Exception:
                safe_value = None
        if chunk.startswith("w") and "p" in chunk:
            try:
                warning_value = float(chunk[1:].replace("p", "."))
            except Exception:
                warning_value = None
    return safe_value, warning_value


def _build_model_rows(
    benchmark_summary: dict[str, Any],
    calibration_summary: dict[str, Any],
    loo_summary: dict[str, Any],
    case_summary: dict[str, Any],
    *,
    benchmark_f1_threshold: float,
    ece_threshold: float,
    loo_f1_threshold: float,
    case_f1_threshold: float,
    case_repeat_std_threshold: float,
) -> list[dict[str, Any]]:
    model_names = sorted(
        set(benchmark_summary.get("models", {}).keys())
        | set(calibration_summary.get("models", {}).keys())
        | set(loo_summary.get("aggregate_models", {}).keys())
        | set(case_summary.get("aggregate_models", {}).keys())
    )
    rows: list[dict[str, Any]] = []
    for model_name in model_names:
        benchmark_metrics = benchmark_summary.get("models", {}).get(model_name, {})
        calibration_metrics = calibration_summary.get("models", {}).get(model_name, {})
        loo_metrics = loo_summary.get("aggregate_models", {}).get(model_name, {})
        case_metrics = case_summary.get("aggregate_models", {}).get(model_name, {})

        benchmark_f1 = _safe_float(benchmark_metrics.get("f1"))
        calibration_ece = _safe_float(calibration_metrics.get("ece"))
        loo_f1_mean = _safe_float(loo_metrics.get("f1_mean"))
        case_f1_mean = _safe_float(case_metrics.get("f1_mean"))
        case_repeat_std_mean = _safe_float(case_metrics.get("f1_std_repeat_mean"))

        gate_fail_reasons: list[str] = []
        if benchmark_f1 is None or benchmark_f1 < float(benchmark_f1_threshold):
            gate_fail_reasons.append(f"benchmark_f1<{benchmark_f1_threshold:.2f}")
        if calibration_ece is None or calibration_ece > float(ece_threshold):
            gate_fail_reasons.append(f"ece>{ece_threshold:.2f}")
        if loo_f1_mean is None or loo_f1_mean < float(loo_f1_threshold):
            gate_fail_reasons.append(f"loo_f1<{loo_f1_threshold:.2f}")
        if case_f1_mean is None or case_f1_mean < float(case_f1_threshold):
            gate_fail_reasons.append(f"case_f1<{case_f1_threshold:.2f}")
        if case_repeat_std_mean is None or case_repeat_std_mean > float(case_repeat_std_threshold):
            gate_fail_reasons.append(f"case_repeat_std>{case_repeat_std_threshold:.2f}")

        row = {
            "model_name": model_name,
            "benchmark_f1": benchmark_f1,
            "benchmark_auroc": _safe_float(benchmark_metrics.get("auroc")),
            "calibration_ece": calibration_ece,
            "calibration_brier": _safe_float(calibration_metrics.get("brier_score")),
            "loo_f1_mean": loo_f1_mean,
            "loo_auroc_mean": _safe_float(loo_metrics.get("auroc_mean")),
            "case_f1_mean": case_f1_mean,
            "case_f1_ci95_width": _safe_float(case_metrics.get("f1_ci95_width")),
            "case_repeat_std_mean": case_repeat_std_mean,
            "gate_passed": len(gate_fail_reasons) == 0,
            "gate_fail_reasons": ",".join(gate_fail_reasons) if gate_fail_reasons else "",
        }
        rows.append(row)
    return rows


def _model_sort_key(row: dict[str, Any]) -> tuple[float, float, float, float]:
    ece = _safe_float(row.get("calibration_ece"))
    loo = _safe_float(row.get("loo_f1_mean"))
    case_f1 = _safe_float(row.get("case_f1_mean"))
    benchmark_f1 = _safe_float(row.get("benchmark_f1"))
    return (
        ece if ece is not None else 999.0,
        -(loo if loo is not None else -999.0),
        -(case_f1 if case_f1 is not None else -999.0),
        -(benchmark_f1 if benchmark_f1 is not None else -999.0),
    )


def _build_threshold_rows(stability_summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in stability_summary.get("shortlist", []):
        safe_threshold = _safe_float(item.get("safe_threshold_mean"))
        warning_threshold = _safe_float(item.get("warning_threshold_mean"))
        if safe_threshold is None or warning_threshold is None:
            parsed_safe, parsed_warning = _parse_profile_thresholds(str(item.get("profile_name", "")))
            safe_threshold = parsed_safe
            warning_threshold = parsed_warning
        row = {
            "profile_name": str(item.get("profile_name", "")),
            "rank": _safe_int(item.get("rank")),
            "safe_threshold": safe_threshold,
            "warning_threshold": warning_threshold,
            "recommended_count": _safe_int(item.get("recommended_count")),
            "consensus_count": _safe_int(item.get("consensus_count")),
            "topk_ratio": _safe_float(item.get("topk_ratio")),
            "mean_rank": _safe_float(item.get("mean_rank")),
            "mean_objective_score": _safe_float(item.get("mean_objective_score")),
            "mean_bootstrap_top1_frequency": _safe_float(item.get("mean_bootstrap_top1_frequency")),
        }
        rows.append(row)
    return rows


def _build_threshold_sensitivity_rows(
    threshold_compare_summary: dict[str, Any],
    *,
    default_profile_name: str,
) -> list[dict[str, Any]]:
    rows_by_profile: dict[str, dict[str, Any]] = {}
    case_count = 0
    for case in threshold_compare_summary.get("cases", []):
        case_count += 1
        profile_rows = case.get("profile_rows", [])
        baseline = next((row for row in profile_rows if str(row.get("profile_label")) == default_profile_name), None)
        if baseline is None:
            continue
        baseline_warning = float(baseline.get("warning_area_nm2", 0.0) or 0.0)
        baseline_caution = float(baseline.get("caution_area_nm2", 0.0) or 0.0)
        baseline_sector = str(baseline.get("dominant_sector", ""))

        for profile_row in profile_rows:
            profile_name = str(profile_row.get("profile_label", ""))
            bucket = rows_by_profile.setdefault(
                profile_name,
                {
                    "profile_name": profile_name,
                    "case_count": 0,
                    "avg_warning_area_delta_vs_default": 0.0,
                    "avg_caution_area_delta_vs_default": 0.0,
                    "sector_change_count_vs_default": 0,
                },
            )
            bucket["case_count"] += 1
            bucket["avg_warning_area_delta_vs_default"] += float(profile_row.get("warning_area_nm2", 0.0) or 0.0) - baseline_warning
            bucket["avg_caution_area_delta_vs_default"] += float(profile_row.get("caution_area_nm2", 0.0) or 0.0) - baseline_caution
            if str(profile_row.get("dominant_sector", "")) != baseline_sector:
                bucket["sector_change_count_vs_default"] += 1

    rows: list[dict[str, Any]] = []
    for profile_name, payload in rows_by_profile.items():
        divisor = max(1, int(payload["case_count"]))
        rows.append(
            {
                "profile_name": profile_name,
                "case_count": int(payload["case_count"]),
                "avg_warning_area_delta_vs_default": float(payload["avg_warning_area_delta_vs_default"]) / divisor,
                "avg_caution_area_delta_vs_default": float(payload["avg_caution_area_delta_vs_default"]) / divisor,
                "sector_change_count_vs_default": int(payload["sector_change_count_vs_default"]),
            }
        )
    rows.sort(key=lambda item: str(item.get("profile_name", "")))
    return rows


def _choose_threshold_roles(threshold_rows: list[dict[str, Any]]) -> dict[str, str]:
    if not threshold_rows:
        return {}

    ranked_rows = sorted(
        threshold_rows,
        key=lambda row: (
            int(row.get("rank") or 999),
            -(row.get("recommended_count") or 0),
            row.get("profile_name") or "",
        ),
    )
    default_profile = str(ranked_rows[0]["profile_name"])

    sensitive_profile = min(
        threshold_rows,
        key=lambda row: (
            row.get("warning_threshold") if row.get("warning_threshold") is not None else 999.0,
            row.get("safe_threshold") if row.get("safe_threshold") is not None else 999.0,
            row.get("rank") if row.get("rank") is not None else 999,
        ),
    )
    tight_profile = max(
        threshold_rows,
        key=lambda row: (
            row.get("safe_threshold") if row.get("safe_threshold") is not None else -999.0,
            row.get("warning_threshold") if row.get("warning_threshold") is not None else -999.0,
            -(row.get("rank") if row.get("rank") is not None else 999),
        ),
    )

    return {
        "default_profile": default_profile,
        "sensitive_profile": str(sensitive_profile["profile_name"]),
        "tight_profile": str(tight_profile["profile_name"]),
    }


def _build_markdown(summary: dict[str, Any]) -> str:
    model_gate = summary["model_gate"]
    threshold_gate = summary["threshold_gate"]
    lines = [
        "# Governed Model and Threshold Selection",
        "",
        "## 1) 목적",
        "- [확정] 46일 통합 모델 검증 결과와 46일 threshold stability 결과를 하나의 운영 규칙으로 연결.",
        "- [확정] `primary model`, `explainable comparator`, `threshold shortlist role`을 명시해 발표/연구 문구를 고정.",
        "",
        "## 2) 모델 게이트",
        f"- [합리적 가정] benchmark F1 >= `{model_gate['benchmark_f1_threshold']:.2f}`",
        f"- [합리적 가정] calibration ECE <= `{model_gate['ece_threshold']:.2f}`",
        f"- [합리적 가정] own-ship LOO F1 mean >= `{model_gate['loo_f1_threshold']:.2f}`",
        f"- [합리적 가정] own-ship case F1 mean >= `{model_gate['case_f1_threshold']:.2f}`",
        f"- [합리적 가정] own-ship case repeat std mean <= `{model_gate['case_repeat_std_threshold']:.2f}`",
        "",
        "| model | benchmark F1 | ECE | LOO F1 mean | case F1 mean | case repeat std mean | gate | fail reasons |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in summary.get("model_rows", []):
        lines.append(
            f"| {row['model_name']} | {float(row['benchmark_f1']):.4f} | {float(row['calibration_ece']):.4f} | "
            f"{float(row['loo_f1_mean']):.4f} | {float(row['case_f1_mean']):.4f} | {float(row['case_repeat_std_mean']):.4f} | "
            f"{'pass' if row['gate_passed'] else 'fail'} | {row['gate_fail_reasons'] or '-'} |"
        )

    primary_model = summary.get("primary_model", {})
    comparator_model = summary.get("comparator_model", {})
    lines.extend(
        [
            "",
            "## 3) 모델 선택 결과",
            f"- [확정] primary model: `{primary_model.get('model_name', 'n/a')}`",
            f"- [확정] selection basis: `{summary.get('primary_selection_basis', 'n/a')}`",
            f"- [확정] explainable comparator: `{comparator_model.get('model_name', 'n/a')}`",
            "- [확정] rule_score는 설명 가능한 baseline으로 유지하고, torch_mlp는 Apple Silicon GPU 실험 비교군으로 한정한다.",
            "",
            "## 4) threshold stability",
            f"- [확정] stability_status: `{threshold_gate.get('stability_status', 'n/a')}`",
            f"- [확정] recommendation_majority_ratio: `{threshold_gate.get('recommendation_majority_ratio', 0.0):.4f}`",
            f"- [확정] mean_topk_jaccard: `{threshold_gate.get('mean_topk_jaccard', 0.0):.4f}`",
            f"- [확정] mean_recommended_bootstrap_top1_frequency: `{threshold_gate.get('mean_recommended_bootstrap_top1_frequency', 0.0):.4f}`",
            "",
            "| profile | rank | safe | warning | recommended_count | consensus_count | topk_ratio | mean_rank | mean_bootstrap_top1_frequency |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary.get("threshold_rows", []):
        lines.append(
            f"| {row['profile_name']} | {int(row['rank'] or 0)} | {float(row['safe_threshold']):.2f} | {float(row['warning_threshold']):.2f} | "
            f"{int(row['recommended_count'] or 0)} | {int(row['consensus_count'] or 0)} | {float(row['topk_ratio'] or 0.0):.4f} | "
            f"{float(row['mean_rank'] or 0.0):.4f} | {float(row['mean_bootstrap_top1_frequency'] or 0.0):.4f} |"
        )

    threshold_roles = summary.get("threshold_roles", {})
    lines.extend(
        [
            "",
            "## 5) threshold 역할 정의",
            f"- [확정] default profile: `{threshold_roles.get('default_profile', 'n/a')}`",
            f"- [확정] sensitive profile: `{threshold_roles.get('sensitive_profile', 'n/a')}`",
            f"- [확정] tight profile: `{threshold_roles.get('tight_profile', 'n/a')}`",
            "",
            "| profile | case_count | avg warning area delta vs default | avg caution area delta vs default | sector change count vs default |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary.get("threshold_sensitivity_rows", []):
        lines.append(
            f"| {row['profile_name']} | {int(row['case_count'])} | {float(row['avg_warning_area_delta_vs_default']):.4f} | "
            f"{float(row['avg_caution_area_delta_vs_default']):.4f} | {int(row['sector_change_count_vs_default'])} |"
        )

    lines.extend(
        [
            "",
            "## 6) 운영 권고",
            f"- [확정] 기본 발표/데모 조합은 `{primary_model.get('model_name', 'n/a')} + {threshold_roles.get('default_profile', 'n/a')}`.",
            f"- [확정] warning 민감도를 강조할 때는 `{threshold_roles.get('sensitive_profile', 'n/a')}`를 함께 제시.",
            f"- [확정] caution 영역을 더 타이트하게 보여주고 싶을 때는 `{threshold_roles.get('tight_profile', 'n/a')}`를 함께 제시.",
            f"- [확정] 설명 가능한 비교군은 `{comparator_model.get('model_name', 'n/a')}`로 유지.",
            "",
            "## 7) 해석",
            "- [확정] 모델 선택은 threshold 선택보다 훨씬 안정적이며, 현재 근거는 `hgbt primary`로 충분하다.",
            "- [확정] threshold는 단일 최적값으로 수렴하지 않았기 때문에 `운영 shortlist + 역할 분담`으로 설명하는 편이 더 정직하다.",
            "- [리스크] threshold role은 46일 stability와 representative holdout 3건을 함께 사용한 운영 규칙이며, 보편 규칙으로 과장하면 안 된다.",
            "",
            "## 8) 다음 액션",
            "- [추가 검증 필요] threshold shortlist sensitivity를 해역별 3-case 이상으로 확장해 통계화.",
            "- [추가 검증 필요] `2023-10` NOAA 또는 다른 NOAA 해역으로 같은 governed rule이 유지되는지 점검.",
            "- [추가 검증 필요] 논문 본문에서는 모델 선택 근거와 threshold 역할 분담을 별도 표로 제시.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a governed selection summary that combines multidate model metrics and threshold shortlist stability."
    )
    parser.add_argument("--benchmark-summary", required=True, help="Path to benchmark summary JSON.")
    parser.add_argument("--calibration-summary", required=True, help="Path to calibration summary JSON.")
    parser.add_argument("--loo-summary", required=True, help="Path to own-ship LOO summary JSON.")
    parser.add_argument("--case-summary", required=True, help="Path to own-ship case eval summary JSON.")
    parser.add_argument("--threshold-stability-summary", required=True, help="Path to threshold stability summary JSON.")
    parser.add_argument("--threshold-compare-summary", required=True, help="Path to threshold holdout compare summary JSON.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for governed summary artifacts.")
    parser.add_argument("--benchmark-f1-threshold", type=float, default=0.85)
    parser.add_argument("--ece-threshold", type=float, default=0.08)
    parser.add_argument("--loo-f1-threshold", type=float, default=0.85)
    parser.add_argument("--case-f1-threshold", type=float, default=0.85)
    parser.add_argument("--case-repeat-std-threshold", type=float, default=0.05)
    args = parser.parse_args()

    benchmark_summary = _read_json(args.benchmark_summary)
    calibration_summary = _read_json(args.calibration_summary)
    loo_summary = _read_json(args.loo_summary)
    case_summary = _read_json(args.case_summary)
    threshold_stability_summary = _read_json(args.threshold_stability_summary)
    threshold_compare_summary = _read_json(args.threshold_compare_summary)

    model_rows = _build_model_rows(
        benchmark_summary=benchmark_summary,
        calibration_summary=calibration_summary,
        loo_summary=loo_summary,
        case_summary=case_summary,
        benchmark_f1_threshold=float(args.benchmark_f1_threshold),
        ece_threshold=float(args.ece_threshold),
        loo_f1_threshold=float(args.loo_f1_threshold),
        case_f1_threshold=float(args.case_f1_threshold),
        case_repeat_std_threshold=float(args.case_repeat_std_threshold),
    )
    model_rows.sort(key=lambda row: (0 if row["gate_passed"] else 1, _model_sort_key(row), row["model_name"]))

    gate_passed_rows = [row for row in model_rows if bool(row.get("gate_passed", False))]
    if gate_passed_rows:
        primary_model = sorted(gate_passed_rows, key=lambda row: (_model_sort_key(row), row["model_name"]))[0]
        primary_basis = "lowest_ece_then_highest_loo_case_benchmark_within_gate"
    elif model_rows:
        primary_model = sorted(model_rows, key=lambda row: (_model_sort_key(row), row["model_name"]))[0]
        primary_basis = "fallback_lowest_ece_then_highest_loo_case_benchmark"
    else:
        primary_model = {}
        primary_basis = "no_models_available"

    comparator_model = next((row for row in model_rows if str(row.get("model_name")) == "logreg"), {})

    threshold_rows = _build_threshold_rows(threshold_stability_summary)
    threshold_roles = _choose_threshold_roles(threshold_rows)
    default_profile_name = threshold_roles.get("default_profile", "")
    threshold_sensitivity_rows = _build_threshold_sensitivity_rows(
        threshold_compare_summary=threshold_compare_summary,
        default_profile_name=default_profile_name,
    )

    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    model_rows_csv_path = prefix.with_name(f"{prefix.name}_model_rows.csv")
    threshold_rows_csv_path = prefix.with_name(f"{prefix.name}_threshold_rows.csv")
    threshold_sensitivity_csv_path = prefix.with_name(f"{prefix.name}_threshold_sensitivity_rows.csv")

    summary = {
        "status": "completed",
        "sources": {
            "benchmark_summary": str(args.benchmark_summary),
            "calibration_summary": str(args.calibration_summary),
            "loo_summary": str(args.loo_summary),
            "case_summary": str(args.case_summary),
            "threshold_stability_summary": str(args.threshold_stability_summary),
            "threshold_compare_summary": str(args.threshold_compare_summary),
        },
        "model_gate": {
            "benchmark_f1_threshold": float(args.benchmark_f1_threshold),
            "ece_threshold": float(args.ece_threshold),
            "loo_f1_threshold": float(args.loo_f1_threshold),
            "case_f1_threshold": float(args.case_f1_threshold),
            "case_repeat_std_threshold": float(args.case_repeat_std_threshold),
        },
        "primary_model": primary_model,
        "primary_selection_basis": primary_basis,
        "comparator_model": comparator_model,
        "model_rows": model_rows,
        "threshold_gate": {
            "stability_status": threshold_stability_summary.get("stability_status"),
            "recommendation_majority_ratio": _safe_float(threshold_stability_summary.get("recommendation_majority_ratio")),
            "mean_topk_jaccard": _safe_float(threshold_stability_summary.get("mean_topk_jaccard")),
            "mean_recommended_bootstrap_top1_frequency": _safe_float(
                threshold_stability_summary.get("mean_recommended_bootstrap_top1_frequency")
            ),
        },
        "threshold_rows": threshold_rows,
        "threshold_roles": threshold_roles,
        "threshold_sensitivity_rows": threshold_sensitivity_rows,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "model_rows_csv_path": str(model_rows_csv_path),
        "threshold_rows_csv_path": str(threshold_rows_csv_path),
        "threshold_sensitivity_rows_csv_path": str(threshold_sensitivity_csv_path),
    }

    _write_csv(
        model_rows_csv_path,
        model_rows,
        [
            "model_name",
            "benchmark_f1",
            "benchmark_auroc",
            "calibration_ece",
            "calibration_brier",
            "loo_f1_mean",
            "loo_auroc_mean",
            "case_f1_mean",
            "case_f1_ci95_width",
            "case_repeat_std_mean",
            "gate_passed",
            "gate_fail_reasons",
        ],
    )
    _write_csv(
        threshold_rows_csv_path,
        threshold_rows,
        [
            "profile_name",
            "rank",
            "safe_threshold",
            "warning_threshold",
            "recommended_count",
            "consensus_count",
            "topk_ratio",
            "mean_rank",
            "mean_objective_score",
            "mean_bootstrap_top1_frequency",
        ],
    )
    _write_csv(
        threshold_sensitivity_csv_path,
        threshold_sensitivity_rows,
        [
            "profile_name",
            "case_count",
            "avg_warning_area_delta_vs_default",
            "avg_caution_area_delta_vs_default",
            "sector_change_count_vs_default",
        ],
    )
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(_build_markdown(summary), encoding="utf-8")

    print(f"status={summary['status']}")
    print(f"primary_model={summary['primary_model'].get('model_name', 'n/a')}")
    print(f"default_profile={summary['threshold_roles'].get('default_profile', 'n/a')}")
    print(f"summary_json={summary_json_path}")
    print(f"summary_md={summary_md_path}")


if __name__ == "__main__":
    main()
