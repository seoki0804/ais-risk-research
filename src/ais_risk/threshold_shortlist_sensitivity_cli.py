from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any

from .config import load_config
from .csv_tools import parse_timestamp
from .io import load_snapshot
from .models import ProjectConfig, ThresholdConfig
from .pipeline import run_snapshot


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def _parse_profile(raw: str) -> dict[str, object]:
    parts = [part.strip() for part in str(raw).split(":")]
    if len(parts) != 3:
        raise ValueError(f"Invalid --profile format: {raw}")
    return {
        "label": parts[0],
        "safe": float(parts[1]),
        "warning": float(parts[2]),
    }


def _collect_summary_paths(paths: list[str] | None, path_glob: str | None) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()
    for item in paths or []:
        normalized = str(item).strip()
        if not normalized or normalized in seen:
            continue
        collected.append(normalized)
        seen.add(normalized)
    if path_glob:
        for matched in sorted(Path(".").glob(path_glob)):
            normalized = str(matched)
            if normalized in seen:
                continue
            collected.append(normalized)
            seen.add(normalized)
    return collected


def _clone_config(config: ProjectConfig, safe: float, warning: float) -> ProjectConfig:
    return replace(
        config,
        thresholds=ThresholdConfig(
            safe=safe,
            warning=warning,
            density_radius_nm=config.thresholds.density_radius_nm,
            density_reference_count=config.thresholds.density_reference_count,
        ),
    )


def _extract_region(run_label: str) -> str:
    token = str(run_label).split("_", 1)[0].strip().lower()
    if token == "nola":
        return "nola"
    if token == "houston":
        return "houston"
    if token == "seattle":
        return "seattle"
    return token or "unknown"


def _extract_scenario_metrics(result, scenario_name: str) -> dict[str, object]:
    for scenario in result.scenarios:
        if scenario.summary.scenario_name == scenario_name:
            summary = scenario.summary
            return {
                "max_risk": float(summary.max_risk),
                "mean_risk": float(summary.mean_risk),
                "warning_area_nm2": float(summary.warning_area_nm2),
                "caution_area_nm2": float(summary.caution_area_nm2),
                "dominant_sector": str(summary.dominant_sector),
                "target_count": int(summary.target_count),
            }
    raise ValueError(f"Scenario {scenario_name} not found in result.")


def _write_csv(path_value: str | Path, rows: list[dict[str, Any]], columns: list[str]) -> str:
    destination = Path(path_value)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) for column in columns})
    return str(destination)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _build_aggregate_rows(case_rows: list[dict[str, Any]], default_profile: str) -> list[dict[str, Any]]:
    bucket: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        bucket[(str(row["region"]), str(row["profile_label"]))].append(row)
        bucket[("overall", str(row["profile_label"]))].append(row)

    aggregate_rows: list[dict[str, Any]] = []
    for (region, profile_label), rows in sorted(bucket.items()):
        warning_deltas = [float(row["warning_area_delta_vs_default"]) for row in rows]
        caution_deltas = [float(row["caution_area_delta_vs_default"]) for row in rows]
        max_risk_deltas = [float(row["max_risk_delta_vs_default"]) for row in rows]
        mean_risk_deltas = [float(row["mean_risk_delta_vs_default"]) for row in rows]
        sector_change_count = sum(1 for row in rows if bool(row["sector_changed_vs_default"]))
        warning_nonzero_count = sum(1 for row in rows if float(row["warning_area_nm2"]) > 0.0)
        warning_increase_count = sum(1 for row in rows if float(row["warning_area_delta_vs_default"]) > 0.0)
        caution_decrease_count = sum(1 for row in rows if float(row["caution_area_delta_vs_default"]) < 0.0)
        aggregate_rows.append(
            {
                "region": region,
                "profile_label": profile_label,
                "case_count": len(rows),
                "avg_warning_area_nm2": _mean([float(row["warning_area_nm2"]) for row in rows]),
                "avg_caution_area_nm2": _mean([float(row["caution_area_nm2"]) for row in rows]),
                "avg_max_risk": _mean([float(row["max_risk"]) for row in rows]),
                "avg_mean_risk": _mean([float(row["mean_risk"]) for row in rows]),
                "avg_warning_area_delta_vs_default": _mean(warning_deltas),
                "avg_caution_area_delta_vs_default": _mean(caution_deltas),
                "avg_max_risk_delta_vs_default": _mean(max_risk_deltas),
                "avg_mean_risk_delta_vs_default": _mean(mean_risk_deltas),
                "sector_change_count_vs_default": sector_change_count,
                "sector_change_ratio_vs_default": float(sector_change_count / len(rows)) if rows else None,
                "warning_nonzero_count": warning_nonzero_count,
                "warning_nonzero_ratio": float(warning_nonzero_count / len(rows)) if rows else None,
                "warning_increase_count_vs_default": warning_increase_count,
                "warning_increase_ratio_vs_default": float(warning_increase_count / len(rows)) if rows else None,
                "caution_decrease_count_vs_default": caution_decrease_count,
                "caution_decrease_ratio_vs_default": float(caution_decrease_count / len(rows)) if rows else None,
                "is_default_profile": profile_label == default_profile,
            }
        )
    return aggregate_rows


def _selection_sort_key(sample: dict[str, Any]) -> tuple[int, int, str]:
    return (
        int(sample.get("selected_rank", 9999) or 9999),
        int(sample.get("candidate_rank", 9999) or 9999),
        str(sample.get("timestamp", "")),
    )


def _select_samples_for_run(
    samples: list[dict[str, Any]],
    max_cases_per_run: int,
    selection_mode: str,
    time_window_hours: float,
) -> list[dict[str, Any]]:
    completed = [sample for sample in samples if str(sample.get("status")) == "completed"]
    completed.sort(key=_selection_sort_key)
    limit = max(1, int(max_cases_per_run))
    if selection_mode == "selected_rank":
        return completed[:limit]

    window_seconds = max(1.0, float(time_window_hours) * 3600.0)
    chosen_by_window: dict[tuple[str, int], dict[str, Any]] = {}
    for sample in completed:
        timestamp = parse_timestamp(str(sample.get("timestamp", "")))
        midnight = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        bucket_index = int((timestamp - midnight).total_seconds() // window_seconds)
        key = (timestamp.date().isoformat(), bucket_index)
        existing = chosen_by_window.get(key)
        if existing is None or _selection_sort_key(sample) < _selection_sort_key(existing):
            chosen_by_window[key] = sample

    selected = sorted(
        chosen_by_window.values(),
        key=lambda sample: (
            parse_timestamp(str(sample.get("timestamp", ""))),
            _selection_sort_key(sample),
        ),
    )
    return selected[:limit]


def _build_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Threshold Shortlist Sensitivity Aggregate",
        "",
        "## 1) 목적",
        "- [확정] shortlisted threshold profile의 spatial sensitivity를 대표 case 수준이 아니라 다중 holdout case 통계로 확장.",
        "- [확정] default/sensitive/tight profile 역할이 지역별로도 유지되는지 확인.",
        "",
        "## 2) 설정",
        f"- summary source count: `{summary.get('summary_source_count', 0)}`",
        f"- max cases per run: `{summary.get('max_cases_per_run', 0)}`",
        f"- selection mode: `{summary.get('selection_mode', 'selected_rank')}`",
        f"- time window hours: `{summary.get('time_window_hours', 'n/a')}`",
        f"- scenario name: `{summary.get('scenario_name', 'n/a')}`",
        f"- default profile: `{summary.get('default_profile', 'n/a')}`",
        "",
        "## 3) profile",
    ]
    for profile in summary.get("profiles", []):
        lines.append(
            f"- [확정] `{profile['label']}`: safe `{float(profile['safe']):.2f}`, warning `{float(profile['warning']):.2f}`"
        )

    lines.extend(
        [
            "",
            "## 4) 지역별 집계",
        ]
    )
    for region in ("houston", "nola", "seattle", "overall"):
        region_rows = [row for row in summary.get("aggregate_rows", []) if row.get("region") == region]
        if not region_rows:
            continue
        lines.extend(
            [
                "",
                f"### {region}",
                "",
                "| profile | case_count | avg warning area | avg caution area | avg warning delta vs default | avg caution delta vs default | sector change ratio | warning increase ratio | caution decrease ratio |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in region_rows:
            lines.append(
                f"| {row['profile_label']} | {int(row['case_count'])} | {float(row['avg_warning_area_nm2'] or 0.0):.4f} | "
                f"{float(row['avg_caution_area_nm2'] or 0.0):.4f} | {float(row['avg_warning_area_delta_vs_default'] or 0.0):.4f} | "
                f"{float(row['avg_caution_area_delta_vs_default'] or 0.0):.4f} | {float(row['sector_change_ratio_vs_default'] or 0.0):.4f} | "
                f"{float(row['warning_increase_ratio_vs_default'] or 0.0):.4f} | {float(row['caution_decrease_ratio_vs_default'] or 0.0):.4f} |"
            )

    lines.extend(
        [
            "",
            "## 5) 해석",
            "- [확정] `sensitive` profile은 default 대비 warning area를 늘리는 방향으로 작동하는지 확인한다.",
            "- [확정] `tight` profile은 default 대비 caution area를 줄이는 방향으로 작동하는지 확인한다.",
            "- [리스크] 본 통계는 AIS-only selected snapshot 기반이며, 법적 안전 경계 검증이 아니다.",
            "",
            "## 6) 다음 액션",
            "- [추가 검증 필요] `max_cases_per_run=2/3`으로 확장해 sensitivity 통계가 유지되는지 확인.",
            "- [추가 검증 필요] `2023-10` NOAA 또는 다른 NOAA 해역으로 같은 sensitivity 역할 구조가 유지되는지 점검.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate threshold shortlist spatial sensitivity across multiple scenario-shift summaries.")
    parser.add_argument("--config", default="configs/base.toml", help="Path to base config TOML.")
    parser.add_argument("--summary-json", action="append", help="Path to scenario_shift_multi summary JSON. Repeatable.")
    parser.add_argument("--summary-json-glob", help="Optional glob for scenario_shift_multi summary JSON files.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for aggregate artifacts.")
    parser.add_argument("--profile", action="append", required=True, help="Profile in label:safe:warning format. Repeatable.")
    parser.add_argument("--default-profile", required=True, help="Profile label used as delta baseline.")
    parser.add_argument("--scenario-name", default="current", help="Scenario name to compare. Default: current.")
    parser.add_argument("--max-cases-per-run", type=int, default=1, help="Use up to this many selected samples per run.")
    parser.add_argument(
        "--selection-mode",
        choices=("selected_rank", "time_window"),
        default="selected_rank",
        help="How to choose samples per run before aggregation.",
    )
    parser.add_argument(
        "--time-window-hours",
        type=float,
        default=6.0,
        help="Window size in hours when --selection-mode=time_window.",
    )
    args = parser.parse_args()

    summary_paths = _collect_summary_paths(args.summary_json, args.summary_json_glob)
    if not summary_paths:
        raise ValueError("No summary JSON paths resolved.")

    profiles = [_parse_profile(item) for item in args.profile]
    profile_map = {str(profile["label"]): profile for profile in profiles}
    if args.default_profile not in profile_map:
        raise ValueError(f"--default-profile must be one of {[profile['label'] for profile in profiles]}")

    config = load_config(args.config)
    case_rows: list[dict[str, Any]] = []
    case_counter = 0

    for summary_path in summary_paths:
        payload = json.loads(Path(summary_path).read_text(encoding="utf-8"))
        for run in payload.get("runs", []):
            run_label = str(run.get("label", "unknown"))
            region = _extract_region(run_label)
            selected_samples = _select_samples_for_run(
                samples=list(run.get("samples", [])),
                max_cases_per_run=max(1, int(args.max_cases_per_run)),
                selection_mode=str(args.selection_mode),
                time_window_hours=float(args.time_window_hours),
            )
            for sample in selected_samples:
                snapshot = load_snapshot(str(sample["snapshot_json"]))
                per_profile: dict[str, dict[str, object]] = {}
                for profile in profiles:
                    profile_label = str(profile["label"])
                    profile_config = _clone_config(config, safe=float(profile["safe"]), warning=float(profile["warning"]))
                    result = run_snapshot(snapshot=snapshot, config=profile_config)
                    per_profile[profile_label] = _extract_scenario_metrics(result=result, scenario_name=args.scenario_name)

                baseline = per_profile[args.default_profile]
                for profile in profiles:
                    profile_label = str(profile["label"])
                    metrics = per_profile[profile_label]
                    case_counter += 1
                    case_rows.append(
                        {
                            "source_summary_path": str(summary_path),
                            "run_label": run_label,
                            "region": region,
                            "selected_rank": int(sample.get("selected_rank", 0) or 0),
                            "candidate_rank": int(sample.get("candidate_rank", 0) or 0),
                            "snapshot_json": str(sample["snapshot_json"]),
                            "timestamp": str(sample.get("timestamp", snapshot.timestamp)),
                            "own_mmsi": str(sample.get("own_mmsi", snapshot.own_ship.mmsi)),
                            "snapshot_target_count": len(snapshot.targets),
                            "profile_label": profile_label,
                            "safe_threshold": float(profile["safe"]),
                            "warning_threshold": float(profile["warning"]),
                            "max_risk": float(metrics["max_risk"]),
                            "mean_risk": float(metrics["mean_risk"]),
                            "warning_area_nm2": float(metrics["warning_area_nm2"]),
                            "caution_area_nm2": float(metrics["caution_area_nm2"]),
                            "dominant_sector": str(metrics["dominant_sector"]),
                            "max_risk_delta_vs_default": float(metrics["max_risk"]) - float(baseline["max_risk"]),
                            "mean_risk_delta_vs_default": float(metrics["mean_risk"]) - float(baseline["mean_risk"]),
                            "warning_area_delta_vs_default": float(metrics["warning_area_nm2"]) - float(baseline["warning_area_nm2"]),
                            "caution_area_delta_vs_default": float(metrics["caution_area_nm2"]) - float(baseline["caution_area_nm2"]),
                            "sector_changed_vs_default": str(metrics["dominant_sector"]) != str(baseline["dominant_sector"]),
                            "is_default_profile": profile_label == args.default_profile,
                        }
                    )

    aggregate_rows = _build_aggregate_rows(case_rows, default_profile=args.default_profile)
    prefix = Path(args.output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    case_rows_csv_path = prefix.with_name(f"{prefix.name}_case_rows.csv")
    aggregate_rows_csv_path = prefix.with_name(f"{prefix.name}_aggregate_rows.csv")

    summary = {
        "status": "completed",
        "config_path": str(args.config),
        "summary_source_count": len(summary_paths),
        "max_cases_per_run": int(args.max_cases_per_run),
        "selection_mode": str(args.selection_mode),
        "time_window_hours": float(args.time_window_hours),
        "scenario_name": args.scenario_name,
        "default_profile": args.default_profile,
        "profiles": profiles,
        "case_count": len(case_rows),
        "case_rows": case_rows,
        "aggregate_rows": aggregate_rows,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "case_rows_csv_path": str(case_rows_csv_path),
        "aggregate_rows_csv_path": str(aggregate_rows_csv_path),
    }

    _write_csv(
        case_rows_csv_path,
        case_rows,
        [
            "source_summary_path",
            "run_label",
            "region",
            "selected_rank",
            "candidate_rank",
            "snapshot_json",
            "timestamp",
            "own_mmsi",
            "snapshot_target_count",
            "profile_label",
            "safe_threshold",
            "warning_threshold",
            "max_risk",
            "mean_risk",
            "warning_area_nm2",
            "caution_area_nm2",
            "dominant_sector",
            "max_risk_delta_vs_default",
            "mean_risk_delta_vs_default",
            "warning_area_delta_vs_default",
            "caution_area_delta_vs_default",
            "sector_changed_vs_default",
            "is_default_profile",
        ],
    )
    _write_csv(
        aggregate_rows_csv_path,
        aggregate_rows,
        [
            "region",
            "profile_label",
            "case_count",
            "avg_warning_area_nm2",
            "avg_caution_area_nm2",
            "avg_max_risk",
            "avg_mean_risk",
            "avg_warning_area_delta_vs_default",
            "avg_caution_area_delta_vs_default",
            "avg_max_risk_delta_vs_default",
            "avg_mean_risk_delta_vs_default",
            "sector_change_count_vs_default",
            "sector_change_ratio_vs_default",
            "warning_nonzero_count",
            "warning_nonzero_ratio",
            "warning_increase_count_vs_default",
            "warning_increase_ratio_vs_default",
            "caution_decrease_count_vs_default",
            "caution_decrease_ratio_vs_default",
            "is_default_profile",
        ],
    )
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(_build_markdown(summary), encoding="utf-8")

    print(f"status={summary['status']}")
    print(f"summary_source_count={summary['summary_source_count']}")
    print(f"case_count={summary['case_count']}")
    print(f"summary_json={summary_json_path}")
    print(f"summary_md={summary_md_path}")


if __name__ == "__main__":
    main()
