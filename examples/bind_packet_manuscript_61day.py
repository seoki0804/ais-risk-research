#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path("/Users/seoki/Desktop/research")
OUT_ROOT = ROOT / "outputs/presentation_deck_outline_61day_2026-03-13"
WORKBENCH = OUT_ROOT / "workbenches/paper_workbench_main_61day"


def build_bundle(packet_dir: Path, mode: str) -> Path:
    bundle_dir = packet_dir / "manuscript_bundle_61day"
    assets_src = WORKBENCH / "conference_print_assets_61day"
    tex_src = WORKBENCH / "paper_conference_8page_asset_locked_61day.tex"
    bbl_src = WORKBENCH / "paper_conference_8page_asset_locked_61day.bbl"
    pdf_src = WORKBENCH / "paper_conference_8page_asset_locked_61day.pdf"
    bib_src = WORKBENCH / "literature_reference_pack_61day.bib"

    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)

    tex_text = tex_src.read_text()
    if mode == "blind":
        tex_text = tex_text.replace(
            r"\author{Anonymous Submission Draft}",
            r"\author{Anonymous Submission Draft}",
        )
    else:
        tex_text = tex_text.replace(
            r"\author{Anonymous Submission Draft}",
            r"\author{Author Metadata Pending Final Intake}",
        )

    tex_out = bundle_dir / f"paper_{mode}_bound_61day.tex"
    tex_out.write_text(tex_text)

    shutil.copy2(bbl_src, bundle_dir / "paper_conference_8page_asset_locked_61day.bbl")
    shutil.copy2(bib_src, bundle_dir / "literature_reference_pack_61day.bib")
    if pdf_src.exists():
        shutil.copy2(pdf_src, bundle_dir / "paper_conference_8page_asset_locked_61day.pdf")
    shutil.copytree(assets_src, bundle_dir / "conference_print_assets_61day")

    note = bundle_dir / "MANUSCRIPT_BUNDLE_NOTE_61day.md"
    note.write_text(
        "\n".join(
            [
                "# Manuscript Bundle Note 61day",
                "",
                f"- Packet: `{packet_dir}`",
                f"- Mode: `{mode}`",
                "- Source TeX: `paper_conference_8page_asset_locked_61day.tex`",
                "- Bibliography mode: frozen `.bbl` input",
                "- Asset directory: `conference_print_assets_61day`",
                "",
                "## Entry files",
                "",
                f"- TeX: `{tex_out.name}`",
                "- BBL: `paper_conference_8page_asset_locked_61day.bbl`",
                "- Bib: `literature_reference_pack_61day.bib`",
                "",
                "## Notes",
                "",
                "- This bundle is packet-local and intended for venue-specific adaptation work.",
                "- Blind mode preserves anonymous front matter.",
                "- Camera-ready mode keeps a placeholder author line until real metadata is filled.",
            ]
        )
        + "\n"
    )

    compile_script = bundle_dir / "compile_manuscript_bundle_61day.sh"
    compile_script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'cd "$(dirname "$0")"',
                f"tectonic --keep-logs --keep-intermediates {tex_out.name}",
                "",
            ]
        )
    )
    compile_script.chmod(0o755)

    return bundle_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet_dir")
    parser.add_argument("mode", choices=["blind", "camera-ready"])
    args = parser.parse_args()

    packet_dir = Path(args.packet_dir)
    bundle_dir = build_bundle(packet_dir, args.mode)
    print(bundle_dir)


if __name__ == "__main__":
    main()
