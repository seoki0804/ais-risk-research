from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


OPERATOR_LOCK_FIELDS = [
    "region",
    "dataset",
    "model_name",
    "locked_profile",
    "mean_regret",
    "mean_recommended_threshold",
    "mean_best_threshold",
    "selection_basis",
]

MODEL_CLAIM_SCOPE_FIELDS = [
    "region",
    "dataset",
    "model_name",
    "is_recommended",
    "f1_mean",
    "f1_std",
    "ece_mean",
    "variance_pass",
    "calibration_pass",
    "claim_scope",
    "risk_flags",
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


def _dataset_to_region(dataset: str) -> str:
    return str(dataset).replace("_pooled_pairwise", "")


def _profile_priority(name: str) -> int:
    order = {
        "balanced": 0,
        "fn_heavy": 1,
        "fn_very_heavy": 2,
        "fp_heavy": 3,
    }
    return order.get(str(name), 99)


def _risk_flags(ece_mean: float | None, f1_std: float | None, max_ece: float, max_f1_std: float) -> str:
    flags: list[str] = []
    if ece_mean is not None and ece_mean > float(max_ece):
        flags.append("ece_high")
    if f1_std is not None and f1_std > float(max_f1_std):
        flags.append("seed_variance_high")
    return ",".join(flags)


def _build_model_claim_scope_rows(
    recommendation_rows: list[dict[str, str]],
    aggregate_rows: list[dict[str, str]],
    max_ece: float,
    max_f1_std: float,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    recommendation_keys: dict[tuple[str, str], dict[str, str]] = {}
    for row in recommendation_rows:
        dataset = str(row.get("dataset", "")).strip()
        model_name = str(row.get("model_name", "")).strip()
        if dataset and model_name:
            recommendation_keys[(dataset, model_name)] = row

    scope_rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    recommended_model_count = 0
    recommended_stable_count = 0
    appendix_only_count = 0

    for row in aggregate_rows:
        dataset = str(row.get("dataset", "")).strip()
        model_name = str(row.get("model_name", "")).strip()
        if not dataset or not model_name:
            continue
        key = (dataset, model_name)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        ece_mean = _safe_float(row.get("ece_mean"))
        f1_std = _safe_float(row.get("f1_std"))
        f1_mean = _safe_float(row.get("f1_mean"))
        calibration_pass = ece_mean is not None and ece_mean <= float(max_ece)
        variance_pass = f1_std is not None and f1_std <= float(max_f1_std)
        is_recommended = key in recommendation_keys

        if is_recommended and calibration_pass and variance_pass:
            claim_scope = "main_text_allowed"
            recommended_stable_count += 1
        elif is_recommended:
            claim_scope = "main_text_blocked"
        elif calibration_pass and variance_pass:
            claim_scope = "appendix_optional"
        else:
            claim_scope = "appendix_only"
            appendix_only_count += 1

        if is_recommended:
            recommended_model_count += 1

        scope_rows.append(
            {
                "region": _dataset_to_region(dataset),
                "dataset": dataset,
                "model_name": model_name,
                "is_recommended": bool(is_recommended),
                "f1_mean": f1_mean,
                "f1_std": f1_std,
                "ece_mean": ece_mean,
                "variance_pass": bool(variance_pass),
                "calibration_pass": bool(calibration_pass),
                "claim_scope": claim_scope,
                "risk_flags": _risk_flags(
                    ece_mean=ece_mean,
                    f1_std=f1_std,
                    max_ece=float(max_ece),
                    max_f1_std=float(max_f1_std),
                ),
            }
        )

    for key, rec_row in recommendation_keys.items():
        if key in seen_keys:
            continue
        dataset, model_name = key
        ece_mean = _safe_float(rec_row.get("ece_mean"))
        f1_std = _safe_float(rec_row.get("f1_std"))
        f1_mean = _safe_float(rec_row.get("f1_mean"))
        calibration_pass = ece_mean is not None and ece_mean <= float(max_ece)
        variance_pass = f1_std is not None and f1_std <= float(max_f1_std)
        claim_scope = "main_text_allowed" if (calibration_pass and variance_pass) else "main_text_blocked"
        recommended_model_count += 1
        if claim_scope == "main_text_allowed":
            recommended_stable_count += 1
        scope_rows.append(
            {
                "region": _dataset_to_region(dataset),
                "dataset": dataset,
                "model_name": model_name,
                "is_recommended": True,
                "f1_mean": f1_mean,
                "f1_std": f1_std,
                "ece_mean": ece_mean,
                "variance_pass": bool(variance_pass),
                "calibration_pass": bool(calibration_pass),
                "claim_scope": claim_scope,
                "risk_flags": _risk_flags(
                    ece_mean=ece_mean,
                    f1_std=f1_std,
                    max_ece=float(max_ece),
                    max_f1_std=float(max_f1_std),
                ),
            }
        )

    scope_rows.sort(
        key=lambda row: (
            str(row.get("dataset", "")),
            0 if bool(row.get("is_recommended")) else 1,
            str(row.get("claim_scope", "")),
            str(row.get("model_name", "")),
        )
    )
    return scope_rows, {
        "recommended_model_count": int(recommended_model_count),
        "recommended_stable_count": int(recommended_stable_count),
        "appendix_only_count": int(appendix_only_count),
    }


def _select_operator_profile_locks(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        dataset = str(row.get("dataset", "")).strip()
        if dataset:
            grouped.setdefault(dataset, []).append(row)

    selected_rows: list[dict[str, Any]] = []
    for dataset in sorted(grouped.keys()):
        candidates: list[dict[str, Any]] = []
        for row in grouped[dataset]:
            mean_regret = _safe_float(row.get("mean_regret"))
            mean_rec_th = _safe_float(row.get("mean_recommended_threshold"))
            mean_best_th = _safe_float(row.get("mean_best_threshold"))
            if mean_regret is None:
                continue
            candidates.append(
                {
                    "raw": row,
                    "dataset": dataset,
                    "region": _dataset_to_region(dataset),
                    "model_name": str(row.get("model_name", "")),
                    "profile": str(row.get("profile", "")),
                    "mean_regret": float(mean_regret),
                    "mean_recommended_threshold": mean_rec_th,
                    "mean_best_threshold": mean_best_th,
                    "threshold_gap": abs((mean_rec_th or 0.0) - (mean_best_th or 0.0)),
                }
            )
        if not candidates:
            continue
        candidates.sort(
            key=lambda item: (
                item["mean_regret"],
                _profile_priority(item["profile"]),
                item["threshold_gap"],
                item["profile"],
            )
        )
        chosen = candidates[0]
        selection_basis = "minimum_mean_regret_then_profile_priority_then_threshold_gap"
        selected_rows.append(
            {
                "region": chosen["region"],
                "dataset": chosen["dataset"],
                "model_name": chosen["model_name"],
                "locked_profile": chosen["profile"],
                "mean_regret": chosen["mean_regret"],
                "mean_recommended_threshold": chosen["mean_recommended_threshold"],
                "mean_best_threshold": chosen["mean_best_threshold"],
                "selection_basis": selection_basis,
            }
        )
    return selected_rows


def run_manuscript_freeze_packet(
    unseen_area_summary_csv_path: str | Path,
    threshold_robustness_summary_csv_path: str | Path,
    significance_csv_path: str | Path,
    output_prefix: str | Path,
    min_test_positive_support: int = 10,
    recommendation_csv_path: str | Path | None = None,
    aggregate_csv_path: str | Path | None = None,
    max_ece: float = 0.10,
    max_f1_std: float = 0.03,
) -> dict[str, Any]:
    unseen_rows = _parse_csv_rows(unseen_area_summary_csv_path)
    threshold_rows = _parse_csv_rows(threshold_robustness_summary_csv_path)
    significance_rows = _parse_csv_rows(significance_csv_path)
    recommendation_rows: list[dict[str, str]] = []
    aggregate_rows: list[dict[str, str]] = []
    recommendation_path_resolved = Path(recommendation_csv_path).resolve() if recommendation_csv_path else None
    aggregate_path_resolved = Path(aggregate_csv_path).resolve() if aggregate_csv_path else None
    if recommendation_path_resolved and recommendation_path_resolved.exists():
        recommendation_rows = _parse_csv_rows(recommendation_path_resolved)
    if aggregate_path_resolved and aggregate_path_resolved.exists():
        aggregate_rows = _parse_csv_rows(aggregate_path_resolved)
    if not unseen_rows:
        raise ValueError("unseen area summary CSV has no rows")

    unseen = unseen_rows[0]
    supported_splits = int(_safe_float(unseen.get("true_area_supported_split_count")) or 0)
    total_splits = int(_safe_float(unseen.get("true_area_split_count")) or 0)
    low_support_count = int(_safe_float(unseen.get("true_area_low_support_count")) or 0)
    low_support_splits = str(unseen.get("low_support_region_splits", "")).strip() or "none"
    transfer_negative = int(_safe_float(unseen.get("transfer_negative_delta_count")) or 0)
    transfer_total = int(_safe_float(unseen.get("transfer_row_count")) or 0)
    transfer_regions = int(_safe_float(unseen.get("transfer_region_count")) or 0)

    f1_better_ci = sum(1 for row in significance_rows if str(row.get("f1_rec_better_ci", "")).lower() == "true")
    ece_better_ci = sum(1 for row in significance_rows if str(row.get("ece_rec_lower_ci", "")).lower() == "true")

    profile_locks = _select_operator_profile_locks(threshold_rows)
    profile_count = len(profile_locks)
    max_locked_regret = max([float(row["mean_regret"]) for row in profile_locks], default=0.0)

    unseen_claim_text = (
        "True unseen-area generalization claim is locked to support-governed evidence only: "
        f"{supported_splits}/{total_splits} evaluated splits satisfy the minimum support policy "
        f"(test positives >= {int(min_test_positive_support)}), with low-support count={low_support_count} "
        f"({low_support_splits})."
    )
    transfer_scope_text = (
        "Transfer-scope claim is bounded to the evaluated cross-year independent-harbor set: "
        f"coverage={transfer_regions} regions, negative-DeltaF1 pairs={transfer_negative}/{transfer_total}."
    )
    threshold_policy_text = (
        "Operator-threshold policy is locked per region by minimum mean regret over predefined cost profiles "
        "(balanced, fn_heavy, fn_very_heavy, fp_heavy). The selected profile and threshold statistics are frozen "
        "in the operator-profile lock table."
    )
    caption_addendum_text = (
        "Caption addendum: Recommended models show lower calibration error in "
        f"{ece_better_ci}/{len(significance_rows)} datasets and higher F1 with non-overlapping 95% CI in "
        f"{f1_better_ci}/{len(significance_rows)} datasets; see significance appendix "
        f"({Path(significance_csv_path).resolve()})."
    )

    output_root = Path(output_prefix).resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    summary_md_path = output_root.with_suffix(".md")
    summary_json_path = output_root.with_suffix(".json")
    operator_lock_csv_path = output_root.with_name(output_root.name + "_operator_profile_lock").with_suffix(".csv")
    model_claim_scope_csv_path = output_root.with_name(output_root.name + "_model_claim_scope").with_suffix(".csv")
    _write_csv(operator_lock_csv_path, profile_locks, OPERATOR_LOCK_FIELDS)

    model_claim_scope_rows: list[dict[str, Any]] = []
    model_claim_counts = {
        "recommended_model_count": 0,
        "recommended_stable_count": 0,
        "appendix_only_count": 0,
    }
    recommended_claim_hygiene_ready = False
    model_claim_caveat_text = ""
    if recommendation_rows and aggregate_rows:
        model_claim_scope_rows, model_claim_counts = _build_model_claim_scope_rows(
            recommendation_rows=recommendation_rows,
            aggregate_rows=aggregate_rows,
            max_ece=float(max_ece),
            max_f1_std=float(max_f1_std),
        )
        _write_csv(model_claim_scope_csv_path, model_claim_scope_rows, MODEL_CLAIM_SCOPE_FIELDS)
        recommended_claim_hygiene_ready = bool(
            model_claim_counts["recommended_model_count"] > 0
            and model_claim_counts["recommended_model_count"] == model_claim_counts["recommended_stable_count"]
        )
        model_claim_caveat_text = (
            "Reviewer caveat: Main-text model claims are restricted to recommended models that satisfy "
            f"calibration (ECE<={float(max_ece):.2f}) and seed-variance (F1 std<={float(max_f1_std):.2f}) gates; "
            "models failing either gate are retained in appendix-only ablation tables."
        )

    markdown_lines = [
        "# Manuscript Freeze Packet",
        "",
        "## Inputs",
        "",
        f"- unseen_area_summary_csv: `{Path(unseen_area_summary_csv_path).resolve()}`",
        f"- threshold_robustness_summary_csv: `{Path(threshold_robustness_summary_csv_path).resolve()}`",
        f"- significance_csv: `{Path(significance_csv_path).resolve()}`",
        (
            f"- recommendation_csv: `{recommendation_path_resolved}`"
            if recommendation_path_resolved
            else "- recommendation_csv: `(not provided)`"
        ),
        (
            f"- aggregate_csv: `{aggregate_path_resolved}`"
            if aggregate_path_resolved
            else "- aggregate_csv: `(not provided)`"
        ),
        "",
        "## Frozen Claim Text (Paste-Ready)",
        "",
        f"1. {unseen_claim_text}",
        f"2. {transfer_scope_text}",
        f"3. {threshold_policy_text}",
        "",
        "## Operator Profile Lock Table",
        "",
        "| Region | Dataset | Model | Locked Profile | Mean Regret | Mean Rec Th | Mean Best Th |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for row in profile_locks:
        markdown_lines.append(
            "| {region} | {dataset} | {model} | {profile} | {regret} | {rec_th} | {best_th} |".format(
                region=row["region"],
                dataset=row["dataset"],
                model=row["model_name"],
                profile=row["locked_profile"],
                regret=_fmt(row["mean_regret"], digits=3),
                rec_th=_fmt(row["mean_recommended_threshold"]),
                best_th=_fmt(row["mean_best_threshold"]),
            )
        )
    markdown_lines.extend(
        [
            "",
            "## Main Result Table Caption Addendum (Paste-Ready)",
            "",
            f"- {caption_addendum_text}",
            "",
        ]
    )
    if model_claim_scope_rows:
        markdown_lines.extend(
            [
                "## Model-Claim Hygiene Freeze",
                "",
                (
                    f"- recommended stable claims: "
                    f"`{model_claim_counts['recommended_stable_count']}/{model_claim_counts['recommended_model_count']}`"
                ),
                f"- appendix-only model rows: `{model_claim_counts['appendix_only_count']}`",
                f"- recommended_claim_hygiene_ready: `{recommended_claim_hygiene_ready}`",
                f"- caveat sentence: {model_claim_caveat_text}",
                f"- model_claim_scope_csv: `{model_claim_scope_csv_path}`",
                "",
            ]
        )
    markdown_lines.extend(
        [
            "## Outputs",
            "",
            f"- summary_md: `{summary_md_path}`",
            f"- summary_json: `{summary_json_path}`",
            f"- operator_profile_lock_csv: `{operator_lock_csv_path}`",
            (
                f"- model_claim_scope_csv: `{model_claim_scope_csv_path}`"
                if model_claim_scope_rows
                else "- model_claim_scope_csv: `(not generated)`"
            ),
            "",
        ]
    )
    summary_md_path.write_text("\n".join(markdown_lines), encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "completed",
        "unseen_area_summary_csv_path": str(Path(unseen_area_summary_csv_path).resolve()),
        "threshold_robustness_summary_csv_path": str(Path(threshold_robustness_summary_csv_path).resolve()),
        "significance_csv_path": str(Path(significance_csv_path).resolve()),
        "recommendation_csv_path": str(recommendation_path_resolved) if recommendation_path_resolved else "",
        "aggregate_csv_path": str(aggregate_path_resolved) if aggregate_path_resolved else "",
        "max_ece": float(max_ece),
        "max_f1_std": float(max_f1_std),
        "min_test_positive_support": int(min_test_positive_support),
        "supported_split_count": supported_splits,
        "total_split_count": total_splits,
        "low_support_count": low_support_count,
        "low_support_splits": low_support_splits,
        "transfer_negative_count": transfer_negative,
        "transfer_total_count": transfer_total,
        "transfer_region_count": transfer_regions,
        "f1_better_ci_count": f1_better_ci,
        "ece_better_ci_count": ece_better_ci,
        "significance_row_count": len(significance_rows),
        "profile_lock_count": profile_count,
        "max_locked_mean_regret": max_locked_regret,
        "unseen_claim_text": unseen_claim_text,
        "transfer_scope_text": transfer_scope_text,
        "threshold_policy_text": threshold_policy_text,
        "caption_addendum_text": caption_addendum_text,
        "recommended_model_count": int(model_claim_counts["recommended_model_count"]),
        "recommended_stable_count": int(model_claim_counts["recommended_stable_count"]),
        "appendix_only_count": int(model_claim_counts["appendix_only_count"]),
        "recommended_claim_hygiene_ready": bool(recommended_claim_hygiene_ready),
        "model_claim_caveat_text": model_claim_caveat_text,
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
        "operator_profile_lock_csv_path": str(operator_lock_csv_path),
        "model_claim_scope_csv_path": str(model_claim_scope_csv_path) if model_claim_scope_rows else "",
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
