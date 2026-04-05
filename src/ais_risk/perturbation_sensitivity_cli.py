from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .benchmark import run_pairwise_benchmark
from .calibration_eval import run_calibration_evaluation
from .pairwise_perturbation import run_pairwise_perturbation
from .prediction_grid_projection import run_prediction_grid_projection


def _read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_rows(path: str | Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _build_raw_band_rows(prediction_rows: list[dict[str, str]], model_name: str) -> list[dict[str, str]]:
    score_key = f"{model_name}_score"
    pred_key = f"{model_name}_pred"
    rows: list[dict[str, str]] = []
    for row in prediction_rows:
        if score_key not in row:
            continue
        raw_score = float(row[score_key])
        rows.append(
            {
                "timestamp": row.get("timestamp", ""),
                "own_mmsi": row.get("own_mmsi", ""),
                "target_mmsi": row.get("target_mmsi", ""),
                "label_future_conflict": row.get("label_future_conflict", ""),
                "model": model_name,
                "raw_score": f"{raw_score:.6f}",
                "raw_pred": row.get(pred_key, ""),
                "score_lower": f"{raw_score:.6f}",
                "score_mean": f"{raw_score:.6f}",
                "score_upper": f"{raw_score:.6f}",
                "band_width": "0.000000",
            }
        )
    return rows


def _top_case_id(case_summary_rows: list[dict[str, str]], rank_key: str = "max_risk_mean") -> str | None:
    if not case_summary_rows:
        return None
    ordered = sorted(case_summary_rows, key=lambda row: float(row.get(rank_key) or 0.0), reverse=True)
    return str(ordered[0].get("case_id") or "") or None


def _lookup_case(case_summary_rows: list[dict[str, str]], case_id: str | None) -> dict[str, str] | None:
    if not case_id:
        return None
    for row in case_summary_rows:
        if str(row.get("case_id")) == str(case_id):
            return row
    return None


def _join_score_drift(
    baseline_rows: list[dict[str, str]],
    perturbed_rows: list[dict[str, str]],
    model_name: str,
) -> dict[str, Any]:
    score_key = f"{model_name}_score"
    baseline_lookup = {
        (str(row.get("timestamp", "")), str(row.get("own_mmsi", "")), str(row.get("target_mmsi", ""))): row
        for row in baseline_rows
        if score_key in row
    }
    score_deltas: list[float] = []
    pred_flips = 0
    matched_rows = 0
    for row in perturbed_rows:
        key = (str(row.get("timestamp", "")), str(row.get("own_mmsi", "")), str(row.get("target_mmsi", "")))
        base_row = baseline_lookup.get(key)
        if base_row is None or score_key not in base_row or score_key not in row:
            continue
        matched_rows += 1
        baseline_score = float(base_row[score_key])
        perturbed_score = float(row[score_key])
        score_deltas.append(abs(perturbed_score - baseline_score))
        baseline_pred = str(base_row.get(f"{model_name}_pred", ""))
        perturbed_pred = str(row.get(f"{model_name}_pred", ""))
        if baseline_pred != perturbed_pred:
            pred_flips += 1
    return {
        "matched_rows": matched_rows,
        "mean_abs_score_drift": (sum(score_deltas) / len(score_deltas)) if score_deltas else 0.0,
        "max_abs_score_drift": max(score_deltas) if score_deltas else 0.0,
        "prediction_flip_count": pred_flips,
        "prediction_flip_rate": (pred_flips / matched_rows) if matched_rows else 0.0,
    }


def _case_metric(row: dict[str, str] | None, key: str) -> float | None:
    if row is None:
        return None
    value = row.get(key)
    if value is None or value == "":
        return None
    return float(value)


def build_perturbation_sensitivity_summary_markdown(summary: dict[str, Any]) -> str:
    baseline = summary["baseline"]
    perturbed = summary["perturbed"]
    drift = summary["score_drift"]
    lines = [
        "# AIS Perturbation Sensitivity Summary",
        "",
        "## Inputs",
        "",
        f"- baseline_pairwise_csv: `{summary['baseline_pairwise_csv_path']}`",
        f"- baseline_predictions_csv: `{summary['baseline_predictions_csv_path']}`",
        f"- config_path: `{summary['config_path']}`",
        f"- model: `{summary['model_name']}`",
        f"- split_strategy: `{summary['split_strategy']}`",
        f"- profile_name: `{summary['profile_name']}`",
        "",
        "## Perturbation",
        "",
        f"- position_jitter_m: `{summary['position_jitter_m']:.2f}`",
        f"- speed_jitter_frac: `{summary['speed_jitter_frac']:.4f}`",
        f"- course_jitter_deg: `{summary['course_jitter_deg']:.2f}`",
        f"- drop_rate: `{summary['drop_rate']:.4f}`",
        "",
        "## Benchmark Drift",
        "",
        f"- baseline_f1: `{baseline['f1']:.4f}`",
        f"- perturbed_f1: `{perturbed['f1']:.4f}`",
        f"- delta_f1: `{summary['delta_f1']:.4f}`",
        f"- baseline_ece: `{baseline['ece']:.4f}`",
        f"- perturbed_ece: `{perturbed['ece']:.4f}`",
        f"- delta_ece: `{summary['delta_ece']:.4f}`",
        "",
        "## Score Drift",
        "",
        f"- matched_rows: `{drift['matched_rows']}`",
        f"- mean_abs_score_drift: `{drift['mean_abs_score_drift']:.4f}`",
        f"- max_abs_score_drift: `{drift['max_abs_score_drift']:.4f}`",
        f"- prediction_flip_rate: `{drift['prediction_flip_rate']:.4f}`",
        "",
        "## Representative Case Drift",
        "",
        f"- baseline_top_case_id: `{summary['baseline_top_case_id']}`",
        f"- perturbed_top_case_id: `{summary['perturbed_top_case_id']}`",
        f"- top_case_preserved: `{summary['top_case_preserved']}`",
        f"- baseline_case_present_under_perturbation: `{summary['baseline_case_present_under_perturbation']}`",
        f"- delta_case_max_risk_mean: `{summary['delta_case_max_risk_mean']}`",
        f"- delta_case_warning_area_mean_nm2: `{summary['delta_case_warning_area_mean_nm2']}`",
        f"- delta_case_caution_area_mean_nm2: `{summary['delta_case_caution_area_mean_nm2']}`",
        "",
        "## Outputs",
        "",
        f"- perturbation_summary_json: `{summary['perturbation_summary_json_path']}`",
        f"- perturbed_pairwise_csv: `{summary['perturbed_pairwise_csv_path']}`",
        f"- perturbed_benchmark_summary_json: `{summary['perturbed_benchmark_summary_json_path']}`",
        f"- perturbed_predictions_csv: `{summary['perturbed_predictions_csv_path']}`",
        f"- perturbed_projection_summary_json: `{summary['perturbed_projection_summary_json_path']}`",
        f"- summary_json: `{summary['summary_json_path']}`",
        f"- summary_md: `{summary['summary_md_path']}`",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run pairwise AIS perturbation, benchmark re-evaluation, and representative raw-contour drift summary."
    )
    parser.add_argument("--baseline-pairwise", required=True, help="Baseline pairwise CSV path.")
    parser.add_argument("--baseline-predictions", required=True, help="Baseline benchmark predictions CSV path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for perturbation sensitivity outputs.")
    parser.add_argument("--config", default="configs/base.toml", help="Project TOML config path.")
    parser.add_argument("--model", default="hgbt", help="Model name to track for contour and score drift.")
    parser.add_argument("--profile-name", default="custom", help="Short perturbation profile label.")
    parser.add_argument("--position-jitter-m", type=float, default=0.0, help="Gaussian local position jitter in meters.")
    parser.add_argument("--speed-jitter-frac", type=float, default=0.0, help="Gaussian relative-speed jitter as a fractional std.")
    parser.add_argument("--course-jitter-deg", type=float, default=0.0, help="Gaussian course-difference jitter in degrees.")
    parser.add_argument("--drop-rate", type=float, default=0.0, help="Random row drop rate in [0, 1).")
    parser.add_argument("--split-strategy", default="own_ship", choices=["timestamp", "own_ship"], help="Benchmark split strategy.")
    parser.add_argument("--train-fraction", type=float, default=0.6, help="Train fraction for benchmark rerun.")
    parser.add_argument("--val-fraction", type=float, default=0.2, help="Validation fraction for benchmark rerun.")
    parser.add_argument("--random-seed", type=int, default=42, help="Random seed for perturbation and benchmark rerun.")
    args = parser.parse_args()

    output_root = Path(str(args.output_prefix))
    output_root.parent.mkdir(parents=True, exist_ok=True)

    baseline_prediction_rows = _read_csv_rows(args.baseline_predictions)
    baseline_band_rows = _build_raw_band_rows(baseline_prediction_rows, model_name=args.model)
    if not baseline_band_rows:
        raise ValueError(f"No `{args.model}` rows found in baseline predictions CSV.")
    baseline_band_csv_path = output_root.with_name(f"{output_root.name}_baseline_raw_bands.csv")
    _write_rows(
        baseline_band_csv_path,
        [
            "timestamp",
            "own_mmsi",
            "target_mmsi",
            "label_future_conflict",
            "model",
            "raw_score",
            "raw_pred",
            "score_lower",
            "score_mean",
            "score_upper",
            "band_width",
        ],
        baseline_band_rows,
    )

    baseline_projection_summary = run_prediction_grid_projection(
        pairwise_csv_path=args.baseline_pairwise,
        sample_bands_csv_path=baseline_band_csv_path,
        output_prefix=output_root.with_name(f"{output_root.name}_baseline_projection"),
        config_path=args.config,
        model_names=[args.model],
        case_limit=1,
        case_rank_metric="max_risk_mean",
    )
    baseline_case_rows = _read_csv_rows(baseline_projection_summary["case_summary_csv_path"])
    baseline_top_case_id = _top_case_id(baseline_case_rows)
    baseline_case_row = _lookup_case(baseline_case_rows, baseline_top_case_id)

    baseline_calibration_summary = run_calibration_evaluation(
        predictions_csv_path=args.baseline_predictions,
        output_prefix=output_root.with_name(f"{output_root.name}_baseline_calibration"),
        model_names=[args.model],
        num_bins=10,
    )

    perturbation_summary = run_pairwise_perturbation(
        input_csv_path=args.baseline_pairwise,
        output_prefix=output_root.with_name(f"{output_root.name}_perturbation"),
        config_path=args.config,
        profile_name=args.profile_name,
        position_jitter_m=float(args.position_jitter_m),
        speed_jitter_frac=float(args.speed_jitter_frac),
        course_jitter_deg=float(args.course_jitter_deg),
        drop_rate=float(args.drop_rate),
        random_seed=int(args.random_seed),
    )

    perturbed_benchmark_summary = run_pairwise_benchmark(
        input_path=perturbation_summary["perturbed_csv_path"],
        output_prefix=output_root.with_name(f"{output_root.name}_perturbed_benchmark"),
        model_names=[args.model],
        train_fraction=float(args.train_fraction),
        val_fraction=float(args.val_fraction),
        split_strategy=args.split_strategy,
        random_seed=int(args.random_seed),
    )
    perturbed_predictions_csv_path = perturbed_benchmark_summary["predictions_csv_path"]
    perturbed_prediction_rows = _read_csv_rows(perturbed_predictions_csv_path)
    perturbed_band_rows = _build_raw_band_rows(perturbed_prediction_rows, model_name=args.model)
    perturbed_band_csv_path = output_root.with_name(f"{output_root.name}_perturbed_raw_bands.csv")
    _write_rows(
        perturbed_band_csv_path,
        [
            "timestamp",
            "own_mmsi",
            "target_mmsi",
            "label_future_conflict",
            "model",
            "raw_score",
            "raw_pred",
            "score_lower",
            "score_mean",
            "score_upper",
            "band_width",
        ],
        perturbed_band_rows,
    )

    perturbed_projection_summary = run_prediction_grid_projection(
        pairwise_csv_path=perturbation_summary["perturbed_csv_path"],
        sample_bands_csv_path=perturbed_band_csv_path,
        output_prefix=output_root.with_name(f"{output_root.name}_perturbed_projection"),
        config_path=args.config,
        model_names=[args.model],
        selected_case_ids=[baseline_top_case_id] if baseline_top_case_id else None,
        case_limit=1,
        case_rank_metric="max_risk_mean",
    )
    perturbed_case_rows = _read_csv_rows(perturbed_projection_summary["case_summary_csv_path"])
    perturbed_top_case_id = _top_case_id(perturbed_case_rows)
    perturbed_same_case_row = _lookup_case(perturbed_case_rows, baseline_top_case_id)

    perturbed_calibration_summary = run_calibration_evaluation(
        predictions_csv_path=perturbed_predictions_csv_path,
        output_prefix=output_root.with_name(f"{output_root.name}_perturbed_calibration"),
        model_names=[args.model],
        num_bins=10,
    )

    score_drift = _join_score_drift(
        baseline_rows=baseline_prediction_rows,
        perturbed_rows=perturbed_prediction_rows,
        model_name=args.model,
    )

    baseline_metrics = baseline_calibration_summary["models"][args.model]
    baseline_benchmark_metrics = {
        "f1": float(0.0 if baseline_metrics.get("status") == "skipped" else 0.0),
        "ece": float(baseline_metrics.get("ece", 0.0)),
    }
    baseline_summary_path = str(args.baseline_predictions).replace("_test_predictions.csv", "_summary.json")
    baseline_benchmark_summary_json = Path(baseline_summary_path)
    if baseline_benchmark_summary_json.exists():
        baseline_summary = json.loads(baseline_benchmark_summary_json.read_text(encoding="utf-8"))
        baseline_model_metrics = baseline_summary.get("models", {}).get(args.model, {})
        baseline_benchmark_metrics["f1"] = float(baseline_model_metrics.get("f1", 0.0) or 0.0)

    perturbed_model_metrics = perturbed_benchmark_summary["models"][args.model]
    perturbed_benchmark_metrics = {
        "f1": float(perturbed_model_metrics.get("f1", 0.0) or 0.0),
        "ece": float(perturbed_calibration_summary["models"][args.model].get("ece", 0.0) or 0.0),
    }

    summary = {
        "status": "completed",
        "baseline_pairwise_csv_path": str(args.baseline_pairwise),
        "baseline_predictions_csv_path": str(args.baseline_predictions),
        "config_path": str(args.config),
        "model_name": str(args.model),
        "profile_name": str(args.profile_name),
        "split_strategy": str(args.split_strategy),
        "position_jitter_m": float(args.position_jitter_m),
        "speed_jitter_frac": float(args.speed_jitter_frac),
        "course_jitter_deg": float(args.course_jitter_deg),
        "drop_rate": float(args.drop_rate),
        "baseline": baseline_benchmark_metrics,
        "perturbed": perturbed_benchmark_metrics,
        "delta_f1": perturbed_benchmark_metrics["f1"] - baseline_benchmark_metrics["f1"],
        "delta_ece": perturbed_benchmark_metrics["ece"] - baseline_benchmark_metrics["ece"],
        "score_drift": score_drift,
        "baseline_top_case_id": baseline_top_case_id,
        "perturbed_top_case_id": perturbed_top_case_id,
        "top_case_preserved": bool(baseline_top_case_id and baseline_top_case_id == perturbed_top_case_id),
        "baseline_case_present_under_perturbation": perturbed_same_case_row is not None,
        "delta_case_max_risk_mean": (
            None
            if baseline_case_row is None or perturbed_same_case_row is None
            else _case_metric(perturbed_same_case_row, "max_risk_mean") - _case_metric(baseline_case_row, "max_risk_mean")
        ),
        "delta_case_warning_area_mean_nm2": (
            None
            if baseline_case_row is None or perturbed_same_case_row is None
            else _case_metric(perturbed_same_case_row, "warning_area_mean_nm2")
            - _case_metric(baseline_case_row, "warning_area_mean_nm2")
        ),
        "delta_case_caution_area_mean_nm2": (
            None
            if baseline_case_row is None or perturbed_same_case_row is None
            else _case_metric(perturbed_same_case_row, "caution_area_mean_nm2")
            - _case_metric(baseline_case_row, "caution_area_mean_nm2")
        ),
        "perturbation_summary_json_path": str(perturbation_summary["summary_json_path"]),
        "perturbed_pairwise_csv_path": str(perturbation_summary["perturbed_csv_path"]),
        "perturbed_benchmark_summary_json_path": str(perturbed_benchmark_summary["summary_json_path"]),
        "perturbed_predictions_csv_path": str(perturbed_predictions_csv_path),
        "perturbed_projection_summary_json_path": str(perturbed_projection_summary["summary_json_path"]),
    }

    summary_json_path = output_root.with_name(f"{output_root.name}_summary.json")
    summary_md_path = output_root.with_name(f"{output_root.name}_summary.md")
    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_md_path"] = str(summary_md_path)

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_perturbation_sensitivity_summary_markdown(summary), encoding="utf-8")

    print("status=completed")
    print(f"summary_json={summary_json_path}")
    print(f"summary_md={summary_md_path}")
    print(f"perturbed_predictions_csv={perturbed_predictions_csv_path}")
    print(f"perturbed_projection_summary_json={perturbed_projection_summary['summary_json_path']}")


if __name__ == "__main__":
    main()
