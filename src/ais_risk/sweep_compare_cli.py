from __future__ import annotations

import argparse

from .sweep_compare import compare_study_sweep_summaries


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare focused own-ship sweep summary against baseline sweep summary."
    )
    parser.add_argument("--focus-summary", required=True, help="Focused sweep summary JSON path.")
    parser.add_argument("--baseline-summary", required=True, help="Baseline sweep summary JSON path.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for compare artifacts.")
    parser.add_argument("--focus-label", default="focus", help="Label for focused sweep side.")
    parser.add_argument("--baseline-label", default="baseline", help="Label for baseline sweep side.")
    parser.add_argument(
        "--epsilon",
        type=float,
        default=1e-9,
        help="Numeric tolerance for deciding equal metrics.",
    )
    args = parser.parse_args()

    summary = compare_study_sweep_summaries(
        focus_summary_path=args.focus_summary,
        baseline_summary_path=args.baseline_summary,
        output_prefix=args.output_prefix,
        focus_label=args.focus_label,
        baseline_label=args.baseline_label,
        epsilon=float(args.epsilon),
    )
    print(f"status={summary['status']}")
    print(f"modelset_count={summary['modelset_count']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_csv={summary['summary_csv_path']}")


if __name__ == "__main__":
    main()

