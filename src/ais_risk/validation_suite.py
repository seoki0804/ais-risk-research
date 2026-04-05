from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .benchmark import run_pairwise_benchmark
from .own_ship_cv import run_leave_one_own_ship_out_benchmark


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _select_best_model(models: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    best_name = None
    best_metrics = None
    best_f1 = -1.0
    for model_name, metrics in models.items():
        if metrics.get("status") == "skipped":
            continue
        f1 = metrics.get("f1")
        if f1 is None:
            continue
        f1_value = float(f1)
        if f1_value > best_f1:
            best_name = model_name
            best_metrics = metrics
            best_f1 = f1_value
    return best_name, best_metrics


def _benchmark_snapshot(summary: dict[str, Any]) -> dict[str, Any]:
    best_model_name, best_model_metrics = _select_best_model(summary.get("models", {}))
    return {
        "status": "completed",
        "summary_json_path": summary.get("summary_json_path"),
        "summary_md_path": summary.get("summary_md_path"),
        "predictions_csv_path": summary.get("predictions_csv_path"),
        "split_strategy": summary.get("split", {}).get("strategy"),
        "row_count": summary.get("row_count"),
        "positive_rate": summary.get("positive_rate"),
        "best_model": {
            "name": best_model_name,
            "f1": None if best_model_metrics is None else best_model_metrics.get("f1"),
            "auroc": None if best_model_metrics is None else best_model_metrics.get("auroc"),
            "auprc": None if best_model_metrics is None else best_model_metrics.get("auprc"),
        },
        "models": summary.get("models", {}),
    }


def _loo_snapshot(summary: dict[str, Any]) -> dict[str, Any]:
    aggregate_models = summary.get("aggregate_models", {})
    best_model_name = None
    best_model_payload = None
    best_f1 = -1.0
    for model_name, metrics in aggregate_models.items():
        f1_mean = metrics.get("f1_mean")
        if f1_mean is None:
            continue
        if float(f1_mean) > best_f1:
            best_f1 = float(f1_mean)
            best_model_name = model_name
            best_model_payload = metrics
    return {
        "status": "completed",
        "summary_json_path": summary.get("summary_json_path"),
        "summary_md_path": summary.get("summary_md_path"),
        "fold_metrics_csv_path": summary.get("fold_metrics_csv_path"),
        "evaluated_holdouts": summary.get("evaluated_holdouts"),
        "completed_fold_count": summary.get("completed_fold_count"),
        "best_model": {
            "name": best_model_name,
            "f1_mean": None if best_model_payload is None else best_model_payload.get("f1_mean"),
            "auroc_mean": None if best_model_payload is None else best_model_payload.get("auroc_mean"),
            "auprc_mean": None if best_model_payload is None else best_model_payload.get("auprc_mean"),
        },
        "aggregate_models": aggregate_models,
    }


def build_validation_suite_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Validation Suite Summary",
        "",
        "## Inputs",
        "",
        f"- input: `{summary['input_path']}`",
        f"- models: `{', '.join(summary['model_names'])}`",
        f"- torch device: `{summary['torch_device']}`",
        f"- random seed: `{summary.get('random_seed', 'n/a')}`",
        "",
        "## Strategy Overview",
        "",
    ]
    for key in ("timestamp_split", "own_ship_split", "own_ship_loo"):
        strategy = summary["strategies"].get(key, {})
        status = strategy.get("status", "unknown")
        lines.append(f"### {key}")
        lines.append("")
        lines.append(f"- status: `{status}`")
        if status != "completed":
            lines.append(f"- reason: `{strategy.get('error', strategy.get('reason', 'n/a'))}`")
            lines.append("")
            continue
        best = strategy.get("best_model", {})
        lines.append(f"- best model: `{best.get('name', 'n/a')}`")
        if key == "own_ship_loo":
            lines.append(f"- F1 mean: `{_fmt(best.get('f1_mean'))}`")
            lines.append(f"- AUROC mean: `{_fmt(best.get('auroc_mean'))}`")
            lines.append(f"- AUPRC mean: `{_fmt(best.get('auprc_mean'))}`")
            lines.append(f"- completed folds: `{strategy.get('completed_fold_count')}` / `{strategy.get('evaluated_holdouts')}`")
        else:
            lines.append(f"- F1: `{_fmt(best.get('f1'))}`")
            lines.append(f"- AUROC: `{_fmt(best.get('auroc'))}`")
            lines.append(f"- AUPRC: `{_fmt(best.get('auprc'))}`")
            lines.append(f"- split strategy: `{strategy.get('split_strategy')}`")
        lines.append("")
    return "\n".join(lines)


def run_validation_suite(
    input_path: str | Path,
    output_prefix: str | Path,
    model_names: list[str] | None = None,
    torch_device: str = "auto",
    own_ship_loo_holdout_mmsis: list[str] | None = None,
    own_ship_loo_val_fraction: float = 0.2,
    random_seed: int | None = 42,
) -> dict[str, Any]:
    requested_models = model_names or ["rule_score", "logreg", "hgbt"]
    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)

    strategies: dict[str, Any] = {}

    try:
        timestamp_summary = run_pairwise_benchmark(
            input_path=input_path,
            output_prefix=prefix.with_name(f"{prefix.name}_timestamp"),
            model_names=requested_models,
            split_strategy="timestamp",
            torch_device=torch_device,
            random_seed=None if random_seed is None else int(random_seed),
        )
        strategies["timestamp_split"] = _benchmark_snapshot(timestamp_summary)
    except Exception as exc:
        strategies["timestamp_split"] = {"status": "failed", "error": repr(exc)}

    try:
        own_ship_summary = run_pairwise_benchmark(
            input_path=input_path,
            output_prefix=prefix.with_name(f"{prefix.name}_own_ship"),
            model_names=requested_models,
            split_strategy="own_ship",
            torch_device=torch_device,
            random_seed=None if random_seed is None else int(random_seed) + 100,
        )
        strategies["own_ship_split"] = _benchmark_snapshot(own_ship_summary)
    except Exception as exc:
        strategies["own_ship_split"] = {"status": "failed", "error": repr(exc)}

    try:
        own_ship_loo_summary = run_leave_one_own_ship_out_benchmark(
            input_path=input_path,
            output_prefix=prefix.with_name(f"{prefix.name}_own_ship_loo"),
            model_names=requested_models,
            holdout_own_mmsis=own_ship_loo_holdout_mmsis,
            val_fraction=float(own_ship_loo_val_fraction),
            torch_device=torch_device,
            random_seed=None if random_seed is None else int(random_seed) + 200,
        )
        strategies["own_ship_loo"] = _loo_snapshot(own_ship_loo_summary)
    except Exception as exc:
        strategies["own_ship_loo"] = {"status": "failed", "error": repr(exc)}

    summary: dict[str, Any] = {
        "status": "completed",
        "input_path": str(input_path),
        "model_names": requested_models,
        "torch_device": torch_device,
        "random_seed": random_seed,
        "own_ship_loo_holdout_mmsis": own_ship_loo_holdout_mmsis or [],
        "own_ship_loo_val_fraction": float(own_ship_loo_val_fraction),
        "strategies": strategies,
    }

    summary_json_path = prefix.with_name(f"{prefix.name}_validation_suite_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_validation_suite_summary.md")
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_validation_suite_summary_markdown(summary), encoding="utf-8")
    summary["summary_json_path"] = str(summary_json_path)
    summary["summary_md_path"] = str(summary_md_path)
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
