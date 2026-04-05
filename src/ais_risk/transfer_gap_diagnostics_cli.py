from __future__ import annotations

import argparse

from .transfer_gap_diagnostics import run_transfer_gap_diagnostics


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose transfer F1 gaps with bootstrap CI and target-retune gains.")
    parser.add_argument(
        "--transfer-check-csv",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_check_10seed/transfer_recommendation_check.csv",
        help="Transfer recommendation check CSV path.",
    )
    parser.add_argument(
        "--output-prefix",
        default="/Users/seoki/Desktop/research/outputs/2026-04-04_transfer_gap_diagnostics_10seed/transfer_gap_diagnostics",
        help="Output prefix path (without extension).",
    )
    parser.add_argument("--threshold-grid-step", type=float, default=0.01, help="Threshold sweep step size.")
    parser.add_argument("--bootstrap-samples", type=int, default=500, help="Bootstrap sample count.")
    parser.add_argument("--random-seed", type=int, default=42, help="Random seed.")
    args = parser.parse_args()

    summary = run_transfer_gap_diagnostics(
        transfer_check_csv_path=args.transfer_check_csv,
        output_prefix=args.output_prefix,
        threshold_grid_step=float(args.threshold_grid_step),
        bootstrap_samples=int(args.bootstrap_samples),
        random_seed=int(args.random_seed),
    )
    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"detail_csv={summary['detail_csv_path']}")
    print(f"summary_csv={summary['summary_csv_path']}")


if __name__ == "__main__":
    main()
