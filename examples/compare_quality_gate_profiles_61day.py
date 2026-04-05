from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ais_risk.own_ship_quality_gate import apply_own_ship_quality_gate, load_own_ship_candidate_rows


def _parse_entry(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("expected NAME=PATH")
    name, path_value = raw.split("=", 1)
    return name.strip(), Path(path_value).expanduser()


def _passed_mmsis(rows: list[dict[str, object]]) -> list[str]:
    return [str(row.get("mmsi") or "") for row in rows if bool(row.get("gate_passed"))]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare strict and relaxed quality-gate profiles.")
    parser.add_argument("--entry", action="append", required=True, type=_parse_entry, help="NAME=path/to/own_ship_candidates.csv")
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-md", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    profiles = [
        ("strict_0p30", 0.30),
        ("reviewer_safe_0p25", 0.25),
        ("exploratory_0p20", 0.20),
    ]

    rows_out: list[dict[str, object]] = []
    per_entry_passes: dict[str, dict[str, list[str]]] = {}

    for name, path in args.entry:
        candidate_rows = load_own_ship_candidate_rows(path)
        per_entry_passes[name] = {}
        for profile_name, movement_threshold in profiles:
            gated_rows = apply_own_ship_quality_gate(candidate_rows, min_movement_ratio=movement_threshold)
            passed = _passed_mmsis(gated_rows)
            per_entry_passes[name][profile_name] = passed
            rows_out.append(
                {
                    "region_case": name,
                    "profile": profile_name,
                    "movement_ratio_threshold": movement_threshold,
                    "candidate_count": len(gated_rows),
                    "passed_count": len(passed),
                    "pass_ratio": (len(passed) / len(gated_rows)) if gated_rows else 0.0,
                    "recommended_mmsi": passed[0] if passed else "",
                    "passed_mmsis": ",".join(passed),
                }
            )

    strict_vs_relaxed_rows: list[dict[str, object]] = []
    for name, _ in args.entry:
        strict = set(per_entry_passes[name]["strict_0p30"])
        reviewer_safe = set(per_entry_passes[name]["reviewer_safe_0p25"])
        exploratory = set(per_entry_passes[name]["exploratory_0p20"])
        strict_vs_relaxed_rows.append(
            {
                "region_case": name,
                "new_at_0p25": ",".join(sorted(reviewer_safe - strict)),
                "new_at_0p20": ",".join(sorted(exploratory - reviewer_safe)),
            }
        )

    output_csv = Path(args.output_csv)
    output_md = Path(args.output_md)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(rows_out)

    lines = [
        "# Quality Gate Profile Comparison 61day",
        "",
        "| region/case | profile | movement threshold | candidates | passed | pass ratio | recommended MMSI | passed MMSIs |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in rows_out:
        lines.append(
            "| {region_case} | {profile} | {movement_ratio_threshold:.2f} | {candidate_count} | {passed_count} | {pass_ratio:.3f} | {recommended_mmsi} | {passed_mmsis} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Newly Admitted MMSIs Under Relaxation",
            "",
            "| region/case | new at 0.25 | new at 0.20 |",
            "|---|---|---|",
        ]
    )
    for row in strict_vs_relaxed_rows:
        lines.append("| {region_case} | {new_at_0p25} | {new_at_0p20} |".format(**row))

    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"rows={len(rows_out)}")
    print(f"csv={output_csv}")
    print(f"md={output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
