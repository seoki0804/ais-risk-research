from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _infer_horizon_tag(dirname: str) -> str:
    if "base_horizon10" in dirname:
        return "10"
    if "base_horizon20" in dirname:
        return "20"
    if "fast_horizon10" in dirname:
        return "10"
    if "fast_horizon20" in dirname:
        return "20"
    if "fast_horizon15" in dirname:
        return "15"
    return "15"


def _infer_label_distance(dirname: str) -> str:
    marker = "label_"
    if marker not in dirname:
        return ""
    raw = dirname.split(marker, 1)[1]
    return raw.replace("p", ".")


def _collect_from_study_summary(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for summary_path in sorted(root.glob("*/**/*_study_summary.json")):
        run_dir = summary_path.parent.parent if summary_path.parent.name.endswith("_workflow") else summary_path.parent
        run_name = run_dir.name
        study = _read_json(summary_path)

        calibration_path_text = study.get("calibration_eval_summary_json_path")
        calibration = _read_json(Path(calibration_path_text)) if calibration_path_text else {}
        calib_models = calibration.get("models", {})

        benchmark_models = study.get("benchmark", {}).get("models", {})
        pairwise = study.get("pairwise", {})

        row = {
            "run_name": run_name,
            "horizon_minutes": _infer_horizon_tag(run_name),
            "label_distance_nm": _infer_label_distance(run_name),
            "pairwise_rows": str(pairwise.get("row_count", "")),
            "positive_rate": str(pairwise.get("positive_rate", "")),
            "hgbt_threshold": str(benchmark_models.get("hgbt", {}).get("threshold", "")),
            "hgbt_f1": str(benchmark_models.get("hgbt", {}).get("f1", "")),
            "hgbt_ece": str(calib_models.get("hgbt", {}).get("ece", "")),
            "logreg_threshold": str(benchmark_models.get("logreg", {}).get("threshold", "")),
            "logreg_f1": str(benchmark_models.get("logreg", {}).get("f1", "")),
            "logreg_ece": str(calib_models.get("logreg", {}).get("ece", "")),
            "own_ship_loo_hgbt_f1": "",
            "own_ship_case_hgbt_f1": "",
            "source_summary_json": str(summary_path),
        }
        rows.append(row)
    return rows


def _collect_from_fast_layout(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for run_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        pairwise_stats = run_dir / "pairwise_dataset_stats.json"
        benchmark_summary = run_dir / "benchmark_summary.json"
        calibration_summary = run_dir / "calibration_summary.json"
        loo_summary = run_dir / "own_ship_loo_own_ship_loo_summary.json"
        case_summary = run_dir / "own_ship_case_summary.json"
        if not (pairwise_stats.exists() and benchmark_summary.exists() and calibration_summary.exists()):
            continue

        pairwise = _read_json(pairwise_stats)
        benchmark = _read_json(benchmark_summary)
        calibration = _read_json(calibration_summary)
        loo = _read_json(loo_summary) if loo_summary.exists() else {}
        case = _read_json(case_summary) if case_summary.exists() else {}

        loo_hgbt = loo.get("aggregate_models", {}).get("hgbt", {})
        case_hgbt = case.get("aggregate_models", {}).get("hgbt", {})

        horizon_source = f"{root.name}/{run_dir.name}"
        row = {
            "run_name": run_dir.name,
            "horizon_minutes": _infer_horizon_tag(horizon_source),
            "label_distance_nm": _infer_label_distance(run_dir.name),
            "pairwise_rows": str(pairwise.get("row_count", "")),
            "positive_rate": str(pairwise.get("positive_rate", "")),
            "hgbt_threshold": str(benchmark.get("models", {}).get("hgbt", {}).get("threshold", "")),
            "hgbt_f1": str(benchmark.get("models", {}).get("hgbt", {}).get("f1", "")),
            "hgbt_ece": str(calibration.get("models", {}).get("hgbt", {}).get("ece", "")),
            "logreg_threshold": str(benchmark.get("models", {}).get("logreg", {}).get("threshold", "")),
            "logreg_f1": str(benchmark.get("models", {}).get("logreg", {}).get("f1", "")),
            "logreg_ece": str(calibration.get("models", {}).get("logreg", {}).get("ece", "")),
            "own_ship_loo_hgbt_f1": str(loo_hgbt.get("f1_mean", "")),
            "own_ship_case_hgbt_f1": str(case_hgbt.get("f1_mean", "")),
            "source_summary_json": str(benchmark_summary),
        }
        rows.append(row)
    return rows


def collect_rows(root: Path) -> list[dict[str, str]]:
    rows = _collect_from_study_summary(root)
    if rows:
        return rows
    return _collect_from_fast_layout(root)


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_name",
        "horizon_minutes",
        "label_distance_nm",
        "pairwise_rows",
        "positive_rate",
        "hgbt_threshold",
        "hgbt_f1",
        "hgbt_ece",
        "own_ship_loo_hgbt_f1",
        "own_ship_case_hgbt_f1",
        "logreg_threshold",
        "logreg_f1",
        "logreg_ece",
        "source_summary_json",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Label Sensitivity Sweep Summary 61day",
        "",
        "| horizon (min) | label distance (nm) | pairwise rows | positive rate | hgbt threshold | hgbt F1 | hgbt ECE | hgbt LOO F1 | hgbt case F1 | logreg threshold | logreg F1 | logreg ECE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(rows, key=lambda item: (float(item["horizon_minutes"] or 0), float(item["label_distance_nm"] or 0))):
        lines.append(
            "| {horizon_minutes} | {label_distance_nm} | {pairwise_rows} | {positive_rate} | {hgbt_threshold} | {hgbt_f1} | {hgbt_ece} | {own_ship_loo_hgbt_f1} | {own_ship_case_hgbt_f1} | {logreg_threshold} | {logreg_f1} | {logreg_ece} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize label sensitivity sweep outputs into CSV and markdown.")
    parser.add_argument("--input-root", required=True, help="Root directory containing sweep output runs.")
    parser.add_argument("--output-csv", required=True, help="Summary CSV path.")
    parser.add_argument("--output-md", required=True, help="Summary markdown path.")
    args = parser.parse_args()

    rows = collect_rows(Path(args.input_root))
    write_csv(rows, Path(args.output_csv))
    write_markdown(rows, Path(args.output_md))
    print(f"rows={len(rows)}")
    print(f"csv={args.output_csv}")
    print(f"md={args.output_md}")


if __name__ == "__main__":
    main()
