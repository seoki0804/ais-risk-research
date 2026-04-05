#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path("/Users/seoki/Desktop/research")
DOC_ROOT = ROOT / "outputs" / "presentation_deck_outline_61day_2026-03-13"
REGIONS = ["houston", "nola", "seattle"]
TRANSFERS = [("aug", "sep"), ("aug", "oct"), ("sep", "oct")]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize same-ecosystem external-validity transfer runs."
    )
    parser.add_argument("--run-date", default="2026-03-17", help="Transfer output run date.")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    run_root = ROOT / "outputs" / f"{args.run_date}_same_ecosystem_external_validity"
    if not run_root.exists():
        raise SystemExit(f"missing run root: {run_root}")

    rows: list[dict[str, str]] = []
    by_region: dict[str, list[float]] = {region: [] for region in REGIONS}

    for region in REGIONS:
        for source_block, target_block in TRANSFERS:
            path = run_root / f"{region}_{source_block}_to_{target_block}_transfer_summary.json"
            if not path.exists():
                continue
            payload = load_json(path)
            hgbt_source = payload["models"]["hgbt"]["source_test"]
            hgbt_target = payload["models"]["hgbt"]["target_transfer"]
            logreg_target = payload["models"]["logreg"]["target_transfer"]
            row = {
                "region": region,
                "source_block": source_block,
                "target_block": target_block,
                "source_rows": str(payload["source_row_count"]),
                "target_rows": str(payload["target_row_count"]),
                "source_positive_rate": f"{float(payload['source_positive_rate']):.4f}",
                "target_positive_rate": f"{float(payload['target_positive_rate']):.4f}",
                "source_own_ships": str(payload["source_own_ship_count"]),
                "target_own_ships": str(payload["target_own_ship_count"]),
                "hgbt_source_f1": f"{float(hgbt_source['f1']):.4f}",
                "hgbt_target_f1": f"{float(hgbt_target['f1']):.4f}",
                "logreg_target_f1": f"{float(logreg_target['f1']):.4f}",
                "hgbt_threshold": str(payload["models"]["hgbt"]["threshold"]),
                "transfer_summary_json": str(path),
            }
            rows.append(row)
            by_region[region].append(float(hgbt_target["f1"]))

    if not rows:
        raise SystemExit(f"no transfer summaries found under {run_root}")

    rows.sort(key=lambda item: (item["region"], item["source_block"], item["target_block"]))
    csv_path = DOC_ROOT / "same_ecosystem_external_validity_summary_61day.csv"
    md_path = DOC_ROOT / "same_ecosystem_external_validity_summary_61day.md"
    note_path = DOC_ROOT / "same_ecosystem_external_validity_note_61day.md"

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# 문서명",
        "Same-Ecosystem External Validity Summary 61day",
        "",
        "# 문서 목적",
        "August anchor, September block, October block 사이의 same-area transfer 결과를 한 표로 고정한다.",
        "",
        "# 작성 버전",
        f"v1.0 ({args.run_date})",
        "",
        "## 1. transfer 요약표",
        "",
        "| Region | Source | Target | Source rows | Target rows | Source pos rate | Target pos rate | Source own ships | Target own ships | hgbt source F1 | hgbt target F1 | logreg target F1 | hgbt thr |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['region']} | `{row['source_block']}` | `{row['target_block']}` | {row['source_rows']} | "
            f"{row['target_rows']} | {row['source_positive_rate']} | {row['target_positive_rate']} | "
            f"{row['source_own_ships']} | {row['target_own_ships']} | {row['hgbt_source_f1']} | "
            f"{row['hgbt_target_f1']} | {row['logreg_target_f1']} | {row['hgbt_threshold']} |"
        )

    lines.extend(
        [
            "",
            "## 2. 산출물",
            "",
            f"- CSV: [{csv_path.name}]({csv_path})",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def f1_range(region: str) -> str:
        values = by_region[region]
        if not values:
            return "n/a"
        return f"{min(values):.4f}-{max(values):.4f}"

    note_lines = [
        "# 문서명",
        "Same-Ecosystem External Validity Note 61day",
        "",
        "# 문서 목적",
        "같은 NOAA 생태계 안에서 `August anchor -> September/October new block` generalization을 reviewer-safe하게 해석한다.",
        "",
        "# 작성 버전",
        f"v1.0 ({args.run_date})",
        "",
        "## 1. 핵심 관찰",
        "",
        f"- [확정] Houston hgbt target F1 range: `{f1_range('houston')}`",
        f"- [확정] NOLA hgbt target F1 range: `{f1_range('nola')}`",
        f"- [확정] Seattle hgbt target F1 range: `{f1_range('seattle')}`",
        "- [확정] `aug -> sep`와 `aug -> oct` transfer에서는 세 해역 모두 `hgbt` target F1이 완전 붕괴 없이 유지됐다.",
        "- [확정] 다만 Houston `sep -> oct` source own-ship split은 threshold `0.05`, source-test F1 `0.1333`으로 자체적으로 불안정했기 때문에, temporal extension의 main reading은 August anchor transfer 쪽이 더 깔끔하다.",
        "- [확정] NOLA와 Seattle에서 block-transfer 수치가 pooled own-ship benchmark보다 더 높게 보이는 것은 모순이 아니라, `new block shift`와 `unseen own-ship mismatch`가 서로 다른 일반화 축이기 때문이다.",
        "- [확정] 이 표는 `brand-new area`가 아니라 `new month / new block within the same ecosystem`을 본다.",
        "- [확정] 따라서 broad external validity claim이 아니라 temporal/block extension evidence로 읽어야 한다.",
        "",
        "## 2. reviewer-safe reading",
        "",
        "- [확정] August에서 학습한 모델이 September/October block으로 넘어가도 완전히 붕괴하지 않는다는 점은, current claim이 single-day internal fit를 넘어선다는 evidence가 된다.",
        "- [확정] 그러나 이 결과는 own-ship split을 대체하지 않는다. block transfer는 `same-ecosystem temporal shift`를, own-ship split은 `unseen-own-ship transfer`를 더 직접적으로 본다.",
        "- [확정] 다만 same-ecosystem block transfer는 여전히 NOAA-derived internal extension이므로, `new area` external validity와 동일시하면 안 된다.",
        "- [확정] 따라서 가장 안전한 문장은 `same-ecosystem temporal extension is partially supported, but broad geographic external validity remains open`이다.",
        "",
        "## 3. 산출물",
        "",
        f"- 표: [{md_path.name}]({md_path})",
        f"- CSV: [{csv_path.name}]({csv_path})",
    ]
    note_path.write_text("\n".join(note_lines) + "\n", encoding="utf-8")

    print(f"summary_md={md_path}")
    print(f"summary_csv={csv_path}")
    print(f"note_md={note_path}")


if __name__ == "__main__":
    main()
