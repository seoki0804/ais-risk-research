#!/usr/bin/env python3
"""Apply venue-bound real-value text to intake metadata and TeX placeholders."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13"
)
DEFAULT_INTAKE = DEFAULT_ROOT / "submission_intake_template_61day.json"
DEFAULT_METADATA = DEFAULT_ROOT / "submission_portal_metadata_filled_61day.json"
DEFAULT_TEX_PATHS = [
    DEFAULT_ROOT / "paper_conference_8page_asset_locked_61day.tex",
    DEFAULT_ROOT
    / "venue_packets/applied_conf_default_camera-ready_61day/manuscript_bundle_61day/"
    "paper_camera-ready_bound_61day.tex",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--venue-name", required=True)
    parser.add_argument("--venue-round", required=True)
    parser.add_argument("--intake", default=str(DEFAULT_INTAKE))
    parser.add_argument("--metadata", default=str(DEFAULT_METADATA))
    parser.add_argument("--tex", action="append", dest="tex_paths")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing files.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, payload: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        return
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def render_data_code_sentence(metadata: dict[str, Any]) -> str:
    data = normalize_space(str(metadata.get("data_availability", "")))
    code = normalize_space(str(metadata.get("code_availability", "")))
    parts = [part for part in (data, code) if part]

    repo_allowed = bool(metadata.get("repository_link_allowed"))
    repo_url = normalize_space(str(metadata.get("repo_url", "")))
    anon_repo = metadata.get("submission_has_anonymized_repo")

    if repo_allowed:
        if repo_url and not repo_url.lower().startswith("n/a"):
            parts.append(f"Code repository: {repo_url}.")
        elif anon_repo:
            parts.append("An anonymized repository is provided according to venue policy.")
    else:
        parts.append(
            "Repository links are withheld during blind review and released according to venue policy."
        )

    if not parts:
        parts.append("Data and code availability statements are provided in the submission metadata.")
    return latex_escape(" ".join(parts))


def replace_noindent_section(text: str, section_title: str, new_sentence: str) -> tuple[str, bool]:
    pattern = re.compile(
        rf"(\\section\*\{{{re.escape(section_title)}\}}\n)\\noindent[^\n]*\n", flags=re.MULTILINE
    )
    match = pattern.search(text)
    if not match:
        return text, False
    replacement = f"{match.group(1)}\\noindent {new_sentence}\n"
    current_block = match.group(0)
    if current_block == replacement:
        return text, False
    return text[: match.start()] + replacement + text[match.end() :], True


def build_author_block(metadata: dict[str, Any]) -> str:
    names = metadata.get("author_names") or []
    affiliations = metadata.get("affiliations") or []
    if isinstance(names, list):
        joined_names = ", ".join(str(item) for item in names if str(item).strip())
    else:
        joined_names = str(names).strip()
    if not joined_names:
        joined_names = str(metadata.get("corresponding_author_name", "")).strip()
    if not joined_names:
        joined_names = "Author Name"

    if isinstance(affiliations, list):
        joined_aff = "; ".join(str(item) for item in affiliations if str(item).strip())
    else:
        joined_aff = str(affiliations).strip()

    joined_names = latex_escape(joined_names)
    joined_aff = latex_escape(joined_aff)
    if joined_aff:
        return f"{joined_names} \\\\ {joined_aff}"
    return joined_names


def apply_tex_binding(path: Path, metadata: dict[str, Any], dry_run: bool) -> tuple[bool, list[str]]:
    text = path.read_text(encoding="utf-8")
    original = text
    notes: list[str] = []

    data_code_sentence = render_data_code_sentence(metadata)
    ack_text = latex_escape(normalize_space(str(metadata.get("acknowledgements", "None.")) or "None."))
    conflict_text = latex_escape(
        normalize_space(
            str(metadata.get("conflict_statement", "The author declares no competing interests."))
        )
    )
    author_block = build_author_block(metadata)

    text, changed_data = replace_noindent_section(text, "Data and Code Availability", data_code_sentence)
    if changed_data:
        notes.append("updated Data and Code Availability section")
    text, changed_ack = replace_noindent_section(text, "Acknowledgments", ack_text)
    if changed_ack:
        notes.append("updated Acknowledgments section")
    text, changed_conflict = replace_noindent_section(text, "Conflict of Interest", conflict_text)
    if changed_conflict:
        notes.append("updated Conflict of Interest section")

    if "Author Metadata Pending Final Intake" in text:
        text = text.replace("Author Metadata Pending Final Intake", author_block)
        notes.append("resolved pending author metadata front matter")

    cleaned = re.sub(r"^% TODO\(venue\):.*\n", "", text, flags=re.MULTILINE)
    if cleaned != text:
        text = cleaned
        notes.append("removed TODO(venue) placeholder comments")

    changed = text != original
    if changed and not dry_run:
        path.write_text(text, encoding="utf-8")

    return changed, notes


def main() -> None:
    args = parse_args()
    intake_path = Path(args.intake)
    metadata_path = Path(args.metadata)
    tex_paths = [Path(item) for item in args.tex_paths] if args.tex_paths else DEFAULT_TEX_PATHS

    intake = load_json(intake_path)
    metadata = load_json(metadata_path)

    intake.setdefault("venue", {})
    intake["venue"]["name"] = args.venue_name
    intake["venue"]["round_or_deadline"] = args.venue_round

    metadata["venue_name"] = args.venue_name
    metadata["venue_round_or_deadline"] = args.venue_round

    dump_json(intake_path, intake, dry_run=args.dry_run)
    dump_json(metadata_path, metadata, dry_run=args.dry_run)

    print(f"Intake venue.name -> {args.venue_name}")
    print(f"Intake venue.round_or_deadline -> {args.venue_round}")
    if args.dry_run:
        print("Mode: dry-run (no files written)")

    any_tex_changed = False
    for tex_path in tex_paths:
        if not tex_path.exists():
            print(f"[SKIP] missing TeX file: {tex_path}")
            continue
        changed, notes = apply_tex_binding(tex_path, metadata, dry_run=args.dry_run)
        any_tex_changed = any_tex_changed or changed
        state = "CHANGED" if changed else "UNCHANGED"
        print(f"[{state}] {tex_path}")
        for note in notes:
            print(f"  - {note}")

    if not any_tex_changed:
        print("No TeX placeholder change detected.")


if __name__ == "__main__":
    main()
