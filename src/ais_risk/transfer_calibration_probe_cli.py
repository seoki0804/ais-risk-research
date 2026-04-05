from __future__ import annotations

import argparse

from .transfer_calibration_probe import run_transfer_calibration_probe


def _parse_list(raw: str) -> list[str]:
    return [token.strip() for token in str(raw).split(",") if token.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe post-hoc calibration methods on transfer pairs using source validation scores."
    )
    parser.add_argument(
        "--transfer-scan-detail-csv",
        required=True,
        help="transfer_model_scan detail CSV path.",
    )
    parser.add_argument(
        "--output-prefix",
        required=True,
        help="Output prefix path (without extension).",
    )
    parser.add_argument(
        "--source-region",
        default="",
        help="Optional source-region filter.",
    )
    parser.add_argument(
        "--models",
        default="",
        help="Optional comma-separated model filter (default: all models in detail CSV).",
    )
    parser.add_argument(
        "--methods",
        default="none,platt,isotonic",
        help="Comma-separated calibration methods. Supported: none,platt,isotonic",
    )
    parser.add_argument(
        "--threshold-grid-step",
        type=float,
        default=0.01,
        help="Threshold sweep step for fixed and retuned threshold selection.",
    )
    parser.add_argument(
        "--ece-gate-max",
        type=float,
        default=0.10,
        help="Target ECE gate threshold.",
    )
    parser.add_argument(
        "--max-negative-pairs-allowed",
        type=int,
        default=1,
        help="Allowed negative transfer-pair count for pass flag.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed used by platt scaling.",
    )
    args = parser.parse_args()

    summary = run_transfer_calibration_probe(
        transfer_scan_detail_csv_path=args.transfer_scan_detail_csv,
        output_prefix=args.output_prefix,
        source_region_filter=args.source_region,
        model_names=_parse_list(args.models),
        methods=_parse_list(args.methods),
        threshold_grid_step=float(args.threshold_grid_step),
        ece_gate_max=float(args.ece_gate_max),
        max_negative_pairs_allowed=int(args.max_negative_pairs_allowed),
        random_seed=int(args.random_seed),
    )
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"detail_csv={summary['detail_csv_path']}")
    print(f"model_method_summary_csv={summary['model_method_summary_csv_path']}")


if __name__ == "__main__":
    main()

