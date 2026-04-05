from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .study_journal import build_study_journal_from_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a structured study journal markdown from study_summary JSON."
    )
    parser.add_argument("--study-summary", required=True, help="Path to *_study_summary.json.")
    parser.add_argument("--output", help="Output markdown path. Default: research_logs/{date}_{dataset_id}_study.md")
    parser.add_argument("--author", default="Codex", help="Author name in journal.")
    parser.add_argument("--date", help="Optional YYYY-MM-DD override.")
    parser.add_argument("--topic", help="Optional topic title suffix.")
    parser.add_argument("--note", help="Optional one-line note appended to journal.")
    args = parser.parse_args()

    output_path = args.output
    if not output_path:
        date_text = args.date or date.today().isoformat()
        output_path = str(Path("research_logs") / f"{date_text}_study_journal.md")

    written = build_study_journal_from_summary(
        study_summary_path=args.study_summary,
        output_path=output_path,
        author=args.author,
        date_text=args.date,
        topic=args.topic,
        note=args.note,
    )
    print(f"journal={written}")


if __name__ == "__main__":
    main()

