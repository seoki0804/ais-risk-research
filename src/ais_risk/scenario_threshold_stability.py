from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def _jaccard(left: set[str], right: set[str]) -> float | None:
    union = left | right
    if not union:
        return None
    intersection = left & right
    return float(len(intersection)) / float(len(union))


def _infer_label(path_value: str | Path) -> str:
    stem = Path(path_value).stem
    if stem.endswith("_summary"):
        stem = stem[: -len("_summary")]
    return stem or "unknown"


def _read_json(path_value: str | Path) -> dict[str, Any]:
    return json.loads(Path(path_value).read_text(encoding="utf-8"))


def _extract_top_profiles(payload: dict[str, Any], top_k: int) -> list[str]:
    rows = list(payload.get("top_rows") or payload.get("rows") or [])
    profiles: list[str] = []
    seen: set[str] = set()
    for row in rows:
        profile_name = str(row.get("profile_name") or "").strip()
        if not profile_name or profile_name in seen:
            continue
        profiles.append(profile_name)
        seen.add(profile_name)
        if len(profiles) >= max(1, int(top_k)):
            break
    return profiles


def _write_csv(path_value: str | Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    destination = Path(path_value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})
    return str(destination)


def build_scenario_threshold_stability_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Scenario Threshold Stability Summary",
        "",
        f"- source_count: `{summary.get('source_count', 0)}`",
        f"- top_k: `{summary.get('top_k', 0)}`",
        f"- shortlist_size: `{summary.get('shortlist_size', 0)}`",
        f"- stability_status: `{summary.get('stability_status', '')}`",
        "",
        "## Stability Signals",
        "",
        f"- recommendation_majority_profile: `{summary.get('recommendation_majority_profile', '')}`",
        f"- recommendation_majority_ratio: `{_fmt(summary.get('recommendation_majority_ratio'))}`",
        f"- consensus_majority_profile: `{summary.get('consensus_majority_profile', '')}`",
        f"- consensus_majority_ratio: `{_fmt(summary.get('consensus_majority_ratio'))}`",
        f"- mean_topk_jaccard: `{_fmt(summary.get('mean_topk_jaccard'))}`",
        f"- min_topk_jaccard: `{_fmt(summary.get('min_topk_jaccard'))}`",
        f"- max_topk_jaccard: `{_fmt(summary.get('max_topk_jaccard'))}`",
        f"- mean_recommended_bootstrap_top1_frequency: `{_fmt(summary.get('mean_recommended_bootstrap_top1_frequency'))}`",
        "",
        "## Run-Level View",
        "",
        "| label | recommended_profile | recommended_bootstrap_top1 | consensus_profile | consensus_freq | top_k_profiles |",
        "|---|---|---:|---|---:|---|",
    ]
    for row in summary.get("runs", []):
        lines.append(
            "| {label} | {recommended} | {boot} | {consensus} | {consensus_freq} | {top_profiles} |".format(
                label=row.get("label", ""),
                recommended=row.get("recommended_profile_name", ""),
                boot=_fmt(row.get("recommended_bootstrap_top1_frequency")),
                consensus=row.get("bootstrap_consensus_profile_name", ""),
                consensus_freq=_fmt(row.get("bootstrap_consensus_profile_frequency")),
                top_profiles=", ".join(row.get("top_profiles", [])),
            )
        )
    lines.extend(
        [
            "",
            "## Profile Aggregate",
            "",
            "| rank | profile | recommended_count | consensus_count | topk_count | mean_rank | mean_objective | mean_bootstrap_top1 | safe_mean | warning_mean |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary.get("profile_rows", []):
        lines.append(
            "| {rank} | {profile} | {recommended_count} | {consensus_count} | {topk_count} | {mean_rank} | {mean_objective} | {mean_boot} | {safe_mean} | {warning_mean} |".format(
                rank=row.get("rank", ""),
                profile=row.get("profile_name", ""),
                recommended_count=row.get("recommended_count", 0),
                consensus_count=row.get("consensus_count", 0),
                topk_count=row.get("topk_count", 0),
                mean_rank=_fmt(row.get("mean_rank")),
                mean_objective=_fmt(row.get("mean_objective_score")),
                mean_boot=_fmt(row.get("mean_bootstrap_top1_frequency")),
                safe_mean=_fmt(row.get("safe_threshold_mean")),
                warning_mean=_fmt(row.get("warning_threshold_mean")),
            )
        )
    lines.extend(
        [
            "",
            "## Shortlist",
            "",
            "| rank | profile | recommended_count | topk_count | mean_rank | mean_objective |",
            "|---:|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary.get("shortlist", []):
        lines.append(
            "| {rank} | {profile} | {recommended_count} | {topk_count} | {mean_rank} | {mean_objective} |".format(
                rank=row.get("rank", ""),
                profile=row.get("profile_name", ""),
                recommended_count=row.get("recommended_count", 0),
                topk_count=row.get("topk_count", 0),
                mean_rank=_fmt(row.get("mean_rank")),
                mean_objective=_fmt(row.get("mean_objective_score")),
            )
        )
    lines.append("")
    return "\n".join(lines)


def build_scenario_threshold_stability_report(
    summary_specs: list[dict[str, str]],
    output_prefix: str | Path,
    top_k: int = 5,
    shortlist_size: int = 3,
    stable_recommendation_ratio_threshold: float = 0.70,
    stable_topk_jaccard_threshold: float = 0.50,
    stable_bootstrap_frequency_threshold: float = 0.30,
) -> dict[str, Any]:
    if not summary_specs:
        raise ValueError("summary_specs must not be empty.")

    runs: list[dict[str, Any]] = []
    recommended_counter: Counter[str] = Counter()
    consensus_counter: Counter[str] = Counter()
    topk_sets: list[set[str]] = []
    recommended_bootstrap_values: list[float] = []

    profile_bucket: dict[str, dict[str, Any]] = {}

    for item in summary_specs:
        label = str(item.get("label") or "").strip()
        summary_path = str(item.get("summary_path") or "").strip()
        if not summary_path:
            continue
        if not label:
            label = _infer_label(summary_path)
        payload = _read_json(summary_path)

        recommended_profile_name = str(payload.get("recommended_profile_name") or "").strip()
        recommended_bootstrap_top1_frequency = _safe_float(payload.get("recommended_bootstrap_top1_frequency"))
        bootstrap_consensus_profile_name = str(payload.get("bootstrap_consensus_profile_name") or "").strip()
        bootstrap_consensus_profile_frequency = _safe_float(payload.get("bootstrap_consensus_profile_frequency"))
        top_profiles = _extract_top_profiles(payload, top_k=max(1, int(top_k)))
        top_profiles_set = set(top_profiles)

        if recommended_profile_name:
            recommended_counter.update([recommended_profile_name])
        if bootstrap_consensus_profile_name:
            consensus_counter.update([bootstrap_consensus_profile_name])
        if recommended_bootstrap_top1_frequency is not None:
            recommended_bootstrap_values.append(float(recommended_bootstrap_top1_frequency))
        topk_sets.append(top_profiles_set)

        run_row = {
            "label": label,
            "summary_path": summary_path,
            "scenario_shift_summary_path": str(payload.get("scenario_shift_summary_path") or ""),
            "recommended_profile_name": recommended_profile_name,
            "recommended_safe_threshold": _safe_float(payload.get("recommended_safe_threshold")),
            "recommended_warning_threshold": _safe_float(payload.get("recommended_warning_threshold")),
            "recommended_objective_score": _safe_float(payload.get("recommended_objective_score")),
            "recommended_bootstrap_top1_frequency": recommended_bootstrap_top1_frequency,
            "bootstrap_consensus_profile_name": bootstrap_consensus_profile_name,
            "bootstrap_consensus_profile_frequency": bootstrap_consensus_profile_frequency,
            "top_profiles": top_profiles,
        }
        runs.append(run_row)

        for row in list(payload.get("rows") or []):
            profile_name = str(row.get("profile_name") or "").strip()
            if not profile_name:
                continue
            bucket = profile_bucket.get(profile_name)
            if bucket is None:
                bucket = {
                    "profile_name": profile_name,
                    "appearance_count": 0,
                    "topk_count": 0,
                    "recommended_count": 0,
                    "consensus_count": 0,
                    "ranks": [],
                    "objective_scores": [],
                    "bootstrap_top1_frequencies": [],
                    "safe_thresholds": [],
                    "warning_thresholds": [],
                }
                profile_bucket[profile_name] = bucket
            bucket["appearance_count"] += 1
            rank_value = _safe_float(row.get("rank"))
            objective_value = _safe_float(row.get("objective_score"))
            boot_value = _safe_float(row.get("bootstrap_top1_frequency"))
            safe_value = _safe_float(row.get("safe_threshold"))
            warning_value = _safe_float(row.get("warning_threshold"))
            if rank_value is not None:
                bucket["ranks"].append(float(rank_value))
            if objective_value is not None:
                bucket["objective_scores"].append(float(objective_value))
            if boot_value is not None:
                bucket["bootstrap_top1_frequencies"].append(float(boot_value))
            if safe_value is not None:
                bucket["safe_thresholds"].append(float(safe_value))
            if warning_value is not None:
                bucket["warning_thresholds"].append(float(warning_value))
            if profile_name in top_profiles_set:
                bucket["topk_count"] += 1
            if profile_name == recommended_profile_name:
                bucket["recommended_count"] += 1
            if profile_name == bootstrap_consensus_profile_name:
                bucket["consensus_count"] += 1

    if not runs:
        raise ValueError("No valid summary specs resolved.")

    source_count = len(runs)
    jaccards: list[float] = []
    for left_idx in range(len(topk_sets)):
        for right_idx in range(left_idx + 1, len(topk_sets)):
            value = _jaccard(topk_sets[left_idx], topk_sets[right_idx])
            if value is not None:
                jaccards.append(float(value))

    recommendation_majority_profile = ""
    recommendation_majority_ratio = None
    if recommended_counter:
        top_profile, top_count = recommended_counter.most_common(1)[0]
        recommendation_majority_profile = top_profile
        recommendation_majority_ratio = float(top_count) / float(source_count)

    consensus_majority_profile = ""
    consensus_majority_ratio = None
    if consensus_counter:
        top_profile, top_count = consensus_counter.most_common(1)[0]
        consensus_majority_profile = top_profile
        consensus_majority_ratio = float(top_count) / float(source_count)

    mean_topk_jaccard = _mean(jaccards)
    min_topk_jaccard = min(jaccards) if jaccards else None
    max_topk_jaccard = max(jaccards) if jaccards else None
    mean_recommended_bootstrap_top1_frequency = _mean(recommended_bootstrap_values)

    if source_count < 2:
        stability_status = "insufficient_runs"
    else:
        stable = (
            (recommendation_majority_ratio is not None and recommendation_majority_ratio >= float(stable_recommendation_ratio_threshold))
            and (mean_topk_jaccard is not None and mean_topk_jaccard >= float(stable_topk_jaccard_threshold))
            and (
                mean_recommended_bootstrap_top1_frequency is not None
                and mean_recommended_bootstrap_top1_frequency >= float(stable_bootstrap_frequency_threshold)
            )
        )
        stability_status = "stable" if stable else "unstable"

    profile_rows: list[dict[str, Any]] = []
    for profile_name, bucket in profile_bucket.items():
        mean_rank = _mean(list(bucket["ranks"]))
        mean_objective = _mean(list(bucket["objective_scores"]))
        mean_bootstrap = _mean(list(bucket["bootstrap_top1_frequencies"]))
        safe_mean = _mean(list(bucket["safe_thresholds"]))
        warning_mean = _mean(list(bucket["warning_thresholds"]))

        row = {
            "profile_name": profile_name,
            "appearance_count": int(bucket["appearance_count"]),
            "appearance_ratio": float(bucket["appearance_count"]) / float(source_count),
            "recommended_count": int(bucket["recommended_count"]),
            "consensus_count": int(bucket["consensus_count"]),
            "topk_count": int(bucket["topk_count"]),
            "topk_ratio": float(bucket["topk_count"]) / float(source_count),
            "mean_rank": mean_rank,
            "mean_objective_score": mean_objective,
            "mean_bootstrap_top1_frequency": mean_bootstrap,
            "safe_threshold_mean": safe_mean,
            "warning_threshold_mean": warning_mean,
        }
        profile_rows.append(row)

    profile_rows.sort(
        key=lambda row: (
            -int(row.get("recommended_count", 0)),
            -int(row.get("consensus_count", 0)),
            -int(row.get("topk_count", 0)),
            float(row.get("mean_rank") or 1e9),
            float(row.get("mean_objective_score") or 1e9),
            str(row.get("profile_name", "")),
        )
    )
    for index, row in enumerate(profile_rows, start=1):
        row["rank"] = index

    shortlist = profile_rows[: max(1, int(shortlist_size))]

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    run_rows_csv_path = prefix.with_name(f"{prefix.name}_run_rows.csv")
    profile_rows_csv_path = prefix.with_name(f"{prefix.name}_profile_rows.csv")

    run_rows_csv_written = _write_csv(
        run_rows_csv_path,
        runs,
        fieldnames=[
            "label",
            "summary_path",
            "scenario_shift_summary_path",
            "recommended_profile_name",
            "recommended_safe_threshold",
            "recommended_warning_threshold",
            "recommended_objective_score",
            "recommended_bootstrap_top1_frequency",
            "bootstrap_consensus_profile_name",
            "bootstrap_consensus_profile_frequency",
            "top_profiles",
        ],
    )
    profile_rows_csv_written = _write_csv(
        profile_rows_csv_path,
        profile_rows,
        fieldnames=[
            "rank",
            "profile_name",
            "appearance_count",
            "appearance_ratio",
            "recommended_count",
            "consensus_count",
            "topk_count",
            "topk_ratio",
            "mean_rank",
            "mean_objective_score",
            "mean_bootstrap_top1_frequency",
            "safe_threshold_mean",
            "warning_threshold_mean",
        ],
    )

    summary: dict[str, Any] = {
        "status": "completed",
        "source_count": source_count,
        "top_k": max(1, int(top_k)),
        "shortlist_size": max(1, int(shortlist_size)),
        "stable_recommendation_ratio_threshold": float(stable_recommendation_ratio_threshold),
        "stable_topk_jaccard_threshold": float(stable_topk_jaccard_threshold),
        "stable_bootstrap_frequency_threshold": float(stable_bootstrap_frequency_threshold),
        "stability_status": stability_status,
        "recommendation_majority_profile": recommendation_majority_profile,
        "recommendation_majority_ratio": recommendation_majority_ratio,
        "consensus_majority_profile": consensus_majority_profile,
        "consensus_majority_ratio": consensus_majority_ratio,
        "mean_topk_jaccard": mean_topk_jaccard,
        "min_topk_jaccard": min_topk_jaccard,
        "max_topk_jaccard": max_topk_jaccard,
        "mean_recommended_bootstrap_top1_frequency": mean_recommended_bootstrap_top1_frequency,
        "runs": runs,
        "profile_rows": profile_rows,
        "shortlist": shortlist,
        "run_rows_csv_path": run_rows_csv_written,
        "profile_rows_csv_path": profile_rows_csv_written,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_scenario_threshold_stability_markdown(summary), encoding="utf-8")
    return summary

