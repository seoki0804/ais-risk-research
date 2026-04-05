from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from .study_journal import build_study_journal_from_summary
from .study_run import run_dataset_study_from_manifest


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


def parse_benchmark_modelsets(text: str) -> list[list[str]]:
    modelsets: list[list[str]] = []
    for chunk in str(text).split(";"):
        models = [item.strip() for item in chunk.split(",") if item.strip()]
        if models:
            modelsets.append(models)
    if not modelsets:
        raise ValueError("No valid modelset found. Use format: a,b,c;d,e,f")
    return modelsets


def _modelset_key(models: list[str]) -> str:
    return "+".join(models)


def _best_by_metric(
    models: dict[str, Any],
    metric_key: str,
    higher_is_better: bool,
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


def _read_optional_json(path_value: Any) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(str(path_value))
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _sum_elapsed_seconds(models: dict[str, Any]) -> float | None:
    total = 0.0
    seen = False
    for metrics in models.values():
        if not isinstance(metrics, dict):
            continue
        elapsed = _safe_float(metrics.get("elapsed_seconds"))
        if elapsed is None:
            continue
        total += float(elapsed)
        seen = True
    if not seen:
        return None
    return float(total)


def build_study_sweep_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Study Modelset Sweep Summary",
        "",
        "## Inputs",
        "",
        f"- manifest: `{summary['manifest_path']}`",
        f"- raw_input: `{summary['raw_input_path']}`",
        f"- ingestion_bundle: `{summary.get('ingestion_bundle_name', 'none') or 'none'}`",
        f"- ingestion_config: `{summary.get('ingestion_config_path', 'none') or 'none'}`",
        f"- source_preset: `{summary.get('source_preset_name', 'auto')}`",
        f"- column_map: `{summary.get('manual_column_map_text', 'auto') or 'auto'}`",
        f"- vessel_types: `{summary.get('vessel_types_text', 'none') or 'none'}`",
        f"- modelset_count: `{summary['modelset_count']}`",
        f"- pairwise_split_strategy: `{summary['pairwise_split_strategy']}`",
        f"- run_calibration_eval: `{summary['run_calibration_eval']}`",
        f"- run_own_ship_loo: `{summary['run_own_ship_loo']}`",
        f"- run_own_ship_case_eval: `{summary['run_own_ship_case_eval']}`",
        f"- own_ship_case_eval_mmsis: `{summary.get('own_ship_case_eval_mmsis', [])}`",
        f"- random_seed: `{summary.get('random_seed', 'n/a')}`",
        f"- build_study_journals: `{summary.get('build_study_journals', False)}`",
        f"- study_journal_output_template: `{summary.get('study_journal_output_template', 'n/a')}`",
        "",
        "## Results",
        "",
        "| # | Modelset | Status | Best Benchmark Model | Best Benchmark F1 | Benchmark Elapsed (sec) | Best Model Elapsed (sec) | Best Model Device | torch_mlp Elapsed (sec) | torch_mlp Device | Best Calibration Model | Best Calibration ECE | Best LOO Model | Best LOO F1 Mean | Best Case Model | Best Case F1 Mean | Best Case F1 Std | Best Case F1 CI95 Width | Best Case Repeat Std Mean | Study Summary | Study Journal |",
        "|---|---|---|---|---:|---:|---:|---|---:|---|---|---:|---|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for index, row in enumerate(summary.get("rows", []), start=1):
        lines.append(
            "| {idx} | `{modelset}` | {status} | {bench_model} | {bench_f1} | {bench_elapsed} | {best_elapsed} | {best_device} | {mlp_elapsed} | {mlp_device} | {cal_model} | {cal_ece} | {loo_model} | {loo_f1} | {case_model} | {case_f1} | {case_std} | {case_ci95_width} | {case_repeat_std_mean} | `{study}` | `{journal}` |".format(
                idx=index,
                modelset=row.get("modelset_key", "n/a"),
                status=row.get("status", "unknown"),
                bench_model=row.get("best_benchmark_model", "n/a"),
                bench_f1=_fmt(row.get("best_benchmark_f1")),
                bench_elapsed=_fmt(row.get("benchmark_elapsed_seconds")),
                best_elapsed=_fmt(row.get("best_benchmark_model_elapsed_seconds")),
                best_device=row.get("best_benchmark_model_device") or "n/a",
                mlp_elapsed=_fmt(row.get("torch_mlp_elapsed_seconds")),
                mlp_device=row.get("torch_mlp_device") or "n/a",
                cal_model=row.get("best_calibration_model", "n/a"),
                cal_ece=_fmt(row.get("best_calibration_ece")),
                loo_model=row.get("best_loo_model", "n/a"),
                loo_f1=_fmt(row.get("best_loo_f1_mean")),
                case_model=row.get("best_case_model", "n/a"),
                case_f1=_fmt(row.get("best_case_f1_mean")),
                case_std=_fmt(row.get("best_case_f1_std")),
                case_ci95_width=_fmt(row.get("best_case_f1_ci95_width")),
                case_repeat_std_mean=_fmt(row.get("best_case_f1_std_repeat_mean")),
                study=row.get("study_summary_json_path", "n/a"),
                journal=row.get("study_journal_path", "n/a"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def run_study_modelset_sweep(
    manifest_path: str | Path,
    raw_input_path: str | Path,
    output_prefix: str | Path,
    benchmark_modelsets: list[list[str]],
    config_path: str | Path = "configs/base.toml",
    ingestion_bundle_name: str | None = None,
    ingestion_config_path: str | Path | None = None,
    source_preset_name: str | None = "auto",
    manual_column_map_text: str | None = None,
    vessel_types_text: str | None = None,
    output_root: str | Path = "outputs",
    pairwise_split_strategy: str = "own_ship",
    run_calibration_eval: bool = True,
    run_own_ship_loo: bool = True,
    run_own_ship_case_eval: bool = True,
    own_ship_case_eval_mmsis: list[str] | None = None,
    own_ship_case_eval_min_rows: int = 30,
    own_ship_case_eval_repeat_count: int = 3,
    build_study_journals: bool = False,
    study_journal_output_template: str | None = None,
    study_journal_note: str | None = None,
    torch_device: str = "auto",
    random_seed: int | None = 42,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    base_output_root = Path(output_root)
    base_output_root.mkdir(parents=True, exist_ok=True)

    for index, modelset in enumerate(benchmark_modelsets, start=1):
        modelset_clean = [str(item).strip() for item in modelset if str(item).strip()]
        if not modelset_clean:
            continue
        modelset_key = _modelset_key(modelset_clean)
        modelset_output_root = base_output_root / f"sweep_{index:02d}_{modelset_key.replace('+', '_')}"
        try:
            study_summary = run_dataset_study_from_manifest(
                manifest_path=manifest_path,
                raw_input_path=raw_input_path,
                config_path=config_path,
                ingestion_bundle_name=ingestion_bundle_name,
                ingestion_config_path=ingestion_config_path,
                source_preset_name=source_preset_name,
                manual_column_map_text=manual_column_map_text,
                vessel_types_text=vessel_types_text,
                output_root=modelset_output_root,
                pairwise_split_strategy=pairwise_split_strategy,
                benchmark_models=modelset_clean,
                run_calibration_eval=bool(run_calibration_eval),
                run_own_ship_loo=bool(run_own_ship_loo),
                run_own_ship_case_eval=bool(run_own_ship_case_eval),
                own_ship_case_eval_mmsis=own_ship_case_eval_mmsis,
                own_ship_case_eval_min_rows=int(own_ship_case_eval_min_rows),
                own_ship_case_eval_repeat_count=max(1, int(own_ship_case_eval_repeat_count)),
                torch_device=torch_device,
                random_seed=random_seed,
            )
            benchmark_models = (study_summary.get("benchmark") or {}).get("models", {})
            best_benchmark_model, best_benchmark_f1 = _best_by_metric(benchmark_models, metric_key="f1", higher_is_better=True)
            benchmark_elapsed_seconds = _safe_float((study_summary.get("benchmark") or {}).get("benchmark_elapsed_seconds"))
            summed_model_elapsed_seconds = _sum_elapsed_seconds(benchmark_models)
            best_benchmark_model_elapsed_seconds = None
            best_benchmark_model_device = None
            if best_benchmark_model:
                best_metrics = benchmark_models.get(best_benchmark_model, {})
                if isinstance(best_metrics, dict):
                    best_benchmark_model_elapsed_seconds = _safe_float(best_metrics.get("elapsed_seconds"))
                    if best_metrics.get("device"):
                        best_benchmark_model_device = str(best_metrics.get("device"))
            torch_mlp_elapsed_seconds = None
            torch_mlp_device = None
            torch_mlp_metrics = benchmark_models.get("torch_mlp", {})
            if isinstance(torch_mlp_metrics, dict):
                torch_mlp_elapsed_seconds = _safe_float(torch_mlp_metrics.get("elapsed_seconds"))
                if torch_mlp_metrics.get("device"):
                    torch_mlp_device = str(torch_mlp_metrics.get("device"))

            calibration_summary = _read_optional_json(study_summary.get("calibration_eval_summary_json_path"))
            best_calibration_model, best_calibration_ece = _best_by_metric(
                calibration_summary.get("models", {}), metric_key="ece", higher_is_better=False
            )

            own_ship_loo_summary = _read_optional_json(study_summary.get("own_ship_loo_summary_json_path"))
            best_loo_model, best_loo_f1_mean = _best_by_metric(
                own_ship_loo_summary.get("aggregate_models", {}), metric_key="f1_mean", higher_is_better=True
            )

            own_ship_case_summary = _read_optional_json(study_summary.get("own_ship_case_eval_summary_json_path"))
            best_case_model, best_case_f1_mean = _best_by_metric(
                own_ship_case_summary.get("aggregate_models", {}), metric_key="f1_mean", higher_is_better=True
            )
            best_case_f1_std = None
            best_case_f1_ci95_width = None
            best_case_f1_std_repeat_mean = None
            if best_case_model:
                case_metrics = own_ship_case_summary.get("aggregate_models", {}).get(best_case_model, {})
                if isinstance(case_metrics, dict):
                    best_case_f1_std = _safe_float(case_metrics.get("f1_std"))
                    best_case_f1_ci95_width = _safe_float(case_metrics.get("f1_ci95_width"))
                    best_case_f1_std_repeat_mean = _safe_float(case_metrics.get("f1_std_repeat_mean"))

            study_journal_path = None
            study_journal_error = None
            if build_study_journals:
                dataset_id = str(study_summary.get("dataset_id") or f"dataset_{index:02d}")
                date_text = date.today().isoformat()
                output_template = study_journal_output_template or (
                    "research_logs/{date}_{dataset_id}_sweep_{modelset_index}_study_journal.md"
                )
                resolved_output = output_template.format(
                    date=date_text,
                    dataset_id=dataset_id,
                    modelset_index=f"{index:02d}",
                    modelset_key=modelset_key.replace("+", "_"),
                )
                topic = f"{dataset_id}_sweep_{index:02d}_{modelset_key}_iteration"
                try:
                    study_journal_path = build_study_journal_from_summary(
                        study_summary_path=study_summary.get("summary_json_path"),
                        output_path=resolved_output,
                        date_text=date_text,
                        topic=topic,
                        note=study_journal_note,
                    )
                except Exception as exc:
                    study_journal_error = repr(exc)

            rows.append(
                {
                    "modelset_index": index,
                    "modelset_key": modelset_key,
                    "modelset_models": modelset_clean,
                    "status": "completed",
                    "study_summary_json_path": study_summary.get("summary_json_path"),
                    "study_summary_md_path": study_summary.get("summary_md_path"),
                    "best_benchmark_model": best_benchmark_model,
                    "best_benchmark_f1": best_benchmark_f1,
                    "benchmark_elapsed_seconds": benchmark_elapsed_seconds,
                    "summed_model_elapsed_seconds": summed_model_elapsed_seconds,
                    "best_benchmark_model_elapsed_seconds": best_benchmark_model_elapsed_seconds,
                    "best_benchmark_model_device": best_benchmark_model_device,
                    "torch_mlp_elapsed_seconds": torch_mlp_elapsed_seconds,
                    "torch_mlp_device": torch_mlp_device,
                    "best_calibration_model": best_calibration_model,
                    "best_calibration_ece": best_calibration_ece,
                    "best_loo_model": best_loo_model,
                    "best_loo_f1_mean": best_loo_f1_mean,
                    "best_case_model": best_case_model,
                    "best_case_f1_mean": best_case_f1_mean,
                    "best_case_f1_std": best_case_f1_std,
                    "best_case_f1_ci95_width": best_case_f1_ci95_width,
                    "best_case_f1_std_repeat_mean": best_case_f1_std_repeat_mean,
                    "study_journal_path": study_journal_path,
                    "study_journal_error": study_journal_error,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "modelset_index": index,
                    "modelset_key": modelset_key,
                    "modelset_models": modelset_clean,
                    "status": "failed",
                    "error": repr(exc),
                }
            )

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    summary_csv_path = prefix.with_name(f"{prefix.name}_rows.csv")

    with summary_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "modelset_index",
            "modelset_key",
            "status",
            "study_summary_json_path",
            "best_benchmark_model",
            "best_benchmark_f1",
            "benchmark_elapsed_seconds",
            "summed_model_elapsed_seconds",
            "best_benchmark_model_elapsed_seconds",
            "best_benchmark_model_device",
            "torch_mlp_elapsed_seconds",
            "torch_mlp_device",
            "best_calibration_model",
            "best_calibration_ece",
            "best_loo_model",
            "best_loo_f1_mean",
            "best_case_model",
            "best_case_f1_mean",
            "best_case_f1_std",
            "best_case_f1_ci95_width",
            "best_case_f1_std_repeat_mean",
            "study_journal_path",
            "study_journal_error",
            "error",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})

    summary: dict[str, Any] = {
        "status": "completed",
        "manifest_path": str(manifest_path),
        "raw_input_path": str(raw_input_path),
        "config_path": str(config_path),
        "ingestion_bundle_name": ingestion_bundle_name or "",
        "ingestion_config_path": str(ingestion_config_path) if ingestion_config_path else "",
        "source_preset_name": source_preset_name or "auto",
        "manual_column_map_text": manual_column_map_text or "",
        "vessel_types_text": vessel_types_text or "",
        "output_root": str(base_output_root),
        "pairwise_split_strategy": pairwise_split_strategy,
        "run_calibration_eval": bool(run_calibration_eval),
        "run_own_ship_loo": bool(run_own_ship_loo),
        "run_own_ship_case_eval": bool(run_own_ship_case_eval),
        "own_ship_case_eval_mmsis": own_ship_case_eval_mmsis or [],
        "random_seed": random_seed,
        "build_study_journals": bool(build_study_journals),
        "study_journal_output_template": study_journal_output_template or "",
        "study_journal_note": study_journal_note or "",
        "modelset_count": len(benchmark_modelsets),
        "rows": rows,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "summary_csv_path": str(summary_csv_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_study_sweep_summary_markdown(summary), encoding="utf-8")
    return summary
