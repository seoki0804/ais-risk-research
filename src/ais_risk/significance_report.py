from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path
from statistics import mean
from typing import Any


RESULT_FIELDS = [
    "dataset",
    "recommended_model",
    "comparator_model",
    "n_pairs",
    "recommended_f1_mean",
    "comparator_f1_mean",
    "delta_f1_mean",
    "delta_f1_ci_low",
    "delta_f1_ci_high",
    "delta_f1_sign_p",
    "recommended_ece_mean",
    "comparator_ece_mean",
    "delta_ece_mean",
    "delta_ece_ci_low",
    "delta_ece_ci_high",
    "delta_ece_sign_p",
    "f1_rec_better_ci",
    "ece_rec_lower_ci",
    "note",
]


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


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot compute quantile on empty list.")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    q_clamped = min(1.0, max(0.0, float(q)))
    position = (len(sorted_values) - 1) * q_clamped
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return float(sorted_values[lo])
    weight = position - lo
    return float(sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * weight)


def _bootstrap_mean_ci(values: list[float], bootstrap_samples: int, seed: int) -> tuple[float, float, float]:
    if not values:
        raise ValueError("Cannot compute bootstrap CI from empty values.")
    center = float(mean(values))
    if len(values) == 1:
        return center, center, center
    rng = random.Random(int(seed))
    n = len(values)
    sampled_means: list[float] = []
    for _ in range(int(bootstrap_samples)):
        acc = 0.0
        for _ in range(n):
            acc += values[rng.randrange(n)]
        sampled_means.append(acc / n)
    sampled_means.sort()
    return center, _quantile(sampled_means, 0.025), _quantile(sampled_means, 0.975)


def _two_sided_sign_test_p(values: list[float]) -> float:
    positives = sum(1 for value in values if value > 0)
    negatives = sum(1 for value in values if value < 0)
    trials = positives + negatives
    if trials == 0:
        return 1.0
    k = min(positives, negatives)
    prob = 0.0
    for i in range(k + 1):
        prob += math.comb(trials, i) / (2**trials)
    return float(min(1.0, 2.0 * prob))


def _recommendation_map(path: str | Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in _parse_csv_rows(path):
        dataset = str(row.get("dataset", "")).strip()
        model_name = str(row.get("model_name", "")).strip()
        if dataset and model_name:
            mapping[dataset] = model_name
    return mapping


def _model_seed_metrics(raw_rows: list[dict[str, str]]) -> dict[str, dict[str, dict[int, dict[str, float]]]]:
    output: dict[str, dict[str, dict[int, dict[str, float]]]] = {}
    for row in raw_rows:
        if str(row.get("status", "")) != "completed":
            continue
        dataset = str(row.get("dataset", "")).strip()
        model = str(row.get("model_name", "")).strip()
        seed_value = _safe_float(row.get("seed"))
        f1_value = _safe_float(row.get("f1"))
        ece_value = _safe_float(row.get("ece"))
        if not dataset or not model or seed_value is None or f1_value is None or ece_value is None:
            continue
        seed = int(seed_value)
        output.setdefault(dataset, {}).setdefault(model, {})[seed] = {"f1": float(f1_value), "ece": float(ece_value)}
    return output


def _best_comparator_model(
    per_model_seed_metrics: dict[str, dict[int, dict[str, float]]],
    recommended_model: str,
) -> str | None:
    candidates: list[tuple[float, float, str]] = []
    for model_name, seed_payload in per_model_seed_metrics.items():
        if model_name == recommended_model:
            continue
        f1_values = [float(item["f1"]) for item in seed_payload.values()]
        ece_values = [float(item["ece"]) for item in seed_payload.values()]
        if not f1_values:
            continue
        candidates.append((float(mean(f1_values)), float(mean(ece_values)) if ece_values else 999.0, model_name))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    return str(candidates[0][2])


def run_significance_report(
    recommendation_csv_path: str | Path,
    raw_rows_csv_path: str | Path,
    output_prefix: str | Path,
    bootstrap_samples: int = 5000,
    bootstrap_seed: int = 42,
    min_pairs: int = 5,
) -> dict[str, Any]:
    recommendation_by_dataset = _recommendation_map(recommendation_csv_path)
    raw_rows = _parse_csv_rows(raw_rows_csv_path)
    per_dataset = _model_seed_metrics(raw_rows)
    results: list[dict[str, Any]] = []

    for dataset in sorted(recommendation_by_dataset.keys()):
        recommended_model = recommendation_by_dataset[dataset]
        dataset_models = per_dataset.get(dataset, {})
        if recommended_model not in dataset_models:
            results.append(
                {
                    "dataset": dataset,
                    "recommended_model": recommended_model,
                    "comparator_model": "",
                    "n_pairs": 0,
                    "note": "recommended model missing in raw rows",
                }
            )
            continue
        comparator_model = _best_comparator_model(dataset_models, recommended_model=recommended_model)
        if not comparator_model:
            results.append(
                {
                    "dataset": dataset,
                    "recommended_model": recommended_model,
                    "comparator_model": "",
                    "n_pairs": 0,
                    "note": "no comparator model available",
                }
            )
            continue

        rec_seed_metrics = dataset_models[recommended_model]
        cmp_seed_metrics = dataset_models[comparator_model]
        paired_seeds = sorted(set(rec_seed_metrics.keys()) & set(cmp_seed_metrics.keys()))
        if len(paired_seeds) < int(min_pairs):
            results.append(
                {
                    "dataset": dataset,
                    "recommended_model": recommended_model,
                    "comparator_model": comparator_model,
                    "n_pairs": len(paired_seeds),
                    "note": f"insufficient paired seeds (<{int(min_pairs)})",
                }
            )
            continue

        rec_f1_values = [float(rec_seed_metrics[seed]["f1"]) for seed in paired_seeds]
        cmp_f1_values = [float(cmp_seed_metrics[seed]["f1"]) for seed in paired_seeds]
        rec_ece_values = [float(rec_seed_metrics[seed]["ece"]) for seed in paired_seeds]
        cmp_ece_values = [float(cmp_seed_metrics[seed]["ece"]) for seed in paired_seeds]
        delta_f1_values = [rec_f1_values[i] - cmp_f1_values[i] for i in range(len(paired_seeds))]
        delta_ece_values = [rec_ece_values[i] - cmp_ece_values[i] for i in range(len(paired_seeds))]

        f1_mean, f1_ci_low, f1_ci_high = _bootstrap_mean_ci(
            delta_f1_values,
            bootstrap_samples=int(bootstrap_samples),
            seed=int(bootstrap_seed) + 17,
        )
        ece_mean, ece_ci_low, ece_ci_high = _bootstrap_mean_ci(
            delta_ece_values,
            bootstrap_samples=int(bootstrap_samples),
            seed=int(bootstrap_seed) + 31,
        )

        row = {
            "dataset": dataset,
            "recommended_model": recommended_model,
            "comparator_model": comparator_model,
            "n_pairs": len(paired_seeds),
            "recommended_f1_mean": float(mean(rec_f1_values)),
            "comparator_f1_mean": float(mean(cmp_f1_values)),
            "delta_f1_mean": f1_mean,
            "delta_f1_ci_low": f1_ci_low,
            "delta_f1_ci_high": f1_ci_high,
            "delta_f1_sign_p": _two_sided_sign_test_p(delta_f1_values),
            "recommended_ece_mean": float(mean(rec_ece_values)),
            "comparator_ece_mean": float(mean(cmp_ece_values)),
            "delta_ece_mean": ece_mean,
            "delta_ece_ci_low": ece_ci_low,
            "delta_ece_ci_high": ece_ci_high,
            "delta_ece_sign_p": _two_sided_sign_test_p(delta_ece_values),
            "f1_rec_better_ci": bool(f1_ci_low > 0.0),
            "ece_rec_lower_ci": bool(ece_ci_high < 0.0),
            "note": "",
        }
        results.append(row)

    output_root = Path(output_prefix).resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_root.with_suffix(".csv")
    md_path = output_root.with_suffix(".md")
    json_path = output_root.with_suffix(".json")
    _write_csv(csv_path, results, RESULT_FIELDS)

    lines = [
        "# Significance Report (Recommended vs Best Alternative)",
        "",
        "## Inputs",
        "",
        f"- recommendation_csv: `{Path(recommendation_csv_path).resolve()}`",
        f"- raw_rows_csv: `{Path(raw_rows_csv_path).resolve()}`",
        f"- bootstrap_samples: `{int(bootstrap_samples)}`",
        f"- min_pairs: `{int(min_pairs)}`",
        "",
        "## Pairwise Delta Summary",
        "",
        "| Dataset | Recommended | Comparator | n | ΔF1 mean (CI95) | sign p(F1) | ΔECE mean (CI95) | sign p(ECE) | F1 rec>cmp (CI) | ECE rec<cmp (CI) |",
        "|---|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in results:
        lines.append(
            "| {dataset} | {rec} | {cmp} | {n} | {f1m} ({f1l},{f1h}) | {pf1} | {ecem} ({ecel},{eceh}) | {pece} | {f1sig} | {ecesig} |".format(
                dataset=row.get("dataset", ""),
                rec=row.get("recommended_model", ""),
                cmp=row.get("comparator_model", ""),
                n=row.get("n_pairs", 0),
                f1m=_fmt(row.get("delta_f1_mean")),
                f1l=_fmt(row.get("delta_f1_ci_low")),
                f1h=_fmt(row.get("delta_f1_ci_high")),
                pf1=_fmt(row.get("delta_f1_sign_p")),
                ecem=_fmt(row.get("delta_ece_mean")),
                ecel=_fmt(row.get("delta_ece_ci_low")),
                eceh=_fmt(row.get("delta_ece_ci_high")),
                pece=_fmt(row.get("delta_ece_sign_p")),
                f1sig=str(row.get("f1_rec_better_ci", False)),
                ecesig=str(row.get("ece_rec_lower_ci", False)),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation Rule",
            "",
            "- `F1 rec>cmp (CI)=True` means the 95% CI of `(recommended - comparator)` F1 is strictly positive.",
            "- `ECE rec<cmp (CI)=True` means the 95% CI of `(recommended - comparator)` ECE is strictly negative.",
            "- Sign-test p-values are two-sided, computed on paired seed deltas.",
            "",
            "## Outputs",
            "",
            f"- csv: `{csv_path}`",
            f"- md: `{md_path}`",
            f"- json: `{json_path}`",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "completed",
        "row_count": len(results),
        "bootstrap_samples": int(bootstrap_samples),
        "min_pairs": int(min_pairs),
        "csv_path": str(csv_path),
        "md_path": str(md_path),
        "json_path": str(json_path),
        "results": results,
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
