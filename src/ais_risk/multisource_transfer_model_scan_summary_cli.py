from __future__ import annotations

import argparse

from .multisource_transfer_model_scan_summary import run_multisource_transfer_model_scan_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize transfer-model scans across multiple source regions.")
    parser.add_argument(
        "--scan-output-root",
        default="/Users/seoki/Desktop/research/outputs/2026-04-05_transfer_model_scan_multisource_10seed",
        help="Directory containing <source>_transfer_model_scan_detail.csv and summary json files.",
    )
    parser.add_argument(
        "--source-regions",
        default="houston,nola,seattle",
        help="Comma-separated source regions to summarize.",
    )
    parser.add_argument(
        "--output-prefix",
        default="/Users/seoki/Desktop/research/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed",
        help="Output prefix path (without extension).",
    )
    parser.add_argument("--max-target-ece", type=float, default=0.10, help="Maximum allowed target ECE for combined pass.")
    parser.add_argument(
        "--max-negative-pairs",
        type=int,
        default=1,
        help="Maximum allowed negative transfer pairs for combined pass.",
    )
    args = parser.parse_args()

    summary = run_multisource_transfer_model_scan_summary(
        scan_output_root=args.scan_output_root,
        source_regions=[item.strip() for item in str(args.source_regions).split(",") if item.strip()],
        output_prefix=args.output_prefix,
        max_target_ece=float(args.max_target_ece),
        max_negative_pairs_allowed=int(args.max_negative_pairs),
    )
    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"detail_csv={summary['detail_csv_path']}")
    print(f"source_summary_csv={summary['source_summary_csv_path']}")


if __name__ == "__main__":
    main()

