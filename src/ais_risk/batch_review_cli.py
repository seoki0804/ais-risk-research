from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from .batch_review import build_study_batch_review_from_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build research review markdown from study batch summary JSON."
    )
    parser.add_argument("--batch-summary", required=True, help="Path to study batch summary JSON.")
    parser.add_argument("--previous-batch-summary", help="Optional previous batch summary JSON for delta comparison.")
    parser.add_argument("--output", help="Output markdown path. Defaults to research_logs/{date}_study_batch_review.md")
    parser.add_argument("--date", help="Optional review date in YYYY-MM-DD.")
    parser.add_argument("--author", default="Codex", help="Review author.")
    parser.add_argument(
        "--own-ship-case-f1-std-threshold",
        type=float,
        default=0.10,
        help="Alert threshold for own_ship_case_f1_std.",
    )
    parser.add_argument(
        "--own-ship-case-f1-ci95-width-threshold",
        type=float,
        default=0.20,
        help="Alert threshold for own_ship_case_f1_ci95_width.",
    )
    parser.add_argument(
        "--calibration-ece-threshold",
        type=float,
        default=0.15,
        help="Alert threshold for best calibration ECE.",
    )
    args = parser.parse_args()

    date_text = args.date or datetime.now().date().isoformat()
    output_path = args.output or str(Path("research_logs") / f"{date_text}_study_batch_review.md")
    saved = build_study_batch_review_from_summary(
        batch_summary_path=args.batch_summary,
        output_path=output_path,
        review_date=date_text,
        author=args.author,
        own_ship_case_f1_std_threshold=float(args.own_ship_case_f1_std_threshold),
        own_ship_case_f1_ci95_width_threshold=float(args.own_ship_case_f1_ci95_width_threshold),
        calibration_ece_threshold=float(args.calibration_ece_threshold),
        previous_batch_summary_path=args.previous_batch_summary,
    )
    print(f"review={saved}")


if __name__ == "__main__":
    main()
