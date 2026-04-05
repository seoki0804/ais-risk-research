from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


OUTPUT_DIR = Path(
    "/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13"
)
CSV_OUTPUT = OUTPUT_DIR / "external_validity_interval_summary_61day.csv"
MD_OUTPUT = OUTPUT_DIR / "external_validity_interval_note_61day.md"
BOOTSTRAP_SEED = 20260320
BOOTSTRAP_ITERATIONS = 4000


@dataclass(frozen=True)
class SliceConfig:
    label: str
    category: str
    prediction_csv: Path
    summary_json: Path
    summary_kind: str
    evidence_note: str


SLICES: list[SliceConfig] = [
    SliceConfig(
        label="NY/NJ pooled 2023",
        category="new_area_pooled",
        prediction_csv=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_pooled_refresh/ny_nj_2023/ny_nj_2023_own_ship_test_predictions.csv"
        ),
        summary_json=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_pooled_refresh/ny_nj_2023/ny_nj_2023_own_ship_summary.json"
        ),
        summary_kind="pooled_own_ship",
        evidence_note="low-support pooled new-area slice; interval is intentionally wide",
    ),
    SliceConfig(
        label="LA/LB pooled 2023",
        category="new_area_pooled",
        prediction_csv=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_pooled_refresh/la_lb_2023/la_lb_2023_own_ship_test_predictions.csv"
        ),
        summary_json=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_pooled_refresh/la_lb_2023/la_lb_2023_own_ship_summary.json"
        ),
        summary_kind="pooled_own_ship",
        evidence_note="very low-support pooled new-area slice; interval is widest here",
    ),
    SliceConfig(
        label="NY/NJ pooled 2024",
        category="cross_year_pooled",
        prediction_csv=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_pooled_refresh/ny_nj_2024/ny_nj_2024_own_ship_test_predictions.csv"
        ),
        summary_json=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_pooled_refresh/ny_nj_2024/ny_nj_2024_own_ship_summary.json"
        ),
        summary_kind="pooled_own_ship",
        evidence_note="cross-year pooled benchmark; still moderate-width because positives remain limited",
    ),
    SliceConfig(
        label="Seattle pooled 2024",
        category="cross_year_pooled",
        prediction_csv=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_pooled_refresh/seattle_2024/seattle_2024_own_ship_test_predictions.csv"
        ),
        summary_json=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_pooled_refresh/seattle_2024/seattle_2024_own_ship_summary.json"
        ),
        summary_kind="pooled_own_ship",
        evidence_note="cross-year pooled benchmark; narrower than the low-support new-area pooled slices",
    ),
    SliceConfig(
        label="NY/NJ 2023->2024 transfer",
        category="cross_year_transfer",
        prediction_csv=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_cross_year_ny_nj_cross_year_ny_nj_transfer/ny_nj_2023_to_2024_target_predictions.csv"
        ),
        summary_json=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_cross_year_ny_nj_cross_year_ny_nj_transfer/ny_nj_2023_to_2024_transfer_summary.json"
        ),
        summary_kind="target_transfer",
        evidence_note="weaker cross-year transfer leg, but interval still stays above immediate-collapse territory",
    ),
    SliceConfig(
        label="NY/NJ 2024->2023 transfer",
        category="cross_year_transfer",
        prediction_csv=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_cross_year_ny_nj_cross_year_ny_nj_transfer/ny_nj_2024_to_2023_target_predictions.csv"
        ),
        summary_json=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_cross_year_ny_nj_cross_year_ny_nj_transfer/ny_nj_2024_to_2023_transfer_summary.json"
        ),
        summary_kind="target_transfer",
        evidence_note="stronger reverse transfer leg with visibly tighter interval",
    ),
    SliceConfig(
        label="Seattle 2023->2024 transfer",
        category="cross_year_transfer",
        prediction_csv=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_cross_year_seattle_cross_year_seattle_transfer/seattle_2023_to_2024_target_predictions.csv"
        ),
        summary_json=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_cross_year_seattle_cross_year_seattle_transfer/seattle_2023_to_2024_transfer_summary.json"
        ),
        summary_kind="target_transfer",
        evidence_note="large-enough transfer slice with comparatively compact interval",
    ),
    SliceConfig(
        label="Seattle 2024->2023 transfer",
        category="cross_year_transfer",
        prediction_csv=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_cross_year_seattle_cross_year_seattle_transfer/seattle_2024_to_2023_target_predictions.csv"
        ),
        summary_json=Path(
            "/Users/seoki/Desktop/research/outputs/2026-03-18_leakfix_cross_year_seattle_cross_year_seattle_transfer/seattle_2024_to_2023_transfer_summary.json"
        ),
        summary_kind="target_transfer",
        evidence_note="most stable transfer leg in the current external-validity spine",
    ),
]


def load_summary_f1(path: Path, summary_kind: str) -> float:
    with path.open() as f:
        data = json.load(f)
    if summary_kind == "pooled_own_ship":
        return float(data["models"]["hgbt"]["f1"])
    if summary_kind == "target_transfer":
        return float(data["models"]["hgbt"]["target_transfer"]["f1"])
    raise ValueError(f"Unsupported summary kind: {summary_kind}")


def bootstrap_f1_interval(
    prediction_csv: Path, n_boot: int, seed: int
) -> tuple[float, float, float, int, int, int]:
    df = pd.read_csv(prediction_csv)
    y = df["label_future_conflict"].to_numpy(dtype=np.int8)
    pred = df["hgbt_pred"].to_numpy(dtype=np.int8)
    n = len(df)
    rng = np.random.default_rng(seed)

    tp_mask = ((y == 1) & (pred == 1)).astype(np.int16)
    fp_mask = ((y == 0) & (pred == 1)).astype(np.int16)
    fn_mask = ((y == 1) & (pred == 0)).astype(np.int16)

    probs = np.full(n, 1.0 / n)
    weights = rng.multinomial(n, probs, size=n_boot)

    tp = weights @ tp_mask
    fp = weights @ fp_mask
    fn = weights @ fn_mask
    denom = 2 * tp + fp + fn
    boot_f1 = np.divide(
        2 * tp, denom, out=np.zeros_like(tp, dtype=float), where=denom > 0
    )

    tp0 = int(tp_mask.sum())
    fp0 = int(fp_mask.sum())
    fn0 = int(fn_mask.sum())
    point = (2 * tp0) / (2 * tp0 + fp0 + fn0) if (2 * tp0 + fp0 + fn0) else 0.0
    lo, hi = np.quantile(boot_f1, [0.025, 0.975])
    return float(point), float(lo), float(hi), n, int(y.sum()), int(pred.sum())


def format_float(value: float) -> str:
    return f"{value:.4f}"


def write_markdown(rows: list[dict[str, str]]) -> None:
    header = [
        "# 문서명",
        "External Validity Interval Note 61day",
        "",
        "# 문서 목적",
        "pooled new-area / cross-year pooled / cross-year transfer headline 수치에 대해 fixed-prediction row-bootstrap 95% F1 interval을 같이 고정한다.",
        "",
        "# 대상 독자",
        "주저자, reviewer 대응 작성자, 본문/표 편집자",
        "",
        "# 작성 버전",
        "v1.0 (2026-03-20)",
        "",
        "## 1. 계산 원칙",
        "",
        f"- [확정] 각 slice의 이미 잠긴 `hgbt_pred` test prediction row를 `{BOOTSTRAP_ITERATIONS}`회 row-bootstrap 재표집했다.",
        "- [확정] interval은 `fixed model / fixed threshold / fixed prediction` 조건에서의 표본 민감도를 요약하며, retraining uncertainty나 portable transfer guarantee를 뜻하지 않는다.",
        "- [확정] same-ecosystem month/block transfer는 여러 block range를 한 줄로 읽는 보조 spine이므로, 이번 interval 표는 pooled/transfer headline 8개 slice에만 붙였다.",
        "",
        "## 2. Summary Table",
        "",
        "| slice | category | test rows | positives | predicted positives | hgbt F1 | 95% row-bootstrap CI | reading |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        header.append(
            f"| {row['label']} | {row['category']} | {row['test_rows']} | {row['positives']} | "
            f"{row['predicted_positives']} | {row['hgbt_f1']} | {row['ci_95']} | {row['reading']} |"
        )
    header.extend(
        [
            "",
            "## 3. Reviewer-Safe Reading",
            "",
            "- [확정] low-support pooled new-area slices는 interval이 넓다. 따라서 `NY/NJ 2023`, `LA/LB 2023`은 workable pooled evidence이지만 narrow-precision claim으로 쓰면 과장이다.",
            "- [확정] cross-year pooled slices는 여전히 moderate-width interval을 가지며, 특히 `NY/NJ 2024`는 workable but not closed로 읽는 편이 안전하다.",
            "- [확정] cross-year transfer 4개 leg는 pooled new-area보다 interval이 더 조밀해, current external-validity spine의 주력 evidence가 pooled/transfer backbone이라는 해석을 지지한다.",
            "",
            "## 4. Entry Points",
            "",
            "- [script](/Users/seoki/Desktop/research/examples/compute_external_validity_intervals_61day.py)",
            "- [csv](/Users/seoki/Desktop/research/outputs/presentation_deck_outline_61day_2026-03-13/external_validity_interval_summary_61day.csv)",
        ]
    )
    MD_OUTPUT.write_text("\n".join(header) + "\n")


def main() -> None:
    rows: list[dict[str, str]] = []
    for cfg in SLICES:
        point, lo, hi, n_rows, positives, pred_pos = bootstrap_f1_interval(
            cfg.prediction_csv,
            n_boot=BOOTSTRAP_ITERATIONS,
            seed=BOOTSTRAP_SEED,
        )
        summary_point = load_summary_f1(cfg.summary_json, cfg.summary_kind)
        if abs(point - summary_point) > 1e-9:
            raise ValueError(
                f"Point estimate mismatch for {cfg.label}: bootstrap={point}, summary={summary_point}"
            )
        rows.append(
            {
                "label": cfg.label,
                "category": cfg.category,
                "test_rows": str(n_rows),
                "positives": str(positives),
                "predicted_positives": str(pred_pos),
                "hgbt_f1": format_float(point),
                "ci_low": format_float(lo),
                "ci_high": format_float(hi),
                "ci_95": f"[{format_float(lo)}, {format_float(hi)}]",
                "reading": cfg.evidence_note,
                "prediction_csv": str(cfg.prediction_csv),
                "summary_json": str(cfg.summary_json),
                "bootstrap_seed": str(BOOTSTRAP_SEED),
                "bootstrap_iterations": str(BOOTSTRAP_ITERATIONS),
            }
        )

    with CSV_OUTPUT.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "label",
                "category",
                "test_rows",
                "positives",
                "predicted_positives",
                "hgbt_f1",
                "ci_low",
                "ci_high",
                "ci_95",
                "reading",
                "prediction_csv",
                "summary_json",
                "bootstrap_seed",
                "bootstrap_iterations",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    write_markdown(rows)
    print(f"Wrote {CSV_OUTPUT}")
    print(f"Wrote {MD_OUTPUT}")


if __name__ == "__main__":
    main()
