from __future__ import annotations

import argparse

from .regional_gradcam_report import run_regional_gradcam_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Grad-CAM report from a regional raster CNN benchmark summary.")
    parser.add_argument("--benchmark-summary-json", required=True, help="Path to the regional raster CNN summary JSON.")
    parser.add_argument("--output-prefix", required=True, help="Output prefix for Grad-CAM report files.")
    parser.add_argument("--torch-device", default="auto", help="Torch device: auto, cpu, or mps.")
    args = parser.parse_args()

    summary = run_regional_gradcam_report(
        benchmark_summary_json_path=args.benchmark_summary_json,
        output_prefix=args.output_prefix,
        torch_device=args.torch_device,
    )
    print(f"summary_json={summary['summary_json_path']}")
    print(f"summary_md={summary['summary_md_path']}")
    print(f"figure_png={summary['figure_png_path']}")
    print(f"figure_svg={summary['figure_svg_path']}")


if __name__ == "__main__":
    main()
