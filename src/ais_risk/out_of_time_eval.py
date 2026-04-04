from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .all_models import run_all_supported_models


RESULT_FIELDS = [
    "region",
    "dataset",
    "recommended_model",
    "status",
    "baseline_split",
    "baseline_f1",
    "baseline_auroc",
    "baseline_ece",
    "baseline_positive_count",
    "out_of_time_split",
    "out_of_time_f1",
    "out_of_time_auroc",
    "out_of_time_ece",
    "out_of_time_positive_count",
    "delta_f1",
    "delta_auroc",
    "delta_ece",
    "leaderboard_csv_path",
    "summary_json_path",
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


def _baseline_map(path: str | Path) -> dict[tuple[str, str], dict[str, str]]:
    rows = _parse_csv_rows(path)
    mapping: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        dataset = str(row.get("dataset", "")).strip()
        model = str(row.get("model_name", "")).strip()
        if not dataset or not model:
            continue
        if str(row.get("status", "")).strip() != "completed":
            continue
        key = (dataset, model)
        if key not in mapping:
            mapping[key] = row
    return mapping


def _markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Out-of-Time Recommendation Check",
        "",
        "## Inputs",
        "",
        f"- recommendation_csv: `{summary['recommendation_csv_path']}`",
        f"- baseline_leaderboard_csv: `{summary.get('baseline_leaderboard_csv_path', '')}`",
        f"- split_strategy: `{summary['split_strategy']}`",
        f"- train_fraction: `{summary['train_fraction']}`",
        f"- val_fraction: `{summary['val_fraction']}`",
        f"- include_regional_cnn: `{summary['include_regional_cnn']}`",
        "",
        "## Results",
        "",
        "| Region | Dataset | Model | Status | Baseline F1 | OOT F1 | ΔF1 | Baseline AUROC | OOT AUROC | ΔAUROC | Baseline ECE | OOT ECE | ΔECE |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {region} | {dataset} | {model} | {status} | {bf1} | {of1} | {df1} | {bauroc} | {oauroc} | {dauroc} | {bece} | {oece} | {dece} |".format(
                region=row.get("region", ""),
                dataset=row.get("dataset", ""),
                model=row.get("recommended_model", ""),
                status=row.get("status", ""),
                bf1=_fmt(row.get("baseline_f1")),
                of1=_fmt(row.get("out_of_time_f1")),
                df1=_fmt(row.get("delta_f1")),
                bauroc=_fmt(row.get("baseline_auroc")),
                oauroc=_fmt(row.get("out_of_time_auroc")),
                dauroc=_fmt(row.get("delta_auroc")),
                bece=_fmt(row.get("baseline_ece")),
                oece=_fmt(row.get("out_of_time_ece")),
                dece=_fmt(row.get("delta_ece")),
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


def run_out_of_time_recommendation_check(
    input_paths_by_region: dict[str, str | Path],
    recommendation_csv_path: str | Path,
    output_root: str | Path,
    baseline_leaderboard_csv_path: str | Path | None = None,
    split_strategy: str = "timestamp",
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    torch_device: str = "auto",
    random_seed: int = 42,
    include_regional_cnn: bool = False,
    cnn_losses: list[str] | None = None,
    min_positive_support: int = 10,
    auto_adjust_split_for_support: bool = False,
) -> dict[str, Any]:
    output_root_path = Path(output_root).resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)
    recommendation_map = _recommendation_map(recommendation_csv_path)
    baseline_map: dict[tuple[str, str], dict[str, str]] = {}
    if baseline_leaderboard_csv_path:
        baseline_map = _baseline_map(baseline_leaderboard_csv_path)

    rows: list[dict[str, Any]] = []
    for region in sorted(input_paths_by_region.keys()):
        input_path = Path(input_paths_by_region[region]).resolve()
        dataset = input_path.stem
        recommended_model = recommendation_map.get(dataset, "")
        payload: dict[str, Any] = {
            "region": region,
            "dataset": dataset,
            "recommended_model": recommended_model,
            "status": "pending",
            "baseline_split": "own_ship",
            "baseline_f1": None,
            "baseline_auroc": None,
            "baseline_ece": None,
            "baseline_positive_count": None,
            "out_of_time_split": split_strategy,
            "out_of_time_f1": None,
            "out_of_time_auroc": None,
            "out_of_time_ece": None,
            "out_of_time_positive_count": None,
            "delta_f1": None,
            "delta_auroc": None,
            "delta_ece": None,
            "leaderboard_csv_path": "",
            "summary_json_path": "",
            "notes": "",
        }
        if not recommended_model:
            payload["status"] = "missing_recommendation"
            payload["notes"] = "No recommendation found for dataset."
            rows.append(payload)
            continue

        baseline_row = baseline_map.get((dataset, recommended_model))
        if baseline_row is not None:
            payload["baseline_f1"] = _safe_float(baseline_row.get("f1"))
            payload["baseline_auroc"] = _safe_float(baseline_row.get("auroc"))
            payload["baseline_ece"] = _safe_float(baseline_row.get("ece"))
            payload["baseline_positive_count"] = _safe_float(baseline_row.get("positive_count"))

        try:
            run_dir = output_root_path / region / "timestamp_split"
            summary = run_all_supported_models(
                input_path=input_path,
                output_dir=run_dir,
                split_strategy=split_strategy,
                train_fraction=float(train_fraction),
                val_fraction=float(val_fraction),
                torch_device=torch_device,
                random_seed=int(random_seed),
                include_regional_cnn=bool(include_regional_cnn),
                cnn_losses=cnn_losses,
                min_positive_support=int(min_positive_support),
                auto_adjust_split_for_support=bool(auto_adjust_split_for_support),
            )
            payload["leaderboard_csv_path"] = summary.get("leaderboard_csv_path", "")
            payload["summary_json_path"] = summary.get("summary_json_path", "")
            leaderboard_rows = _parse_csv_rows(summary["leaderboard_csv_path"])
            model_rows = [row for row in leaderboard_rows if row.get("model_name") == recommended_model]
            if not model_rows:
                payload["status"] = "model_not_found"
                payload["notes"] = "Recommended model missing from out-of-time leaderboard."
                rows.append(payload)
                continue

            model_row = model_rows[0]
            payload["status"] = str(model_row.get("status", "unknown"))
            payload["out_of_time_f1"] = _safe_float(model_row.get("f1"))
            payload["out_of_time_auroc"] = _safe_float(model_row.get("auroc"))
            payload["out_of_time_ece"] = _safe_float(model_row.get("ece"))
            payload["out_of_time_positive_count"] = _safe_float(model_row.get("positive_count"))
            payload["notes"] = str(model_row.get("notes", "")).strip()
            if payload["baseline_f1"] is not None and payload["out_of_time_f1"] is not None:
                payload["delta_f1"] = float(payload["out_of_time_f1"]) - float(payload["baseline_f1"])
            if payload["baseline_auroc"] is not None and payload["out_of_time_auroc"] is not None:
                payload["delta_auroc"] = float(payload["out_of_time_auroc"]) - float(payload["baseline_auroc"])
            if payload["baseline_ece"] is not None and payload["out_of_time_ece"] is not None:
                payload["delta_ece"] = float(payload["out_of_time_ece"]) - float(payload["baseline_ece"])
        except Exception as exc:
            payload["status"] = "error"
            payload["notes"] = str(exc)
        rows.append(payload)

    results_csv_path = output_root_path / "out_of_time_recommendation_check.csv"
    results_md_path = output_root_path / "out_of_time_recommendation_check.md"
    summary_json_path = output_root_path / "out_of_time_recommendation_check_summary.json"
    _write_csv(results_csv_path, rows, RESULT_FIELDS)

    summary: dict[str, Any] = {
        "status": "completed",
        "output_root": str(output_root_path),
        "recommendation_csv_path": str(Path(recommendation_csv_path).resolve()),
        "baseline_leaderboard_csv_path": str(Path(baseline_leaderboard_csv_path).resolve()) if baseline_leaderboard_csv_path else "",
        "split_strategy": split_strategy,
        "train_fraction": float(train_fraction),
        "val_fraction": float(val_fraction),
        "torch_device": torch_device,
        "random_seed": int(random_seed),
        "include_regional_cnn": bool(include_regional_cnn),
        "min_positive_support": int(min_positive_support),
        "row_count": len(rows),
        "results_csv_path": str(results_csv_path),
        "results_md_path": str(results_md_path),
        "summary_json_path": str(summary_json_path),
    }
    results_md_path.write_text(_markdown(summary, rows), encoding="utf-8")
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
