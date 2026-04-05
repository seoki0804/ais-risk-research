from __future__ import annotations

import argparse

from .scenario_threshold_tuning import run_scenario_threshold_tuning


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-tune safe/warning thresholds on scenario-shift multi-snapshot summary."
    )
    parser.add_argument("--scenario-shift-summary", required=True, help="Path to scenario_shift_multi_summary.json.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for tuning summary.")
    parser.add_argument("--config", default="configs/base.toml", help="Project config TOML path.")
    parser.add_argument("--safe-min", type=float, default=0.25, help="Safe threshold grid min.")
    parser.add_argument("--safe-max", type=float, default=0.45, help="Safe threshold grid max.")
    parser.add_argument("--safe-step", type=float, default=0.05, help="Safe threshold grid step.")
    parser.add_argument("--warning-min", type=float, default=0.55, help="Warning threshold grid min.")
    parser.add_argument("--warning-max", type=float, default=0.80, help="Warning threshold grid max.")
    parser.add_argument("--warning-step", type=float, default=0.05, help="Warning threshold grid step.")
    parser.add_argument("--current-scenario-name", default="current", help="Current scenario name for delta reference.")
    parser.add_argument("--epsilon-nonzero-nm2", type=float, default=1e-9, help="Absolute epsilon for non-zero warning delta.")
    parser.add_argument("--target-warning-nonzero-ratio", type=float, default=0.40, help="Target run ratio with non-zero warning delta.")
    parser.add_argument("--min-warning-delta-abs-mean", type=float, default=0.005, help="Minimum desired abs mean warning delta.")
    parser.add_argument("--min-caution-delta-abs-mean", type=float, default=0.05, help="Minimum desired abs mean caution delta.")
    parser.add_argument("--warning-area-min-nm2", type=float, default=0.0, help="Preferred lower bound for current warning area mean.")
    parser.add_argument("--warning-area-max-nm2", type=float, default=0.15, help="Preferred upper bound for current warning area mean.")
    parser.add_argument("--caution-area-min-nm2", type=float, default=0.05, help="Preferred lower bound for current caution area mean.")
    parser.add_argument("--caution-area-max-nm2", type=float, default=1.2, help="Preferred upper bound for current caution area mean.")
    parser.add_argument("--weight-warning-ratio", type=float, default=1.0, help="Objective weight for warning non-zero ratio term.")
    parser.add_argument("--weight-warning-delta", type=float, default=1.0, help="Objective weight for warning delta term.")
    parser.add_argument("--weight-caution-delta", type=float, default=1.0, help="Objective weight for caution delta term.")
    parser.add_argument("--weight-warning-area-range", type=float, default=1.0, help="Objective weight for warning area range term.")
    parser.add_argument("--weight-caution-area-range", type=float, default=1.0, help="Objective weight for caution area range term.")
    parser.add_argument("--top-k", type=int, default=10, help="Top-k profiles shown in markdown summary.")
    parser.add_argument("--bootstrap-iterations", type=int, default=0, help="Bootstrap iterations for recommendation robustness.")
    parser.add_argument("--bootstrap-random-seed", type=int, default=42, help="Random seed for bootstrap resampling.")
    args = parser.parse_args()

    summary = run_scenario_threshold_tuning(
        scenario_shift_summary_path=args.scenario_shift_summary,
        output_prefix=args.output_prefix,
        config_path=args.config,
        safe_min=float(args.safe_min),
        safe_max=float(args.safe_max),
        safe_step=float(args.safe_step),
        warning_min=float(args.warning_min),
        warning_max=float(args.warning_max),
        warning_step=float(args.warning_step),
        current_scenario_name=str(args.current_scenario_name),
        epsilon_nonzero_nm2=float(args.epsilon_nonzero_nm2),
        target_warning_nonzero_ratio=float(args.target_warning_nonzero_ratio),
        min_warning_delta_abs_mean=float(args.min_warning_delta_abs_mean),
        min_caution_delta_abs_mean=float(args.min_caution_delta_abs_mean),
        warning_area_min_nm2=float(args.warning_area_min_nm2),
        warning_area_max_nm2=float(args.warning_area_max_nm2),
        caution_area_min_nm2=float(args.caution_area_min_nm2),
        caution_area_max_nm2=float(args.caution_area_max_nm2),
        weight_warning_ratio=float(args.weight_warning_ratio),
        weight_warning_delta=float(args.weight_warning_delta),
        weight_caution_delta=float(args.weight_caution_delta),
        weight_warning_area_range=float(args.weight_warning_area_range),
        weight_caution_area_range=float(args.weight_caution_area_range),
        top_k=max(1, int(args.top_k)),
        bootstrap_iterations=max(0, int(args.bootstrap_iterations)),
        bootstrap_random_seed=int(args.bootstrap_random_seed),
    )

    print(f"status={summary['status']}")
    print(f"candidate_profile_count={summary['candidate_profile_count']}")
    print(f"recommended_profile={summary['recommended_profile_name']}")
    print(f"recommended_safe={summary['recommended_safe_threshold']}")
    print(f"recommended_warning={summary['recommended_warning_threshold']}")
    print(f"recommended_bootstrap_top1={summary.get('recommended_bootstrap_top1_frequency')}")
    print(f"bootstrap_consensus_profile={summary.get('bootstrap_consensus_profile_name')}")
    print(f"bootstrap_consensus_frequency={summary.get('bootstrap_consensus_profile_frequency')}")
    print(f"bootstrap_iterations={summary.get('bootstrap_effective_iterations', 0)}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"rows_csv={summary['rows_csv_path']}")
    print(f"sweep_summary_json={summary['sweep_summary_path']}")


if __name__ == "__main__":
    main()
