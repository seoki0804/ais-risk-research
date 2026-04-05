from __future__ import annotations

import argparse

from .multisource_transfer_governance_bridge import run_multisource_transfer_governance_bridge


def main() -> None:
    parser = argparse.ArgumentParser(description="Bridge multi-source transfer summary with transfer-policy governance lock.")
    parser.add_argument(
        "--multisource-source-summary-csv",
        default="/Users/seoki/Desktop/research/docs/multisource_transfer_model_scan_summary_2026-04-05_10seed_source_summary.csv",
        help="CSV path from multi-source transfer model scan summary (source-level).",
    )
    parser.add_argument(
        "--transfer-policy-governance-lock-json",
        default="/Users/seoki/Desktop/research/docs/transfer_policy_governance_lock_2026-04-05_10seed.json",
        help="Transfer-policy governance-lock JSON path.",
    )
    parser.add_argument(
        "--output-prefix",
        default="/Users/seoki/Desktop/research/docs/multisource_transfer_governance_bridge_2026-04-05_10seed",
        help="Output prefix path (without extension).",
    )
    args = parser.parse_args()

    summary = run_multisource_transfer_governance_bridge(
        multisource_source_summary_csv_path=args.multisource_source_summary_csv,
        transfer_policy_governance_lock_json_path=args.transfer_policy_governance_lock_json,
        output_prefix=args.output_prefix,
    )
    print(f"summary_md={summary['summary_md_path']}")
    print(f"summary_json={summary['summary_json_path']}")
    print(f"detail_csv={summary['detail_csv_path']}")


if __name__ == "__main__":
    main()

