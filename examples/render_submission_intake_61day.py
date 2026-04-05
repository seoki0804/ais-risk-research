#!/usr/bin/env python3
"""Render intake JSON into operational submission handoff artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(
    "/Users/seoki/Desktop/research/outputs/"
    "presentation_deck_outline_61day_2026-03-13"
)
DEFAULT_INPUT = DEFAULT_ROOT / "submission_intake_template_61day.json"
DEFAULT_BASE_METADATA = (
    DEFAULT_ROOT
    / "venue_packets"
    / "applied_conf_default_blind_61day"
    / "submission_portal_metadata_61day.json"
)
DEFAULT_OUTPUT_JSON = DEFAULT_ROOT / "submission_portal_metadata_filled_61day.json"
DEFAULT_OUTPUT_MD = DEFAULT_ROOT / "submission_intake_handoff_61day.md"
DEFAULT_OUTPUT_COPY_MD = DEFAULT_ROOT / "submission_portal_copy_paste_filled_61day.md"
DEFAULT_OUTPUT_QUEUE_MD = DEFAULT_ROOT / "submission_intake_fill_queue_61day.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to the submission intake JSON file.",
    )
    parser.add_argument(
        "--base-metadata",
        default=str(DEFAULT_BASE_METADATA),
        help="Path to the canonical portal metadata JSON defaults.",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON),
        help="Path to write the rendered portal metadata JSON.",
    )
    parser.add_argument(
        "--output-md",
        default=str(DEFAULT_OUTPUT_MD),
        help="Path to write the rendered handoff markdown.",
    )
    parser.add_argument(
        "--output-copy-md",
        default=str(DEFAULT_OUTPUT_COPY_MD),
        help="Path to write the rendered portal copy-paste markdown.",
    )
    parser.add_argument(
        "--output-queue-md",
        default=str(DEFAULT_OUTPUT_QUEUE_MD),
        help="Path to write the remaining fill-queue markdown.",
    )
    return parser.parse_args()


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def review_mode_is_blind(review_mode: str) -> bool:
    return "blind" in review_mode.lower()


def get_nested(data: dict[str, Any], keys: list[str]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def require(data: dict[str, Any], keys: list[str], sink: list[str]) -> None:
    value = get_nested(data, keys)
    if is_empty(value):
        sink.append(".".join(keys))


def validate(data: dict[str, Any]) -> dict[str, list[str]]:
    venue_missing: list[str] = []
    author_missing: list[str] = []
    disclosure_missing: list[str] = []
    release_missing: list[str] = []
    portal_missing: list[str] = []

    for keys in (
        ["venue", "name"],
        ["venue", "type"],
        ["venue", "template_type"],
        ["venue", "review_mode"],
        ["venue", "main_page_limit"],
        ["venue", "supplementary_policy"],
        ["venue", "abstract_word_limit"],
        ["venue", "keyword_limit"],
    ):
        require(data, keys, venue_missing)

    for keys in (
        ["authors", "author_names"],
        ["authors", "affiliations"],
        ["authors", "corresponding_author_name"],
        ["authors", "corresponding_author_email"],
    ):
        require(data, keys, author_missing)

    for keys in (
        ["release_policy", "submission_has_anonymized_repo"],
        ["release_policy", "code_release_timing"],
    ):
        require(data, keys, release_missing)

    for keys in (
        ["portal_selection", "chosen_abstract_variant"],
        ["portal_selection", "chosen_keyword_set"],
    ):
        require(data, keys, portal_missing)

    review_mode = str(get_nested(data, ["venue", "review_mode"]) or "")
    if review_mode_is_blind(review_mode):
        for keys in (
            ["venue", "repository_link_allowed"],
            ["venue", "supplementary_anonymity_required"],
        ):
            require(data, keys, venue_missing)

    if get_nested(data, ["release_policy", "submission_has_anonymized_repo"]) is True:
        require(data, ["release_policy", "repo_url"], release_missing)

    if get_nested(data, ["venue", "data_code_field_required"]) is True:
        for keys in (
            ["release_policy", "data_availability_final_text"],
            ["release_policy", "code_availability_final_text"],
        ):
            require(data, keys, release_missing)

    if get_nested(data, ["venue", "author_contribution_required"]) is True:
        require(data, ["authors", "author_contribution_statement"], author_missing)

    if get_nested(data, ["venue", "funding_statement_required"]) is True:
        require(data, ["disclosures", "funding_statement"], disclosure_missing)

    if get_nested(data, ["venue", "conflict_statement_required"]) is True:
        require(data, ["disclosures", "conflict_statement"], disclosure_missing)

    track = get_nested(data, ["venue", "track_or_subject_area"])
    if not is_empty(track):
        require(data, ["portal_selection", "chosen_track"], portal_missing)

    return {
        "venue_policy": venue_missing,
        "author_metadata": author_missing,
        "disclosures": disclosure_missing,
        "release_policy": release_missing,
        "portal_selection": portal_missing,
    }


def choose_title(intake: dict[str, Any], defaults: dict[str, Any]) -> str:
    variant = str(get_nested(intake, ["portal_selection", "chosen_title_variant"]) or "primary")
    if variant == "extended":
        return str(get_nested(intake, ["recommended_defaults", "title_extended"]) or defaults["title_extended"])
    return str(get_nested(intake, ["recommended_defaults", "title_primary"]) or defaults["title_primary"])


def choose_keywords(intake: dict[str, Any], defaults: dict[str, Any]) -> list[str]:
    variant = str(get_nested(intake, ["portal_selection", "chosen_keyword_set"]) or "primary").lower()
    if variant in {"extended", "long", "7", "extended7"}:
        values = get_nested(intake, ["recommended_defaults", "keywords_extended"]) or defaults["keywords_extended"]
        return [str(item) for item in values]
    values = get_nested(intake, ["recommended_defaults", "keywords_primary"]) or defaults["keywords_primary"]
    return [str(item) for item in values]


def choose_track(intake: dict[str, Any], defaults: dict[str, Any]) -> str:
    chosen_track = str(get_nested(intake, ["portal_selection", "chosen_track"]) or "").strip()
    if chosen_track:
        return chosen_track

    venue_track = str(get_nested(intake, ["venue", "track_or_subject_area"]) or "").strip()
    if venue_track:
        return venue_track

    venue_type = str(get_nested(intake, ["venue", "type"]) or "").strip().lower()
    if venue_type == "workshop":
        return str(defaults["suggested_track_workshop"])
    return str(defaults["suggested_track_conservative"])


def choose_abstract_source(variant: str) -> str:
    lowered = variant.lower()
    if "100" in lowered:
        return str(DEFAULT_ROOT / "research_abstract_100word_61day_ko_en.md")
    if "150" in lowered or "250" in lowered or "short" in lowered:
        return str(DEFAULT_ROOT / "research_abstract_short_versions_61day_ko_en.md")
    return str(DEFAULT_ROOT / "research_abstract_61day_ko_en.md")


def choose_statement(value: str, fallback: str) -> str:
    return value.strip() if value.strip() else fallback


def normalize_string_list(values: list[Any]) -> list[str]:
    return [str(item).strip() for item in values if str(item).strip()]


def build_rendered_metadata(
    intake: dict[str, Any],
    defaults: dict[str, Any],
    missing: dict[str, list[str]],
    input_path: Path,
) -> dict[str, Any]:
    total_missing = sum(len(items) for items in missing.values())
    status = "READY" if total_missing == 0 else "BLOCKED"

    author_names = normalize_string_list(
        list(get_nested(intake, ["authors", "author_names"]) or [])
    )
    affiliations = normalize_string_list(
        list(get_nested(intake, ["authors", "affiliations"]) or [])
    )
    selected_keywords = choose_keywords(intake, defaults)
    chosen_abstract_variant = str(
        get_nested(intake, ["portal_selection", "chosen_abstract_variant"]) or ""
    )

    return {
        "status": status,
        "missing_field_count": total_missing,
        "source_intake": str(input_path),
        "submission_mode": str(get_nested(intake, ["submission_mode"]) or ""),
        "venue_name": str(get_nested(intake, ["venue", "name"]) or ""),
        "venue_type": str(get_nested(intake, ["venue", "type"]) or ""),
        "venue_round_or_deadline": str(get_nested(intake, ["venue", "round_or_deadline"]) or ""),
        "venue_template_type": str(get_nested(intake, ["venue", "template_type"]) or ""),
        "venue_review_mode": str(get_nested(intake, ["venue", "review_mode"]) or ""),
        "venue_main_page_limit": str(get_nested(intake, ["venue", "main_page_limit"]) or ""),
        "venue_abstract_word_limit": str(get_nested(intake, ["venue", "abstract_word_limit"]) or ""),
        "venue_keyword_limit": str(get_nested(intake, ["venue", "keyword_limit"]) or ""),
        "title_primary": str(
            get_nested(intake, ["recommended_defaults", "title_primary"]) or defaults["title_primary"]
        ),
        "title_extended": str(
            get_nested(intake, ["recommended_defaults", "title_extended"]) or defaults["title_extended"]
        ),
        "short_title": str(
            get_nested(intake, ["recommended_defaults", "short_title"]) or defaults["short_title"]
        ),
        "selected_title": choose_title(intake, defaults),
        "keywords_primary": list(
            get_nested(intake, ["recommended_defaults", "keywords_primary"]) or defaults["keywords_primary"]
        ),
        "keywords_extended": list(
            get_nested(intake, ["recommended_defaults", "keywords_extended"]) or defaults["keywords_extended"]
        ),
        "selected_keywords": selected_keywords,
        "chosen_abstract_variant": chosen_abstract_variant,
        "abstract_source_doc": choose_abstract_source(chosen_abstract_variant or "long"),
        "one_line_summary": str(defaults["one_line_summary"]),
        "scope_statement": str(
            get_nested(intake, ["recommended_defaults", "scope_statement"]) or defaults["scope_statement"]
        ),
        "novelty_statement": str(
            get_nested(intake, ["recommended_defaults", "novelty_statement"]) or defaults["novelty_statement"]
        ),
        "data_availability": choose_statement(
            str(get_nested(intake, ["release_policy", "data_availability_final_text"]) or ""),
            str(
                get_nested(intake, ["recommended_defaults", "data_availability"])
                or defaults["data_availability"]
            ),
        ),
        "code_availability": choose_statement(
            str(get_nested(intake, ["release_policy", "code_availability_final_text"]) or ""),
            str(
                get_nested(intake, ["recommended_defaults", "code_availability"])
                or defaults["code_availability"]
            ),
        ),
        "reproducibility_statement": str(
            get_nested(intake, ["recommended_defaults", "reproducibility_statement"])
            or defaults["reproducibility_statement"]
        ),
        "ethics_safety_statement": choose_statement(
            str(get_nested(intake, ["disclosures", "ethics_statement_override"]) or ""),
            str(
                get_nested(intake, ["recommended_defaults", "ethics_safety_statement"])
                or defaults["ethics_safety_statement"]
            ),
        ),
        "funding_statement": choose_statement(
            str(get_nested(intake, ["disclosures", "funding_statement"]) or ""),
            str(defaults["funding_statement_placeholder"]),
        ),
        "conflict_statement": choose_statement(
            str(get_nested(intake, ["disclosures", "conflict_statement"]) or ""),
            str(defaults["conflict_statement_placeholder"]),
        ),
        "author_contribution_statement": choose_statement(
            str(get_nested(intake, ["authors", "author_contribution_statement"]) or ""),
            str(defaults["author_contribution_placeholder"]),
        ),
        "acknowledgements": choose_statement(
            str(get_nested(intake, ["authors", "acknowledgements"]) or ""),
            str(defaults["acknowledgements_placeholder"]),
        ),
        "selected_track": choose_track(intake, defaults),
        "author_names": author_names,
        "affiliations": affiliations,
        "corresponding_author_name": str(
            get_nested(intake, ["authors", "corresponding_author_name"]) or ""
        ),
        "corresponding_author_email": str(
            get_nested(intake, ["authors", "corresponding_author_email"]) or ""
        ),
        "orcid_required": get_nested(intake, ["authors", "orcid_required"]),
        "code_release_timing": str(get_nested(intake, ["release_policy", "code_release_timing"]) or ""),
        "submission_has_anonymized_repo": get_nested(
            intake, ["release_policy", "submission_has_anonymized_repo"]
        ),
        "repo_url": str(get_nested(intake, ["release_policy", "repo_url"]) or ""),
        "repository_link_allowed": get_nested(intake, ["venue", "repository_link_allowed"]),
        "supplementary_anonymity_required": get_nested(
            intake, ["venue", "supplementary_anonymity_required"]
        ),
        "remaining_missing_fields": missing,
    }


def build_handoff_markdown(
    rendered: dict[str, Any],
    output_json_path: Path,
    output_md_path: Path,
) -> str:
    lines = [
        "# Submission Intake Handoff 61day",
        "",
        f"- Status: `{rendered['status']}`",
        f"- Missing field count: `{rendered['missing_field_count']}`",
        f"- Source intake: `{rendered['source_intake']}`",
        f"- Rendered metadata JSON: `{output_json_path}`",
        f"- This handoff note: `{output_md_path}`",
        "",
        "## Operational Summary",
        f"- Submission mode: `{rendered['submission_mode'] or 'pending'}`",
        f"- Venue: `{rendered['venue_name'] or 'pending'}`",
        f"- Review mode: `{rendered['venue_review_mode'] or 'pending'}`",
        f"- Page limit: `{rendered['venue_main_page_limit'] or 'pending'}`",
        f"- Abstract limit: `{rendered['venue_abstract_word_limit'] or 'pending'}`",
        f"- Keyword limit: `{rendered['venue_keyword_limit'] or 'pending'}`",
        "",
        "## Selected Portal Payload",
        f"- Selected title: `{rendered['selected_title']}`",
        f"- Short title: `{rendered['short_title']}`",
        f"- Keywords: `{', '.join(rendered['selected_keywords'])}`",
        f"- Abstract variant: `{rendered['chosen_abstract_variant'] or 'pending'}`",
        f"- Abstract source doc: `{rendered['abstract_source_doc']}`",
        f"- Track: `{rendered['selected_track']}`",
        "",
        "## Statements",
        "",
        "### One-line Summary",
        f"`{rendered['one_line_summary']}`",
        "",
        "### Scope Statement",
        f"`{rendered['scope_statement']}`",
        "",
        "### Novelty Statement",
        f"`{rendered['novelty_statement']}`",
        "",
        "### Data Availability",
        f"`{rendered['data_availability']}`",
        "",
        "### Code Availability",
        f"`{rendered['code_availability']}`",
        "",
        "### Reproducibility",
        f"`{rendered['reproducibility_statement']}`",
        "",
        "### Ethics / Safety",
        f"`{rendered['ethics_safety_statement']}`",
        "",
        "### Funding",
        f"`{rendered['funding_statement']}`",
        "",
        "### Conflict of Interest",
        f"`{rendered['conflict_statement']}`",
        "",
        "### Author Contribution",
        f"`{rendered['author_contribution_statement']}`",
        "",
        "### Acknowledgements",
        f"`{rendered['acknowledgements']}`",
        "",
        "## Author and Release Inputs",
        f"- Authors: `{', '.join(rendered['author_names']) if rendered['author_names'] else 'pending'}`",
        f"- Affiliations: `{'; '.join(rendered['affiliations']) if rendered['affiliations'] else 'pending'}`",
        f"- Corresponding author: `{rendered['corresponding_author_name'] or 'pending'}`",
        f"- Corresponding email: `{rendered['corresponding_author_email'] or 'pending'}`",
        f"- Code release timing: `{rendered['code_release_timing'] or 'pending'}`",
        f"- Anonymous repo: `{rendered['submission_has_anonymized_repo']}`",
        f"- Repo URL: `{rendered['repo_url'] or 'pending'}`",
        "",
        "## Remaining Missing Fields",
    ]

    total_missing = int(rendered["missing_field_count"])
    if total_missing == 0:
        lines.append("- none")
    else:
        remaining = rendered["remaining_missing_fields"]
        for section in (
            "venue_policy",
            "author_metadata",
            "disclosures",
            "release_policy",
            "portal_selection",
        ):
            items = remaining.get(section, [])
            lines.append(f"- {section}: `{len(items)}`")
            for item in items:
                lines.append(f"  - {item}")

    lines.extend(
        [
            "",
            "## Next Actions",
        ]
    )
    if total_missing == 0:
        lines.extend(
            [
                "1. Use the rendered metadata JSON as the portal copy source.",
                "2. Keep the abstract source document aligned with the selected variant.",
                "3. Re-run the renderer if venue mode or release policy changes.",
            ]
        )
    else:
        lines.extend(
            [
                "1. Fill the remaining venue, author, and release-policy blanks in the intake JSON.",
                "2. Run `python3 /Users/seoki/Desktop/research/examples/validate_submission_intake_61day.py` until the blocker count reaches zero.",
                "3. Re-run `python3 /Users/seoki/Desktop/research/examples/render_submission_intake_61day.py` to refresh the portal handoff files.",
            ]
        )

    return "\n".join(lines) + "\n"


def build_copy_paste_markdown(rendered: dict[str, Any], output_path: Path) -> str:
    review_mode = rendered["venue_review_mode"] or rendered["submission_mode"] or "pending"
    venue_name = rendered["venue_name"] or "pending"
    author_line = ", ".join(rendered["author_names"]) if rendered["author_names"] else "pending"
    affiliation_line = "; ".join(rendered["affiliations"]) if rendered["affiliations"] else "pending"
    lines = [
        "# Submission Portal Copy-Paste Filled 61day",
        "",
        f"- Status: `{rendered['status']}`",
        f"- Venue: `{venue_name}`",
        f"- Review mode: `{review_mode}`",
        f"- Generated from: `{rendered['source_intake']}`",
        f"- Output: `{output_path}`",
        "",
        "## Core Fields",
        "",
        "### Title",
        f"`{rendered['selected_title']}`",
        "",
        "### Short Title",
        f"`{rendered['short_title']}`",
        "",
        "### Keywords",
        f"`{', '.join(rendered['selected_keywords'])}`",
        "",
        "### Track / Subject Area",
        f"`{rendered['selected_track']}`",
        "",
        "### Abstract Source",
        f"`{rendered['chosen_abstract_variant'] or 'pending'}` -> `{rendered['abstract_source_doc']}`",
        "",
        "### One-line Summary",
        f"`{rendered['one_line_summary']}`",
        "",
        "### Novelty Statement",
        f"`{rendered['novelty_statement']}`",
        "",
        "### Scope Statement",
        f"`{rendered['scope_statement']}`",
        "",
        "### Ethics / Safety",
        f"`{rendered['ethics_safety_statement']}`",
        "",
        "### Data Availability",
        f"`{rendered['data_availability']}`",
        "",
        "### Code Availability",
        f"`{rendered['code_availability']}`",
        "",
        "### Reproducibility",
        f"`{rendered['reproducibility_statement']}`",
        "",
        "### Funding",
        f"`{rendered['funding_statement']}`",
        "",
        "### Conflict of Interest",
        f"`{rendered['conflict_statement']}`",
        "",
        "## Author Fields",
        f"- Authors: `{author_line}`",
        f"- Affiliations: `{affiliation_line}`",
        f"- Corresponding author: `{rendered['corresponding_author_name'] or 'pending'}`",
        f"- Corresponding email: `{rendered['corresponding_author_email'] or 'pending'}`",
        "",
        "## Release Fields",
        f"- Code release timing: `{rendered['code_release_timing'] or 'pending'}`",
        f"- Anonymous repo: `{rendered['submission_has_anonymized_repo']}`",
        f"- Repo URL: `{rendered['repo_url'] or 'pending'}`",
        "",
        "## Operator Notes",
    ]

    lowered_mode = review_mode.lower()
    if "blind" in lowered_mode:
        lines.extend(
            [
                "- Keep author names, affiliations, acknowledgements, and contribution text out of the blinded manuscript unless the venue explicitly requests them in separate metadata fields.",
                "- Check whether repository links and supplementary uploads must remain anonymous before pasting availability text.",
            ]
        )
    elif lowered_mode == "pending":
        lines.extend(
            [
                "- Review mode is still pending, so do not finalize author-facing or blind-review-only wording yet.",
                "- Once the venue policy is filled, re-run the pipeline and use the updated operator notes.",
            ]
        )
    else:
        lines.extend(
            [
                "- Restore full author, affiliation, acknowledgement, and contribution metadata in the camera-ready package.",
                "- Confirm funding and conflict statements match the final venue wording before portal submission.",
            ]
        )

    return "\n".join(lines) + "\n"


def build_fill_queue_markdown(rendered: dict[str, Any], output_path: Path) -> str:
    missing = rendered["remaining_missing_fields"]
    total_missing = int(rendered["missing_field_count"])

    if total_missing == 0:
        lines = [
            "# Submission Intake Fill Queue 61day",
            "",
            f"- Status: `{rendered['status']}`",
            f"- Missing field count: `{rendered['missing_field_count']}`",
            f"- Generated from: `{rendered['source_intake']}`",
            f"- Output: `{output_path}`",
            "",
            "## Fill Queue",
            "- none",
            "",
            "## Pre-Submit Check",
            "1. Run `bash /Users/seoki/Desktop/research/examples/run_submission_hard_gate_61day.sh` and confirm `PASS`.",
            "2. Paste from `submission_portal_copy_paste_filled_61day.md` and `submission_intake_handoff_61day.md`.",
            "3. Replace any provisional metadata with final venue-confirmed values before final submit.",
        ]
        return "\n".join(lines) + "\n"

    lines = [
        "# Submission Intake Fill Queue 61day",
        "",
        f"- Status: `{rendered['status']}`",
        f"- Missing field count: `{rendered['missing_field_count']}`",
        f"- Generated from: `{rendered['source_intake']}`",
        f"- Output: `{output_path}`",
        "",
        "## Fill Order",
        "1. Venue policy",
        "2. Author metadata",
        "3. Release policy",
        "4. Portal selection",
        "",
        "## Venue Policy",
    ]

    venue_help = {
        "venue.name": "Example: `IEEE OCEANS 2026`",
        "venue.type": "Choose one: `conference`, `journal`, `workshop`, `internal`",
        "venue.template_type": "Choose one: `LaTeX`, `Word`, `portal-only`",
        "venue.review_mode": "Choose one: `double-blind`, `single-blind`, `open`",
        "venue.main_page_limit": "Example: `8 pages excluding references`",
        "venue.supplementary_policy": "Example: `allowed, anonymous PDF only`",
        "venue.abstract_word_limit": "Example: `150`",
        "venue.keyword_limit": "Example: `5`",
    }
    author_help = {
        "authors.author_names": "Use a JSON array, e.g. `[\"Author One\", \"Author Two\"]`",
        "authors.affiliations": "Use a JSON array aligned to the author list.",
        "authors.corresponding_author_name": "Use the full name.",
        "authors.corresponding_author_email": "Use the final submission email.",
    }
    release_help = {
        "release_policy.submission_has_anonymized_repo": "Choose `true` or `false` based on blind-review policy.",
        "release_policy.code_release_timing": "Example: `private during review, public at camera-ready`",
    }
    portal_help = {
        "portal_selection.chosen_abstract_variant": "Choose one: `100-word`, `150-word`, `250-word`, `long`",
        "portal_selection.chosen_keyword_set": "Choose one: `primary`, `extended`",
    }

    for item in missing["venue_policy"]:
        lines.append(f"- `{item}`")
        lines.append(f"  expected: {venue_help.get(item, 'fill required')}")

    lines.extend(["", "## Author Metadata"])
    for item in missing["author_metadata"]:
        lines.append(f"- `{item}`")
        lines.append(f"  expected: {author_help.get(item, 'fill required')}")

    lines.extend(["", "## Disclosures"])
    if not missing["disclosures"]:
        lines.append("- none")
    else:
        for item in missing["disclosures"]:
            lines.append(f"- `{item}`")

    lines.extend(["", "## Release Policy"])
    for item in missing["release_policy"]:
        lines.append(f"- `{item}`")
        lines.append(f"  expected: {release_help.get(item, 'fill required')}")

    lines.extend(["", "## Portal Selection"])
    for item in missing["portal_selection"]:
        lines.append(f"- `{item}`")
        lines.append(f"  expected: {portal_help.get(item, 'fill required')}")

    lines.extend(
        [
            "",
            "## Run After Filling",
            "1. `bash /Users/seoki/Desktop/research/examples/run_submission_intake_pipeline_61day.sh`",
            "2. Confirm `submission_intake_validation_61day.md` shows `READY`.",
            "3. Paste from `submission_portal_copy_paste_filled_61day.md` and `submission_intake_handoff_61day.md`.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    base_metadata_path = Path(args.base_metadata)
    output_json_path = Path(args.output_json)
    output_md_path = Path(args.output_md)
    output_copy_md_path = Path(args.output_copy_md)
    output_queue_md_path = Path(args.output_queue_md)

    with input_path.open("r", encoding="utf-8") as handle:
        intake = json.load(handle)
    with base_metadata_path.open("r", encoding="utf-8") as handle:
        defaults = json.load(handle)

    missing = validate(intake)
    rendered = build_rendered_metadata(intake, defaults, missing, input_path)
    handoff_md = build_handoff_markdown(rendered, output_json_path, output_md_path)
    copy_md = build_copy_paste_markdown(rendered, output_copy_md_path)
    queue_md = build_fill_queue_markdown(rendered, output_queue_md_path)

    output_json_path.write_text(
        json.dumps(rendered, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    output_md_path.write_text(handoff_md, encoding="utf-8")
    output_copy_md_path.write_text(copy_md, encoding="utf-8")
    output_queue_md_path.write_text(queue_md, encoding="utf-8")

    print(f"Status: {rendered['status']}")
    print(f"Missing field count: {rendered['missing_field_count']}")
    print(f"Rendered JSON: {output_json_path}")
    print(f"Handoff note: {output_md_path}")
    print(f"Copy-paste note: {output_copy_md_path}")
    print(f"Fill queue note: {output_queue_md_path}")


if __name__ == "__main__":
    main()
