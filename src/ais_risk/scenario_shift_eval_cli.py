from __future__ import annotations

import argparse

from .scenario_shift_eval import run_scenario_shift_multi_snapshot


def _parse_run_specs(entries: list[str] | None) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    for entry in entries or []:
        raw = str(entry).strip()
        if not raw:
            continue
        chunks = [part.strip() for part in raw.split("|")]
        if len(chunks) != 3:
            raise ValueError(
                "Invalid --run format. Use 'label|pairwise_path|curated_path'. "
                f"Received: {raw}"
            )
        label, pairwise_path, curated_path = chunks
        specs.append(
            {
                "label": label,
                "pairwise_path": pairwise_path,
                "curated_path": curated_path,
            }
        )
    return specs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate slowdown/current/speedup scenario shift on multiple own-ship snapshots per run."
    )
    parser.add_argument(
        "--run",
        action="append",
        help="Run spec formatted as 'label|pairwise_path|curated_path'. Repeat this argument for multiple runs.",
    )
    parser.add_argument("--output-prefix", required=True, help="Output prefix for scenario shift summary.")
    parser.add_argument("--config", default="configs/base.toml", help="Project config TOML path.")
    parser.add_argument("--sample-count", type=int, default=3, help="Requested snapshot count per run.")
    parser.add_argument("--radius-nm", type=float, default=6.0, help="Snapshot target radius in nautical miles.")
    parser.add_argument("--max-age-min", type=float, default=5.0, help="Snapshot lookup max age (minutes).")
    parser.add_argument("--min-pair-rows", type=int, default=2, help="Minimum pair rows per own_mmsi/timestamp candidate.")
    parser.add_argument("--min-local-target-count", type=float, default=1.0, help="Minimum mean local target count per candidate.")
    parser.add_argument("--min-snapshot-targets", type=int, default=1, help="Minimum target count required after snapshot build.")
    parser.add_argument("--min-time-gap-min", type=float, default=120.0, help="Minimum time gap between selected snapshots per own ship.")
    parser.add_argument("--current-scenario-name", default="current", help="Scenario name used as delta baseline.")
    parser.add_argument("--score-weight-rule", type=float, default=0.4, help="Candidate ranking weight for mean rule score.")
    parser.add_argument("--score-weight-density", type=float, default=0.6, help="Candidate ranking weight for mean local target count.")
    args = parser.parse_args()

    run_specs = _parse_run_specs(args.run)
    if not run_specs:
        raise ValueError("At least one --run must be provided.")

    summary = run_scenario_shift_multi_snapshot(
        run_specs=run_specs,
        output_prefix=args.output_prefix,
        config_path=args.config,
        sample_count=max(1, int(args.sample_count)),
        radius_nm=float(args.radius_nm),
        max_age_minutes=float(args.max_age_min),
        min_pair_rows=max(1, int(args.min_pair_rows)),
        min_local_target_count=float(args.min_local_target_count),
        min_snapshot_targets=max(1, int(args.min_snapshot_targets)),
        min_time_gap_minutes=max(0.0, float(args.min_time_gap_min)),
        current_scenario_name=str(args.current_scenario_name),
        score_weight_rule=float(args.score_weight_rule),
        score_weight_density=float(args.score_weight_density),
    )
    print(f"status={summary['status']}")
    print(f"run_count={summary['run_count']}")
    print(f"requested_sample_count={summary['requested_sample_count']}")
    print(f"completed_sample_count={summary['completed_sample_count']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")


if __name__ == "__main__":
    main()
