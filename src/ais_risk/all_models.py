from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from . import benchmark as benchmark_module
from .benchmark import run_pairwise_benchmark
from .calibration_eval import run_calibration_evaluation
from .regional_raster_cnn import run_regional_raster_cnn_benchmark


ALL_TABULAR_MODEL_NAMES = ["rule_score", "logreg", "hgbt", "torch_mlp"]
CNN_LOSS_TO_MODEL_NAME = {"weighted_bce": "cnn_weighted", "focal": "cnn_focal"}

LEADERBOARD_FIELDS = [
    "dataset",
    "model_family",
    "model_name",
    "status",
    "f1",
    "precision",
    "recall",
    "auroc",
    "auprc",
    "accuracy",
    "threshold",
    "sample_count",
    "positive_count",
    "negative_count",
    "tp",
    "fp",
    "tn",
    "fn",
    "ece",
    "brier_score",
    "elapsed_seconds",
    "device",
    "epochs",
    "hidden_dim",
    "split_strategy",
    "summary_json_path",
    "predictions_csv_path",
    "notes",
]


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


def _status_sort_key(status: str) -> int:
    if status == "completed":
        return 0
    if status == "skipped":
        return 1
    return 2


def _row_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    f1 = _safe_float(row.get("f1"))
    return (
        str(row.get("dataset") or ""),
        _status_sort_key(str(row.get("status") or "")),
        -(f1 if f1 is not None else -1.0),
        str(row.get("model_name") or ""),
    )


def _resolve_cnn_losses(cnn_losses: list[str] | None) -> list[str]:
    if cnn_losses is None:
        return ["weighted_bce", "focal"]
    resolved: list[str] = []
    for item in cnn_losses:
        normalized = str(item).strip()
        if not normalized:
            continue
        if normalized not in ("weighted_bce", "focal"):
            raise ValueError(f"Unsupported cnn loss type: {normalized}")
        if normalized not in resolved:
            resolved.append(normalized)
    return resolved or ["weighted_bce", "focal"]


def _safe_int(value: Any) -> int | None:
    try:
        return int(str(value))
    except Exception:
        return None


def _compute_prediction_confusions(predictions_csv_path: str | Path, prediction_model_names: list[str]) -> dict[str, dict[str, int]]:
    rows = list(csv.DictReader(Path(predictions_csv_path).open("r", encoding="utf-8", newline="")))
    if not rows:
        return {}
    output: dict[str, dict[str, int]] = {}
    for model_name in prediction_model_names:
        pred_key = f"{model_name}_pred"
        if pred_key not in rows[0]:
            continue
        tp = fp = tn = fn = 0
        for row in rows:
            label = _safe_int(row.get("label_future_conflict"))
            pred = _safe_int(row.get(pred_key))
            if label not in (0, 1) or pred not in (0, 1):
                continue
            if label == 1 and pred == 1:
                tp += 1
            elif label == 0 and pred == 1:
                fp += 1
            elif label == 0 and pred == 0:
                tn += 1
            else:
                fn += 1
        output[model_name] = {
            "sample_count": tp + fp + tn + fn,
            "positive_count": tp + fn,
            "negative_count": tn + fp,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
        }
    return output


def _merge_notes(notes: str, extra_note: str) -> str:
    base = str(notes or "").strip()
    suffix = str(extra_note or "").strip()
    if not suffix:
        return base
    if not base:
        return suffix
    return f"{base}; {suffix}"


def _probe_split_support(
    rows: list[dict[str, str]],
    split_strategy: str,
    train_fraction: float,
    val_fraction: float,
) -> dict[str, Any]:
    _, _, test_rows, split_summary = benchmark_module._partition_rows_for_benchmark(  # noqa: SLF001
        rows=rows,
        split_strategy=split_strategy,
        train_fraction=float(train_fraction),
        val_fraction=float(val_fraction),
    )
    positive_count = int(sum(int(row["label_future_conflict"]) for row in test_rows))
    return {
        "split_strategy": split_strategy,
        "train_fraction": float(train_fraction),
        "val_fraction": float(val_fraction),
        "test_rows": len(test_rows),
        "positive_count": positive_count,
        "negative_count": int(len(test_rows) - positive_count),
        "test_own_ships": split_summary.get("test_own_ships"),
    }


def _choose_support_aware_split(
    rows: list[dict[str, str]],
    split_strategy: str,
    train_fraction: float,
    val_fraction: float,
    min_positive_support: int,
) -> tuple[float, float, list[dict[str, Any]], bool]:
    requested = (float(train_fraction), float(val_fraction))
    candidate_pairs: list[tuple[float, float]] = [requested]
    candidate_pairs.extend(
        [
            (0.5, 0.2),
            (0.4, 0.2),
            (0.5, 0.1),
            (0.4, 0.1),
            (0.7, 0.15),
            (0.6, 0.15),
        ]
    )
    dedup_pairs: list[tuple[float, float]] = []
    for pair in candidate_pairs:
        if pair not in dedup_pairs:
            dedup_pairs.append(pair)

    probes: list[dict[str, Any]] = []
    requested_probe: dict[str, Any] | None = None
    chosen_probe: dict[str, Any] | None = None
    for tf, vf in dedup_pairs:
        probe = _probe_split_support(rows=rows, split_strategy=split_strategy, train_fraction=tf, val_fraction=vf)
        probes.append(probe)
        if tf == requested[0] and vf == requested[1]:
            requested_probe = probe
        if chosen_probe is not None:
            continue
        if int(probe["positive_count"]) < int(min_positive_support):
            continue
        if split_strategy == "own_ship":
            test_own_ships = _safe_int(probe.get("test_own_ships"))
            if test_own_ships is not None and int(test_own_ships) < 2:
                continue
        chosen_probe = probe

    if chosen_probe is None:
        chosen_probe = requested_probe or probes[0]
    changed = not (
        float(chosen_probe["train_fraction"]) == requested[0]
        and float(chosen_probe["val_fraction"]) == requested[1]
    )
    return float(chosen_probe["train_fraction"]), float(chosen_probe["val_fraction"]), probes, changed


def _write_leaderboard_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEADERBOARD_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in LEADERBOARD_FIELDS})


def _build_leaderboard_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# All Supported Models Leaderboard",
        "",
        "## Inputs",
        "",
        f"- input_csv: `{summary['input_csv_path']}`",
        f"- output_dir: `{summary['output_dir']}`",
        f"- split_strategy: `{summary['split_strategy']}`",
        f"- requested_train_fraction: `{summary['requested_train_fraction']}`",
        f"- requested_val_fraction: `{summary['requested_val_fraction']}`",
        f"- effective_train_fraction: `{summary['effective_train_fraction']}`",
        f"- effective_val_fraction: `{summary['effective_val_fraction']}`",
        f"- auto_adjust_split_for_support: `{summary['auto_adjust_split_for_support']}`",
        f"- split_was_auto_adjusted: `{summary['split_was_auto_adjusted']}`",
        f"- tabular_models_requested: `{', '.join(summary['tabular_models_requested'])}`",
        f"- regional_cnn_enabled: `{summary['include_regional_cnn']}`",
        f"- regional_cnn_losses: `{', '.join(summary['cnn_losses']) if summary['cnn_losses'] else 'none'}`",
        f"- min_positive_support: `{summary['min_positive_support']}`",
        "",
        "## Model Comparison",
        "",
        "| Rank | Dataset | Model | Family | Status | Positives | F1 | AUROC | AUPRC | Precision | Recall | ECE | Brier | Threshold | Elapsed(s) | Notes |",
        "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rank, row in enumerate(rows, start=1):
        lines.append(
            "| {rank} | {dataset} | {model} | {family} | {status} | {positives} | {f1} | {auroc} | {auprc} | {precision} | {recall} | {ece} | {brier} | {threshold} | {elapsed} | {notes} |".format(
                rank=rank,
                dataset=row.get("dataset", ""),
                model=row.get("model_name", ""),
                family=row.get("model_family", ""),
                status=row.get("status", ""),
                positives=row.get("positive_count", "n/a"),
                f1=_fmt(row.get("f1")),
                auroc=_fmt(row.get("auroc")),
                auprc=_fmt(row.get("auprc")),
                precision=_fmt(row.get("precision")),
                recall=_fmt(row.get("recall")),
                ece=_fmt(row.get("ece")),
                brier=_fmt(row.get("brier_score")),
                threshold=_fmt(row.get("threshold")),
                elapsed=_fmt(row.get("elapsed_seconds"), digits=2),
                notes=(str(row.get("notes") or "").replace("|", "/")),
            )
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- leaderboard_csv: `{summary['leaderboard_csv_path']}`",
            f"- leaderboard_md: `{summary['leaderboard_md_path']}`",
            f"- summary_json: `{summary['summary_json_path']}`",
            f"- summary_md: `{summary['summary_md_path']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _build_summary_markdown(summary: dict[str, Any]) -> str:
    top_model = summary.get("top_model") or {}
    lines = [
        "# All Supported Models Run Summary",
        "",
        "## Inputs",
        "",
        f"- input_csv: `{summary['input_csv_path']}`",
        f"- output_dir: `{summary['output_dir']}`",
        f"- split_strategy: `{summary['split_strategy']}`",
        f"- requested_train_fraction: `{summary['requested_train_fraction']}`",
        f"- requested_val_fraction: `{summary['requested_val_fraction']}`",
        f"- effective_train_fraction: `{summary['effective_train_fraction']}`",
        f"- effective_val_fraction: `{summary['effective_val_fraction']}`",
        f"- auto_adjust_split_for_support: `{summary['auto_adjust_split_for_support']}`",
        f"- split_was_auto_adjusted: `{summary['split_was_auto_adjusted']}`",
        f"- torch_device: `{summary['torch_device']}`",
        f"- random_seed: `{summary['random_seed']}`",
        "",
        "## Coverage",
        "",
        f"- tabular_models_requested: `{', '.join(summary['tabular_models_requested'])}`",
        f"- tabular_models_executed: `{', '.join(summary['tabular_models_executed'])}`",
        f"- include_regional_cnn: `{summary['include_regional_cnn']}`",
        f"- regional_cnn_losses: `{', '.join(summary['cnn_losses']) if summary['cnn_losses'] else 'none'}`",
        f"- min_positive_support: `{summary['min_positive_support']}`",
        f"- low_support_warning_count: `{len(summary.get('low_support_warnings', []))}`",
        f"- leaderboard_row_count: `{summary['row_count']}`",
        "",
        "## Best Completed Model",
        "",
        f"- dataset: `{top_model.get('dataset', 'n/a')}`",
        f"- model: `{top_model.get('model_name', 'n/a')}`",
        f"- family: `{top_model.get('model_family', 'n/a')}`",
        f"- f1: `{_fmt(top_model.get('f1'))}`",
        f"- auroc: `{_fmt(top_model.get('auroc'))}`",
        f"- ece: `{_fmt(top_model.get('ece'))}`",
        "",
        "## Key Outputs",
        "",
        f"- tabular_benchmark_summary_json: `{summary.get('tabular_benchmark_summary_json_path', 'n/a')}`",
        f"- tabular_calibration_summary_json: `{summary.get('tabular_calibration_summary_json_path', 'n/a')}`",
        f"- leaderboard_csv: `{summary['leaderboard_csv_path']}`",
        f"- leaderboard_md: `{summary['leaderboard_md_path']}`",
        f"- summary_json: `{summary['summary_json_path']}`",
        f"- summary_md: `{summary['summary_md_path']}`",
        "",
    ]
    return "\n".join(lines)


def run_all_supported_models(
    input_path: str | Path,
    output_dir: str | Path,
    split_strategy: str = "own_ship",
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    torch_device: str = "auto",
    random_seed: int | None = 42,
    include_regional_cnn: bool = False,
    cnn_losses: list[str] | None = None,
    cnn_half_width_nm: float = 3.0,
    cnn_raster_size: int = 64,
    cnn_epochs: int = 20,
    cnn_batch_size: int = 64,
    cnn_learning_rate: float = 1e-3,
    cnn_focal_gamma: float = 2.0,
    cnn_balance_batches: bool = True,
    cnn_max_train_rows: int | None = None,
    cnn_max_val_rows: int | None = None,
    cnn_max_test_rows: int | None = None,
    calibration_bins: int = 10,
    min_positive_support: int = 10,
    auto_adjust_split_for_support: bool = False,
    continue_on_optional_model_error: bool = True,
) -> dict[str, Any]:
    input_csv_path = Path(input_path).resolve()
    if not input_csv_path.exists():
        raise FileNotFoundError(f"Input CSV does not exist: {input_csv_path}")

    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    dataset_name = input_csv_path.stem
    rows_for_split_probe: list[dict[str, str]] | None = None

    requested_tabular_models = list(ALL_TABULAR_MODEL_NAMES)
    executable_tabular_models = list(requested_tabular_models)
    optional_skip_reasons: dict[str, str] = {}
    if benchmark_module.torch is None and "torch_mlp" in executable_tabular_models:
        executable_tabular_models.remove("torch_mlp")
        optional_skip_reasons["torch_mlp"] = "PyTorch is not installed."

    effective_train_fraction = float(train_fraction)
    effective_val_fraction = float(val_fraction)
    split_support_probes: list[dict[str, Any]] = []
    split_was_auto_adjusted = False
    if bool(auto_adjust_split_for_support):
        rows_for_split_probe = benchmark_module.load_pairwise_dataset_rows(input_csv_path)
        effective_train_fraction, effective_val_fraction, split_support_probes, split_was_auto_adjusted = _choose_support_aware_split(
            rows=rows_for_split_probe,
            split_strategy=str(split_strategy),
            train_fraction=float(train_fraction),
            val_fraction=float(val_fraction),
            min_positive_support=int(min_positive_support),
        )

    tabular_prefix = output_root / f"{dataset_name}_tabular_all_models"
    benchmark_summary = run_pairwise_benchmark(
        input_path=input_csv_path,
        output_prefix=tabular_prefix,
        model_names=executable_tabular_models,
        train_fraction=float(effective_train_fraction),
        val_fraction=float(effective_val_fraction),
        split_strategy=str(split_strategy),
        torch_device=str(torch_device),
        random_seed=random_seed,
    )

    benchmark_models = benchmark_summary.get("models", {})
    calibration_model_names = [
        model_name
        for model_name in executable_tabular_models
        if isinstance(benchmark_models.get(model_name), dict) and benchmark_models.get(model_name, {}).get("status", "completed") != "skipped"
    ]

    calibration_summary: dict[str, Any]
    if calibration_model_names:
        calibration_prefix = output_root / f"{dataset_name}_tabular_all_models_calibration"
        calibration_summary = run_calibration_evaluation(
            predictions_csv_path=benchmark_summary["predictions_csv_path"],
            output_prefix=calibration_prefix,
            model_names=calibration_model_names,
            num_bins=int(calibration_bins),
        )
    else:
        calibration_summary = {"models": {}}

    tabular_confusions = _compute_prediction_confusions(
        predictions_csv_path=benchmark_summary["predictions_csv_path"],
        prediction_model_names=executable_tabular_models,
    )

    rows: list[dict[str, Any]] = []
    low_support_warnings: list[dict[str, Any]] = []
    for model_name in requested_tabular_models:
        metrics = benchmark_models.get(model_name) if isinstance(benchmark_models, dict) else None
        calibration_metrics = calibration_summary.get("models", {}).get(model_name, {})
        confusion = tabular_confusions.get(model_name, {})
        status = "skipped"
        notes = optional_skip_reasons.get(model_name, "Model was not executed.")
        if isinstance(metrics, dict):
            status = str(metrics.get("status", "completed"))
            notes = str(metrics.get("reason", "")) if metrics.get("reason") else ""
        positive_count = confusion.get("positive_count")
        if status == "completed" and positive_count is not None and positive_count < int(min_positive_support):
            notes = _merge_notes(notes, f"low_positive_support={positive_count}")
            low_support_warnings.append(
                {
                    "dataset": dataset_name,
                    "model_name": model_name,
                    "positive_count": int(positive_count),
                    "minimum_required": int(min_positive_support),
                }
            )
        rows.append(
            {
                "dataset": dataset_name,
                "model_family": "tabular",
                "model_name": model_name,
                "status": status,
                "f1": metrics.get("f1") if isinstance(metrics, dict) else None,
                "precision": metrics.get("precision") if isinstance(metrics, dict) else None,
                "recall": metrics.get("recall") if isinstance(metrics, dict) else None,
                "auroc": metrics.get("auroc") if isinstance(metrics, dict) else None,
                "auprc": metrics.get("auprc") if isinstance(metrics, dict) else None,
                "accuracy": metrics.get("accuracy") if isinstance(metrics, dict) else None,
                "threshold": metrics.get("threshold") if isinstance(metrics, dict) else None,
                "sample_count": confusion.get("sample_count"),
                "positive_count": positive_count,
                "negative_count": confusion.get("negative_count"),
                "tp": confusion.get("tp"),
                "fp": confusion.get("fp"),
                "tn": confusion.get("tn"),
                "fn": confusion.get("fn"),
                "ece": calibration_metrics.get("ece"),
                "brier_score": calibration_metrics.get("brier_score"),
                "elapsed_seconds": metrics.get("elapsed_seconds") if isinstance(metrics, dict) else None,
                "device": metrics.get("device") if isinstance(metrics, dict) else None,
                "epochs": metrics.get("epochs") if isinstance(metrics, dict) else None,
                "hidden_dim": metrics.get("hidden_dim") if isinstance(metrics, dict) else None,
                "split_strategy": split_strategy,
                "summary_json_path": benchmark_summary.get("summary_json_path"),
                "predictions_csv_path": benchmark_summary.get("predictions_csv_path"),
                "notes": notes,
            }
        )

    resolved_cnn_losses = _resolve_cnn_losses(cnn_losses) if include_regional_cnn else []
    cnn_runs: list[dict[str, Any]] = []
    if include_regional_cnn:
        for loss_type in resolved_cnn_losses:
            model_alias = CNN_LOSS_TO_MODEL_NAME[loss_type]
            cnn_prefix = output_root / f"{dataset_name}_{model_alias}"
            try:
                cnn_summary = run_regional_raster_cnn_benchmark(
                    input_path=input_csv_path,
                    output_prefix=cnn_prefix,
                    split_strategy=str(split_strategy),
                    train_fraction=float(effective_train_fraction),
                    val_fraction=float(effective_val_fraction),
                    half_width_nm=float(cnn_half_width_nm),
                    raster_size=int(cnn_raster_size),
                    torch_device=str(torch_device),
                    random_seed=random_seed,
                    epochs=int(cnn_epochs),
                    batch_size=int(cnn_batch_size),
                    learning_rate=float(cnn_learning_rate),
                    balance_batches=bool(cnn_balance_batches),
                    loss_type=loss_type,
                    focal_gamma=float(cnn_focal_gamma),
                    max_train_rows=cnn_max_train_rows,
                    max_val_rows=cnn_max_val_rows,
                    max_test_rows=cnn_max_test_rows,
                )
            except Exception as exc:
                if not continue_on_optional_model_error:
                    raise
                rows.append(
                    {
                        "dataset": dataset_name,
                        "model_family": "regional_raster_cnn",
                        "model_name": model_alias,
                        "status": "error",
                        "f1": None,
                        "precision": None,
                        "recall": None,
                        "auroc": None,
                        "auprc": None,
                        "accuracy": None,
                        "threshold": None,
                        "ece": None,
                        "brier_score": None,
                        "elapsed_seconds": None,
                        "device": None,
                        "epochs": int(cnn_epochs),
                        "hidden_dim": None,
                        "split_strategy": split_strategy,
                        "summary_json_path": "",
                        "predictions_csv_path": "",
                        "notes": str(exc),
                    }
                )
                continue

            cnn_runs.append(cnn_summary)
            metrics = cnn_summary.get("metrics", {})
            calibration_metrics = cnn_summary.get("calibration_metrics", {})
            temperature_metrics = cnn_summary.get("temperature_scaling", {}).get("metrics", {})
            temperature_calibration_metrics = cnn_summary.get("temperature_scaled_calibration_metrics", {})
            training_info = cnn_summary.get("training_info", {})
            cnn_confusions = _compute_prediction_confusions(
                predictions_csv_path=cnn_summary.get("predictions_csv_path", ""),
                prediction_model_names=["cnn", "cnn_temp"],
            )
            raw_confusion = cnn_confusions.get("cnn", {})
            temp_confusion = cnn_confusions.get("cnn_temp", {})
            raw_notes = f"loss={loss_type}"
            temp_notes = f"loss={loss_type}; temperature_scaled"
            raw_positive_count = raw_confusion.get("positive_count")
            temp_positive_count = temp_confusion.get("positive_count")
            if metrics.get("status", "completed") == "completed" and raw_positive_count is not None and raw_positive_count < int(min_positive_support):
                raw_notes = _merge_notes(raw_notes, f"low_positive_support={raw_positive_count}")
                low_support_warnings.append(
                    {
                        "dataset": dataset_name,
                        "model_name": model_alias,
                        "positive_count": int(raw_positive_count),
                        "minimum_required": int(min_positive_support),
                    }
                )
            if temperature_metrics.get("status", "completed") == "completed" and temp_positive_count is not None and temp_positive_count < int(min_positive_support):
                temp_notes = _merge_notes(temp_notes, f"low_positive_support={temp_positive_count}")
                low_support_warnings.append(
                    {
                        "dataset": dataset_name,
                        "model_name": f"{model_alias}_temp",
                        "positive_count": int(temp_positive_count),
                        "minimum_required": int(min_positive_support),
                    }
                )

            rows.append(
                {
                    "dataset": dataset_name,
                    "model_family": "regional_raster_cnn",
                    "model_name": model_alias,
                    "status": metrics.get("status", "completed"),
                    "f1": metrics.get("f1"),
                    "precision": metrics.get("precision"),
                    "recall": metrics.get("recall"),
                    "auroc": metrics.get("auroc"),
                    "auprc": metrics.get("auprc"),
                    "accuracy": metrics.get("accuracy"),
                    "threshold": metrics.get("threshold"),
                    "sample_count": raw_confusion.get("sample_count"),
                    "positive_count": raw_positive_count,
                    "negative_count": raw_confusion.get("negative_count"),
                    "tp": raw_confusion.get("tp"),
                    "fp": raw_confusion.get("fp"),
                    "tn": raw_confusion.get("tn"),
                    "fn": raw_confusion.get("fn"),
                    "ece": calibration_metrics.get("ece"),
                    "brier_score": calibration_metrics.get("brier_score"),
                    "elapsed_seconds": metrics.get("elapsed_seconds"),
                    "device": training_info.get("device"),
                    "epochs": training_info.get("epochs"),
                    "hidden_dim": None,
                    "split_strategy": split_strategy,
                    "summary_json_path": cnn_summary.get("summary_json_path"),
                    "predictions_csv_path": cnn_summary.get("predictions_csv_path"),
                    "notes": raw_notes,
                }
            )
            rows.append(
                {
                    "dataset": dataset_name,
                    "model_family": "regional_raster_cnn",
                    "model_name": f"{model_alias}_temp",
                    "status": temperature_metrics.get("status", "completed"),
                    "f1": temperature_metrics.get("f1"),
                    "precision": temperature_metrics.get("precision"),
                    "recall": temperature_metrics.get("recall"),
                    "auroc": temperature_metrics.get("auroc"),
                    "auprc": temperature_metrics.get("auprc"),
                    "accuracy": temperature_metrics.get("accuracy"),
                    "threshold": temperature_metrics.get("threshold"),
                    "sample_count": temp_confusion.get("sample_count"),
                    "positive_count": temp_positive_count,
                    "negative_count": temp_confusion.get("negative_count"),
                    "tp": temp_confusion.get("tp"),
                    "fp": temp_confusion.get("fp"),
                    "tn": temp_confusion.get("tn"),
                    "fn": temp_confusion.get("fn"),
                    "ece": temperature_calibration_metrics.get("ece"),
                    "brier_score": temperature_calibration_metrics.get("brier_score"),
                    "elapsed_seconds": metrics.get("elapsed_seconds"),
                    "device": training_info.get("device"),
                    "epochs": training_info.get("epochs"),
                    "hidden_dim": None,
                    "split_strategy": split_strategy,
                    "summary_json_path": cnn_summary.get("summary_json_path"),
                    "predictions_csv_path": cnn_summary.get("predictions_csv_path"),
                    "notes": temp_notes,
                }
            )

    sorted_rows = sorted(rows, key=_row_sort_key)
    top_model = {}
    for row in sorted_rows:
        if row.get("status") == "completed":
            top_model = row
            break

    leaderboard_csv_path = output_root / f"{dataset_name}_all_models_leaderboard.csv"
    leaderboard_md_path = output_root / f"{dataset_name}_all_models_leaderboard.md"
    summary_json_path = output_root / f"{dataset_name}_all_models_run_summary.json"
    summary_md_path = output_root / f"{dataset_name}_all_models_run_summary.md"

    _write_leaderboard_csv(leaderboard_csv_path, sorted_rows)

    summary: dict[str, Any] = {
        "status": "completed",
        "input_csv_path": str(input_csv_path),
        "output_dir": str(output_root),
        "dataset_name": dataset_name,
        "split_strategy": split_strategy,
        "requested_train_fraction": float(train_fraction),
        "requested_val_fraction": float(val_fraction),
        "effective_train_fraction": float(effective_train_fraction),
        "effective_val_fraction": float(effective_val_fraction),
        "auto_adjust_split_for_support": bool(auto_adjust_split_for_support),
        "split_was_auto_adjusted": bool(split_was_auto_adjusted),
        "split_support_probes": split_support_probes,
        "torch_device": str(torch_device),
        "random_seed": random_seed,
        "tabular_models_requested": requested_tabular_models,
        "tabular_models_executed": executable_tabular_models,
        "tabular_benchmark_summary_json_path": benchmark_summary.get("summary_json_path"),
        "tabular_calibration_summary_json_path": calibration_summary.get("summary_json_path"),
        "include_regional_cnn": bool(include_regional_cnn),
        "cnn_losses": resolved_cnn_losses,
        "min_positive_support": int(min_positive_support),
        "low_support_warnings": low_support_warnings,
        "cnn_summary_json_paths": [item.get("summary_json_path") for item in cnn_runs if isinstance(item, dict)],
        "row_count": len(sorted_rows),
        "top_model": top_model,
        "leaderboard_csv_path": str(leaderboard_csv_path),
        "leaderboard_md_path": str(leaderboard_md_path),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }

    leaderboard_md_path.write_text(_build_leaderboard_markdown(summary, sorted_rows), encoding="utf-8")
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(_build_summary_markdown(summary), encoding="utf-8")
    return summary
