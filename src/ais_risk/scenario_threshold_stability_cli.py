from __future__ import annotations

import argparse
from pathlib import Path

from .scenario_threshold_stability import build_scenario_threshold_stability_report


def _parse_summary_specs(entries: list[str] | None) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    for entry in entries or []:
        raw = str(entry).strip()
        if not raw:
            continue
        if "|" not in raw:
            raise ValueError(
                "Invalid --summary-spec format. Use 'label|summary_json_path'. "
                f"Received: {raw}"
            )
        label, summary_path = [item.strip() for item in raw.split("|", 1)]
        if not summary_path:
            raise ValueError(f"summary_json_path is empty in --summary-spec: {raw}")
        specs.append({"label": label, "summary_path": summary_path})
    return specs


def _infer_label(path_value: str) -> str:
    stem = Path(path_value).stem
    if stem.endswith("_summary"):
        stem = stem[: -len("_summary")]
    return stem or "unknown"


def _collect_summary_specs(
    summary_specs: list[str] | None,
    summary_json_paths: list[str] | None,
    summary_globs: list[str] | None,
) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    specs.extend(_parse_summary_specs(summary_specs))

    for path_value in summary_json_paths or []:
        raw = str(path_value).strip()
        if not raw:
            continue
        specs.append({"label": _infer_label(raw), "summary_path": raw})

    for pattern in summary_globs or []:
        raw = str(pattern).strip()
        if not raw:
            continue
        for resolved in sorted(Path().glob(raw)):
            if resolved.is_file():
                specs.append({"label": _infer_label(str(resolved)), "summary_path": str(resolved)})

    deduped: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    for item in specs:
        path_value = str(item.get("summary_path") or "").strip()
        if not path_value or path_value in seen_paths:
            continue
        seen_paths.add(path_value)
        deduped.append(
            {
                "label": str(item.get("label") or _infer_label(path_value)),
                "summary_path": path_value,
            }
        )
    return deduped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate multiple scenario threshold tuning summaries and evaluate cross-run stability."
    )
    parser.add_argument(
        "--summary-spec",
        action="append",
        help="Summary spec formatted as 'label|summary_json_path'. Repeat for multiple entries.",
    )
    parser.add_argument(
        "--summary-json",
        action="append",
        help="Path to scenario_threshold_tuning summary JSON. Label is inferred from file name.",
    )
    parser.add_argument(
        "--summary-glob",
        action="append",
        help="Glob pattern to collect summary JSON files (for example: outputs/**/*scenario_threshold_tuning*_summary.json).",
    )
    parser.add_argument("--output-prefix", required=True, help="Output prefix for stability summary artifacts.")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K profiles used per run for overlap calculation.")
    parser.add_argument("--shortlist-size", type=int, default=3, help="Top-N shortlist size for robust profile candidates.")
    parser.add_argument(
        "--stable-recommendation-ratio-threshold",
        type=float,
        default=0.70,
        help="Minimum majority ratio for recommended profile stability.",
    )
    parser.add_argument(
        "--stable-topk-jaccard-threshold",
        type=float,
        default=0.50,
        help="Minimum mean top-k Jaccard overlap threshold.",
    )
    parser.add_argument(
        "--stable-bootstrap-frequency-threshold",
        type=float,
        default=0.30,
        help="Minimum mean recommended bootstrap top-1 frequency threshold.",
    )
    args = parser.parse_args()

    specs = _collect_summary_specs(
        summary_specs=args.summary_spec,
        summary_json_paths=args.summary_json,
        summary_globs=args.summary_glob,
    )
    if not specs:
        raise ValueError("At least one summary must be provided via --summary-spec, --summary-json, or --summary-glob.")

    summary = build_scenario_threshold_stability_report(
        summary_specs=specs,
        output_prefix=args.output_prefix,
        top_k=max(1, int(args.top_k)),
        shortlist_size=max(1, int(args.shortlist_size)),
        stable_recommendation_ratio_threshold=float(args.stable_recommendation_ratio_threshold),
        stable_topk_jaccard_threshold=float(args.stable_topk_jaccard_threshold),
        stable_bootstrap_frequency_threshold=float(args.stable_bootstrap_frequency_threshold),
    )
    print(f"status={summary['status']}")
    print(f"source_count={summary['source_count']}")
    print(f"stability_status={summary['stability_status']}")
    print(f"recommendation_majority_profile={summary.get('recommendation_majority_profile', '')}")
    print(f"recommendation_majority_ratio={summary.get('recommendation_majority_ratio')}")
    print(f"mean_topk_jaccard={summary.get('mean_topk_jaccard')}")
    print(f"mean_recommended_bootstrap_top1_frequency={summary.get('mean_recommended_bootstrap_top1_frequency')}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"run_rows_csv={summary['run_rows_csv_path']}")
    print(f"profile_rows_csv={summary['profile_rows_csv_path']}")


if __name__ == "__main__":
    main()

