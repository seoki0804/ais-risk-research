from __future__ import annotations

import argparse

from .scenario_threshold_sweep import run_scenario_threshold_sweep


def _parse_profiles(profile_texts: list[str] | None) -> list[dict[str, float | str]]:
    profiles: list[dict[str, float | str]] = []
    for raw in profile_texts or []:
        text = str(raw).strip()
        if not text:
            continue
        chunks = [item.strip() for item in text.split(":")]
        if len(chunks) != 3:
            raise ValueError(
                "Invalid --profile format. Use 'name:safe:warning'. "
                f"Received: {text}"
            )
        name, safe_text, warning_text = chunks
        profiles.append(
            {
                "name": name,
                "safe": float(safe_text),
                "warning": float(warning_text),
            }
        )
    return profiles


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run threshold sensitivity sweep from scenario-shift multi-snapshot summary."
    )
    parser.add_argument("--scenario-shift-summary", required=True, help="Path to scenario_shift_multi_summary.json.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for threshold sweep summary.")
    parser.add_argument("--config", default="configs/base.toml", help="Project config TOML path.")
    parser.add_argument(
        "--profile",
        action="append",
        help="Threshold profile as 'name:safe:warning'. Repeat for multiple profiles.",
    )
    parser.add_argument("--baseline-profile", default="base", help="Baseline profile name for delta comparison.")
    parser.add_argument("--current-scenario-name", default="current", help="Scenario name used as delta baseline.")
    parser.add_argument(
        "--save-profile-results",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Save per-sample per-profile result JSON files.",
    )
    args = parser.parse_args()

    summary = run_scenario_threshold_sweep(
        scenario_shift_summary_path=args.scenario_shift_summary,
        output_prefix=args.output_prefix,
        config_path=args.config,
        threshold_profiles=_parse_profiles(args.profile),
        baseline_profile=args.baseline_profile,
        current_scenario_name=args.current_scenario_name,
        save_profile_results=bool(args.save_profile_results),
    )
    print(f"status={summary['status']}")
    print(f"sample_count={summary['sample_count']}")
    print(f"profile_count={summary['profile_count']}")
    print(f"rows_csv={summary['rows_csv_path']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")


if __name__ == "__main__":
    main()
