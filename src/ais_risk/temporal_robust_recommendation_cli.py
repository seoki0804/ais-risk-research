from __future__ import annotations

import argparse

from .temporal_robust_recommendation import run_temporal_robust_recommendation


def _parse_str_list(raw: str) -> list[str]:
    return [token.strip() for token in str(raw).split(",") if token.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build temporal-robust recommendation using out-of-time aggregate model metrics.")
    parser.add_argument("--baseline-aggregate-csv", required=True, help="Baseline (in-time) aggregate CSV path.")
    parser.add_argument("--out-of-time-aggregate-csv", required=True, help="Out-of-time aggregate CSV path.")
    parser.add_argument(
        "--baseline-recommendation-csv",
        default="",
        help="Optional baseline recommendation CSV path for current-vs-robust comparison.",
    )
    parser.add_argument(
        "--dataset-prefixes",
        default="",
        help="Optional comma-separated dataset prefixes (e.g., 'houston,nola').",
    )
    parser.add_argument("--output-prefix", required=True, help="Output prefix path (without suffix).")
    parser.add_argument("--f1-tolerance", type=float, default=0.01, help="F1 tolerance band.")
    parser.add_argument("--max-ece-mean", type=float, default=0.10, help="ECE hard gate threshold.")
    parser.add_argument("--disable-ece-gate", action="store_true", help="Disable ECE hard gate.")
    parser.add_argument(
        "--min-out-of-time-delta-f1",
        type=float,
        default=-0.05,
        help="Temporal gate: required minimum out-of-time delta F1 (out_of_time - in_time).",
    )
    parser.add_argument(
        "--delta-penalty-weight",
        type=float,
        default=1.0,
        help="Penalty weight used in robust_score = baseline_f1 - weight * temporal_penalty.",
    )
    args = parser.parse_args()

    summary = run_temporal_robust_recommendation(
        baseline_aggregate_csv_path=args.baseline_aggregate_csv,
        out_of_time_aggregate_csv_path=args.out_of_time_aggregate_csv,
        output_prefix=args.output_prefix,
        baseline_recommendation_csv_path=(args.baseline_recommendation_csv or None),
        dataset_prefix_filters=_parse_str_list(args.dataset_prefixes),
        f1_tolerance=float(args.f1_tolerance),
        max_ece_mean=(None if bool(args.disable_ece_gate) else float(args.max_ece_mean)),
        min_out_of_time_delta_f1=float(args.min_out_of_time_delta_f1),
        delta_penalty_weight=float(args.delta_penalty_weight),
    )

    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"detail_csv={summary['detail_csv_path']}")
    print(f"comparison_csv={summary['comparison_csv_path']}")
    print(f"recommendation_csv={summary['recommendation_csv_path']}")


if __name__ == "__main__":
    main()
