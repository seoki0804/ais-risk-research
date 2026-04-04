from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _parse_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


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


def _choose_top_models(aggregate_rows: list[dict[str, str]], top_k: int = 3) -> dict[str, list[dict[str, str]]]:
    by_dataset: dict[str, list[dict[str, str]]] = {}
    for row in aggregate_rows:
        dataset = str(row.get("dataset", ""))
        if not dataset:
            continue
        by_dataset.setdefault(dataset, []).append(row)

    output: dict[str, list[dict[str, str]]] = {}
    for dataset, rows in by_dataset.items():
        rows_sorted = sorted(
            rows,
            key=lambda item: (
                -(_safe_float(item.get("f1_mean")) or -1.0),
                (_safe_float(item.get("ece_mean")) or 999.0),
                str(item.get("model_name", "")),
            ),
        )
        output[dataset] = rows_sorted[:top_k]
    return output


def _region_from_dataset(dataset: str) -> str:
    return dataset.replace("_pooled_pairwise", "")


def run_reviewer_quality_audit(
    recommendation_csv_path: str | Path,
    aggregate_csv_path: str | Path,
    winner_summary_csv_path: str | Path,
    out_of_time_csv_path: str | Path,
    transfer_csv_path: str | Path,
    reliability_region_summary_csv_path: str | Path,
    taxonomy_region_summary_csv_path: str | Path,
    output_prefix: str | Path,
    significance_csv_path: str | Path | None = None,
    threshold_robustness_summary_csv_path: str | Path | None = None,
) -> dict[str, Any]:
    recommendation_rows = _parse_csv_rows(recommendation_csv_path)
    aggregate_rows = _parse_csv_rows(aggregate_csv_path)
    winner_rows = _parse_csv_rows(winner_summary_csv_path)
    oot_rows = _parse_csv_rows(out_of_time_csv_path)
    transfer_rows = _parse_csv_rows(transfer_csv_path)
    reliability_rows = _parse_csv_rows(reliability_region_summary_csv_path)
    taxonomy_rows = _parse_csv_rows(taxonomy_region_summary_csv_path)
    significance_rows: list[dict[str, str]] = []
    threshold_robustness_rows: list[dict[str, str]] = []
    significance_path_resolved = Path(significance_csv_path).resolve() if significance_csv_path else None
    threshold_robustness_path_resolved = (
        Path(threshold_robustness_summary_csv_path).resolve() if threshold_robustness_summary_csv_path else None
    )
    if significance_path_resolved and significance_path_resolved.exists():
        significance_rows = _parse_csv_rows(significance_path_resolved)
    if threshold_robustness_path_resolved and threshold_robustness_path_resolved.exists():
        threshold_robustness_rows = _parse_csv_rows(threshold_robustness_path_resolved)

    top_models = _choose_top_models(aggregate_rows, top_k=3)

    gate_all_enabled = all(str(row.get("ece_gate_enabled", "")).lower() == "true" for row in recommendation_rows)
    gate_values = [_safe_float(row.get("ece_gate_max")) for row in recommendation_rows]
    gate_threshold = min([value for value in gate_values if value is not None], default=None)

    oot_negative_regions = []
    for row in oot_rows:
        delta_f1 = _safe_float(row.get("delta_f1"))
        if delta_f1 is not None and delta_f1 < 0:
            oot_negative_regions.append(
                {
                    "region": str(row.get("region", "")),
                    "model_name": str(row.get("model_name", "") or row.get("recommended_model", "")),
                    "delta_f1": float(delta_f1),
                    "delta_ece": float(_safe_float(row.get("delta_ece")) or 0.0),
                }
            )

    transfer_negative_pairs = []
    for row in transfer_rows:
        delta_f1 = _safe_float(row.get("delta_f1"))
        if delta_f1 is not None and delta_f1 < 0:
            transfer_negative_pairs.append(
                {
                    "source_region": str(row.get("source_region", "")),
                    "target_region": str(row.get("target_region", "")),
                    "model_name": str(row.get("model_name", "") or row.get("recommended_model", "")),
                    "delta_f1": float(delta_f1),
                }
            )

    high_variance_candidates = []
    for row in aggregate_rows:
        f1_std = _safe_float(row.get("f1_std"))
        if f1_std is None:
            continue
        if f1_std >= 0.03:
            high_variance_candidates.append(
                {
                    "dataset": str(row.get("dataset", "")),
                    "model_name": str(row.get("model_name", "")),
                    "f1_std": float(f1_std),
                    "ece_mean": float(_safe_float(row.get("ece_mean")) or 0.0),
                }
            )

    positive_support_by_region: dict[str, int] = {}
    for row in reliability_rows:
        region = str(row.get("region", ""))
        sample_count = int(_safe_float(row.get("sample_count")) or 0)
        positive_rate = float(_safe_float(row.get("positive_rate")) or 0.0)
        positive_support_by_region[region] = int(round(sample_count * positive_rate))

    fp_fn_by_region: dict[str, dict[str, int]] = {}
    for row in taxonomy_rows:
        region = str(row.get("region", ""))
        fp_fn_by_region[region] = {
            "fp": int(_safe_float(row.get("fp")) or 0),
            "fn": int(_safe_float(row.get("fn")) or 0),
        }

    output_root = Path(output_prefix).resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = output_root.with_suffix(".json")
    summary_md_path = output_root.with_suffix(".md")

    summary: dict[str, Any] = {
        "status": "completed",
        "recommendation_csv_path": str(Path(recommendation_csv_path).resolve()),
        "aggregate_csv_path": str(Path(aggregate_csv_path).resolve()),
        "winner_summary_csv_path": str(Path(winner_summary_csv_path).resolve()),
        "out_of_time_csv_path": str(Path(out_of_time_csv_path).resolve()),
        "transfer_csv_path": str(Path(transfer_csv_path).resolve()),
        "reliability_region_summary_csv_path": str(Path(reliability_region_summary_csv_path).resolve()),
        "taxonomy_region_summary_csv_path": str(Path(taxonomy_region_summary_csv_path).resolve()),
        "recommendation_count": len(recommendation_rows),
        "calibration_gate_enabled_for_all": gate_all_enabled,
        "calibration_gate_threshold": gate_threshold,
        "oot_negative_regions": oot_negative_regions,
        "transfer_negative_pairs": transfer_negative_pairs,
        "high_variance_candidates": high_variance_candidates,
        "positive_support_by_region": positive_support_by_region,
        "fp_fn_by_region": fp_fn_by_region,
        "significance_csv_path": str(significance_path_resolved) if significance_path_resolved else "",
        "significance_rows": len(significance_rows),
        "threshold_robustness_summary_csv_path": str(threshold_robustness_path_resolved) if threshold_robustness_path_resolved else "",
        "threshold_robustness_rows": len(threshold_robustness_rows),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }

    lines = [
        "# Reviewer Quality Audit (10-Seed Expanded Models)",
        "",
        "## Scope",
        "",
        f"- recommendation_csv: `{summary['recommendation_csv_path']}`",
        f"- aggregate_csv: `{summary['aggregate_csv_path']}`",
        f"- winner_summary_csv: `{summary['winner_summary_csv_path']}`",
        f"- out_of_time_csv: `{summary['out_of_time_csv_path']}`",
        f"- transfer_csv: `{summary['transfer_csv_path']}`",
        f"- reliability_csv: `{summary['reliability_region_summary_csv_path']}`",
        f"- taxonomy_csv: `{summary['taxonomy_region_summary_csv_path']}`",
        "",
        "## Recommendation Snapshot",
        "",
        "| Region | Dataset | Model | Family | F1 mean±std | ECE mean±std | Gate |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in recommendation_rows:
        dataset = str(row.get("dataset", ""))
        lines.append(
            "| {region} | {dataset} | {model} | {family} | {f1m}±{f1s} | {ecem}±{eces} | {gate} |".format(
                region=_region_from_dataset(dataset),
                dataset=dataset,
                model=row.get("model_name", ""),
                family=row.get("model_family", ""),
                f1m=_fmt(row.get("f1_mean")),
                f1s=_fmt(row.get("f1_std")),
                ecem=_fmt(row.get("ece_mean")),
                eces=_fmt(row.get("ece_std")),
                gate=row.get("gate_status", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Examiner Findings",
            "",
            "1. Calibration governance is active.",
            f"Calibration gate enabled for all regions: `{gate_all_enabled}` (threshold=`{_fmt(gate_threshold)}`)",
            "",
            "2. Out-of-time drift remains region-dependent.",
            f"- negative-ΔF1 regions: `{len(oot_negative_regions)}`",
        ]
    )
    for item in sorted(oot_negative_regions, key=lambda payload: payload["delta_f1"]):
        lines.append(
            f"- {item['region']}: model `{item['model_name']}`, ΔF1 `{item['delta_f1']:.4f}`, ΔECE `{item['delta_ece']:.4f}`"
        )

    lines.extend(
        [
            "",
            "3. Cross-region transfer still shows substantial degradation on multiple directions.",
            f"- negative transfer pairs: `{len(transfer_negative_pairs)}` / `{len(transfer_rows)}`",
        ]
    )
    for item in sorted(transfer_negative_pairs, key=lambda payload: payload["delta_f1"])[:6]:
        lines.append(
            f"- {item['source_region']} -> {item['target_region']}: `{item['model_name']}` ΔF1 `{item['delta_f1']:.4f}`"
        )

    lines.extend(
        [
            "",
            "4. Seed variance outliers are concentrated in neural/CNN candidates.",
            f"- high variance candidates (F1 std>=0.03): `{len(high_variance_candidates)}`",
        ]
    )
    for item in sorted(high_variance_candidates, key=lambda payload: payload["f1_std"], reverse=True)[:8]:
        lines.append(
            f"- {item['dataset']} / {item['model_name']}: F1 std `{item['f1_std']:.4f}`, ECE mean `{item['ece_mean']:.4f}`"
        )

    lines.extend(
        [
            "",
            "5. Error taxonomy indicates region-specific FN pressure that should be addressed in discussion.",
            "",
            "| Region | Positive Support (approx) | FP | FN |",
            "|---|---:|---:|---:|",
        ]
    )
    for region in sorted(set(list(positive_support_by_region.keys()) + list(fp_fn_by_region.keys()))):
        support = positive_support_by_region.get(region, 0)
        fp = fp_fn_by_region.get(region, {}).get("fp", 0)
        fn = fp_fn_by_region.get(region, {}).get("fn", 0)
        lines.append(f"| {region} | {support} | {fp} | {fn} |")

    if significance_rows:
        f1_ci_true = sum(1 for row in significance_rows if str(row.get("f1_rec_better_ci", "")).lower() == "true")
        ece_ci_true = sum(1 for row in significance_rows if str(row.get("ece_rec_lower_ci", "")).lower() == "true")
        lines.extend(
            [
                "",
                "## Significance Addendum",
                "",
                f"- source: `{significance_path_resolved}`",
                f"- datasets with `F1 rec>cmp (CI)=True`: `{f1_ci_true}/{len(significance_rows)}`",
                f"- datasets with `ECE rec<cmp (CI)=True`: `{ece_ci_true}/{len(significance_rows)}`",
            ]
        )
    if threshold_robustness_rows:
        nonzero_regret_profiles = [
            row for row in threshold_robustness_rows if (_safe_float(row.get("mean_regret")) or 0.0) > 0.0
        ]
        worst = sorted(
            nonzero_regret_profiles,
            key=lambda row: float(_safe_float(row.get("mean_regret")) or 0.0),
            reverse=True,
        )[:3]
        lines.extend(
            [
                "",
                "## Threshold-Robustness Addendum",
                "",
                f"- source: `{threshold_robustness_path_resolved}`",
                f"- non-zero regret profiles: `{len(nonzero_regret_profiles)}/{len(threshold_robustness_rows)}`",
            ]
        )
        for row in worst:
            lines.append(
                "- {dataset}/{profile}: mean_regret `{regret}` (mean_rec_th `{rec_th}` vs mean_best_th `{best_th}`)".format(
                    dataset=row.get("dataset", ""),
                    profile=row.get("profile", ""),
                    regret=_fmt(row.get("mean_regret"), digits=3),
                    rec_th=_fmt(row.get("mean_recommended_threshold")),
                    best_th=_fmt(row.get("mean_best_threshold")),
                )
            )

    lines.extend(
        [
            "",
            "## Priority TODO (Examiner View)",
            "",
            "1. Add true unseen-area evidence (outside current same-ecosystem region set).",
            (
                "2. Add threshold-policy robustness table under operator cost scenarios (FP-heavy vs FN-heavy)."
                if not threshold_robustness_rows
                else "2. Lock one operator cost profile per region and freeze threshold policy text in manuscript."
            ),
            (
                "3. Add significance notes for top-model deltas (bootstrap CI or paired test) in main table."
                if not significance_rows
                else "3. Integrate significance appendix link and one-line interpretation into main result table caption."
            ),
            "",
            "## Top-3 Models Per Dataset (10-seed aggregate)",
            "",
        ]
    )
    for dataset in sorted(top_models.keys()):
        lines.append(f"### {dataset}")
        lines.append("")
        lines.append("| Model | F1 mean±std (CI95) | ECE mean±std |")
        lines.append("|---|---:|---:|")
        for row in top_models[dataset]:
            lines.append(
                "| {model} | {f1m}±{f1s} ({f1ci}) | {ecem}±{eces} |".format(
                    model=row.get("model_name", ""),
                    f1m=_fmt(row.get("f1_mean")),
                    f1s=_fmt(row.get("f1_std")),
                    f1ci=_fmt(row.get("f1_ci95")),
                    ecem=_fmt(row.get("ece_mean")),
                    eces=_fmt(row.get("ece_std")),
                )
            )
        lines.append("")

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary
