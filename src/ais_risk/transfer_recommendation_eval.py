from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .benchmark import run_pairwise_transfer_benchmark
from .calibration_eval import run_calibration_evaluation


RESULT_FIELDS = [
    "source_region",
    "target_region",
    "source_dataset",
    "target_dataset",
    "recommended_model",
    "status",
    "source_f1",
    "target_f1",
    "delta_f1",
    "source_auroc",
    "target_auroc",
    "delta_auroc",
    "target_ece",
    "target_brier",
    "threshold",
    "transfer_summary_json_path",
    "target_predictions_csv_path",
    "target_calibration_summary_json_path",
    "notes",
]


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _fmt(value: Any, digits: int = 4) -> str:
    number = _safe_float(value)
    if number is None:
        return "n/a"
    return f"{number:.{digits}f}"


def _parse_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _recommendation_map(path: str | Path) -> dict[str, str]:
    rows = _parse_csv_rows(path)
    mapping: dict[str, str] = {}
    for row in rows:
        dataset = str(row.get("dataset", "")).strip()
        model = str(row.get("model_name", "")).strip()
        if not dataset or not model:
            continue
        mapping[dataset] = model
    return mapping


def _markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Cross-Region Transfer Recommendation Check",
        "",
        "## Inputs",
        "",
        f"- recommendation_csv: `{summary['recommendation_csv_path']}`",
        f"- split_strategy: `{summary['split_strategy']}`",
        f"- train_fraction: `{summary['train_fraction']}`",
        f"- val_fraction: `{summary['val_fraction']}`",
        f"- threshold_grid_step: `{summary['threshold_grid_step']}`",
        f"- calibration_bins: `{summary['calibration_bins']}`",
        "",
        "## Results",
        "",
        "| Source | Target | Model | Status | Source F1 | Target F1 | ΔF1 | Source AUROC | Target AUROC | ΔAUROC | Target ECE |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {src} | {tgt} | {model} | {status} | {sf1} | {tf1} | {df1} | {sauroc} | {tauroc} | {dauroc} | {tece} |".format(
                src=row.get("source_region", ""),
                tgt=row.get("target_region", ""),
                model=row.get("recommended_model", ""),
                status=row.get("status", ""),
                sf1=_fmt(row.get("source_f1")),
                tf1=_fmt(row.get("target_f1")),
                df1=_fmt(row.get("delta_f1")),
                sauroc=_fmt(row.get("source_auroc")),
                tauroc=_fmt(row.get("target_auroc")),
                dauroc=_fmt(row.get("delta_auroc")),
                tece=_fmt(row.get("target_ece")),
            )
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- results_csv: `{summary['results_csv_path']}`",
            f"- results_md: `{summary['results_md_path']}`",
            f"- summary_json: `{summary['summary_json_path']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run_cross_region_transfer_recommendation_check(
    input_paths_by_region: dict[str, str | Path],
    recommendation_csv_path: str | Path,
    output_root: str | Path,
    split_strategy: str = "own_ship",
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    torch_device: str = "auto",
    random_seed: int = 42,
    calibration_bins: int = 10,
    threshold_grid_step: float = 0.05,
) -> dict[str, Any]:
    output_root_path = Path(output_root).resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)
    recommendation_map = _recommendation_map(recommendation_csv_path)
    paths = {region: Path(path).resolve() for region, path in input_paths_by_region.items()}

    rows: list[dict[str, Any]] = []
    for source_region in sorted(paths.keys()):
        source_path = paths[source_region]
        source_dataset = source_path.stem
        model_name = recommendation_map.get(source_dataset, "")
        for target_region in sorted(paths.keys()):
            if source_region == target_region:
                continue
            target_path = paths[target_region]
            target_dataset = target_path.stem
            payload: dict[str, Any] = {
                "source_region": source_region,
                "target_region": target_region,
                "source_dataset": source_dataset,
                "target_dataset": target_dataset,
                "recommended_model": model_name,
                "status": "pending",
                "source_f1": None,
                "target_f1": None,
                "delta_f1": None,
                "source_auroc": None,
                "target_auroc": None,
                "delta_auroc": None,
                "target_ece": None,
                "target_brier": None,
                "threshold": None,
                "transfer_summary_json_path": "",
                "target_predictions_csv_path": "",
                "target_calibration_summary_json_path": "",
                "notes": "",
            }
            if not model_name:
                payload["status"] = "missing_recommendation"
                payload["notes"] = "No recommendation found for source dataset."
                rows.append(payload)
                continue
            try:
                run_prefix = output_root_path / f"{source_region}_to_{target_region}" / f"{model_name}_transfer"
                transfer_summary = run_pairwise_transfer_benchmark(
                    train_input_path=source_path,
                    target_input_path=target_path,
                    output_prefix=run_prefix,
                    model_names=[model_name],
                    train_fraction=float(train_fraction),
                    val_fraction=float(val_fraction),
                    split_strategy=split_strategy,
                    torch_device=torch_device,
                    random_seed=int(random_seed),
                    threshold_grid_step=float(threshold_grid_step),
                )
                model_summary = transfer_summary.get("models", {}).get(model_name, {})
                source_metrics = model_summary.get("source_test", {})
                target_metrics = model_summary.get("target_transfer", {})
                payload["status"] = str(model_summary.get("status", "unknown"))
                payload["source_f1"] = _safe_float(source_metrics.get("f1"))
                payload["target_f1"] = _safe_float(target_metrics.get("f1"))
                payload["source_auroc"] = _safe_float(source_metrics.get("auroc"))
                payload["target_auroc"] = _safe_float(target_metrics.get("auroc"))
                payload["threshold"] = _safe_float(model_summary.get("threshold"))
                payload["transfer_summary_json_path"] = transfer_summary.get("transfer_summary_json_path", "")
                payload["target_predictions_csv_path"] = transfer_summary.get("target_predictions_csv_path", "")

                if payload["source_f1"] is not None and payload["target_f1"] is not None:
                    payload["delta_f1"] = float(payload["target_f1"]) - float(payload["source_f1"])
                if payload["source_auroc"] is not None and payload["target_auroc"] is not None:
                    payload["delta_auroc"] = float(payload["target_auroc"]) - float(payload["source_auroc"])

                if payload["status"] == "completed" and payload["target_predictions_csv_path"]:
                    calibration_prefix = run_prefix.with_name(f"{run_prefix.name}_target_calibration")
                    calibration_summary = run_calibration_evaluation(
                        predictions_csv_path=payload["target_predictions_csv_path"],
                        output_prefix=calibration_prefix,
                        model_names=[model_name],
                        num_bins=int(calibration_bins),
                    )
                    model_calibration = calibration_summary.get("models", {}).get(model_name, {})
                    payload["target_ece"] = _safe_float(model_calibration.get("ece"))
                    payload["target_brier"] = _safe_float(model_calibration.get("brier_score"))
                    payload["target_calibration_summary_json_path"] = calibration_summary.get("summary_json_path", "")
            except Exception as exc:
                payload["status"] = "error"
                payload["notes"] = str(exc)
            rows.append(payload)

    results_csv_path = output_root_path / "transfer_recommendation_check.csv"
    results_md_path = output_root_path / "transfer_recommendation_check.md"
    summary_json_path = output_root_path / "transfer_recommendation_check_summary.json"
    _write_csv(results_csv_path, rows, RESULT_FIELDS)

    summary: dict[str, Any] = {
        "status": "completed",
        "output_root": str(output_root_path),
        "recommendation_csv_path": str(Path(recommendation_csv_path).resolve()),
        "split_strategy": split_strategy,
        "train_fraction": float(train_fraction),
        "val_fraction": float(val_fraction),
        "threshold_grid_step": float(threshold_grid_step),
        "torch_device": torch_device,
        "random_seed": int(random_seed),
        "calibration_bins": int(calibration_bins),
        "pair_count": len(rows),
        "results_csv_path": str(results_csv_path),
        "results_md_path": str(results_md_path),
        "summary_json_path": str(summary_json_path),
    }
    results_md_path.write_text(_markdown(summary, rows), encoding="utf-8")
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
