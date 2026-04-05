from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


MODEL_DETAIL_FIELDS = [
    "source_region",
    "model_name",
    "pair_count",
    "completed_pair_count",
    "negative_pair_count",
    "mean_delta_f1_fixed_threshold",
    "min_delta_f1_fixed_threshold",
    "max_target_ece",
    "max_target_ece_gate",
    "all_targets_ece_pass",
    "max_negative_pairs_allowed",
    "negative_pair_gate_pass",
    "combined_pass",
]

SOURCE_SUMMARY_FIELDS = [
    "source_region",
    "recommended_model",
    "recommended_combined_pass",
    "recommended_negative_pair_count",
    "recommended_max_target_ece",
    "recommended_mean_delta_f1_fixed_threshold",
    "recommended_min_delta_f1_fixed_threshold",
    "best_combined_model",
    "best_combined_negative_pair_count",
    "best_combined_max_target_ece",
    "best_combined_mean_delta_f1_fixed_threshold",
    "best_combined_min_delta_f1_fixed_threshold",
    "best_combined_pass",
    "model_count",
    "target_pair_count",
]


def _parse_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


def _select_best_combined(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [row for row in rows if bool(row.get("combined_pass"))]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda row: (
            int(row.get("negative_pair_count", 10**9)),
            -float(row.get("min_delta_f1_fixed_threshold", -10**9)),
            -float(row.get("mean_delta_f1_fixed_threshold", -10**9)),
        ),
    )[0]


def _summarize_model_rows(
    source_region: str,
    rows: list[dict[str, str]],
    max_target_ece: float,
    max_negative_pairs_allowed: int,
) -> list[dict[str, Any]]:
    model_names = sorted({str(row.get("model_name", "")).strip() for row in rows if str(row.get("model_name", "")).strip()})
    model_rows: list[dict[str, Any]] = []
    for model_name in model_names:
        model_pairs = [row for row in rows if str(row.get("model_name", "")).strip() == model_name]
        completed_pairs = [row for row in model_pairs if str(row.get("status", "")).strip() == "completed"]
        deltas = [_safe_float(row.get("delta_f1")) for row in completed_pairs]
        eces = [_safe_float(row.get("target_ece")) for row in completed_pairs]
        deltas = [float(value) for value in deltas if value is not None]
        eces = [float(value) for value in eces if value is not None]
        negative_pair_count = sum(1 for value in deltas if float(value) < 0.0)
        max_ece_value = max(eces) if eces else None
        all_targets_ece_pass = (max_ece_value is not None) and (float(max_ece_value) <= float(max_target_ece))
        negative_pair_gate_pass = int(negative_pair_count) <= int(max_negative_pairs_allowed)
        model_rows.append(
            {
                "source_region": source_region,
                "model_name": model_name,
                "pair_count": len(model_pairs),
                "completed_pair_count": len(completed_pairs),
                "negative_pair_count": int(negative_pair_count),
                "mean_delta_f1_fixed_threshold": (sum(deltas) / len(deltas)) if deltas else None,
                "min_delta_f1_fixed_threshold": min(deltas) if deltas else None,
                "max_target_ece": max_ece_value,
                "max_target_ece_gate": float(max_target_ece),
                "all_targets_ece_pass": bool(all_targets_ece_pass),
                "max_negative_pairs_allowed": int(max_negative_pairs_allowed),
                "negative_pair_gate_pass": bool(negative_pair_gate_pass),
                "combined_pass": bool(all_targets_ece_pass and negative_pair_gate_pass),
            }
        )
    return model_rows


def run_multisource_transfer_model_scan_summary(
    scan_output_root: str | Path,
    source_regions: list[str],
    output_prefix: str | Path,
    max_target_ece: float = 0.10,
    max_negative_pairs_allowed: int = 1,
) -> dict[str, Any]:
    scan_root = Path(scan_output_root)
    source_list = [str(item).strip() for item in source_regions if str(item).strip()]
    if not source_list:
        raise ValueError("source_regions must contain at least one region")

    per_model_rows: list[dict[str, Any]] = []
    per_source_rows: list[dict[str, Any]] = []
    for source_region in source_list:
        detail_csv = scan_root / f"{source_region}_transfer_model_scan_detail.csv"
        summary_json = scan_root / f"{source_region}_transfer_model_scan.json"
        if not detail_csv.exists():
            raise FileNotFoundError(f"detail csv not found: {detail_csv}")
        if not summary_json.exists():
            raise FileNotFoundError(f"summary json not found: {summary_json}")

        detail_rows = _parse_csv_rows(detail_csv)
        model_rows = _summarize_model_rows(
            source_region=source_region,
            rows=detail_rows,
            max_target_ece=float(max_target_ece),
            max_negative_pairs_allowed=int(max_negative_pairs_allowed),
        )
        per_model_rows.extend(model_rows)

        summary_payload = json.loads(summary_json.read_text(encoding="utf-8"))
        recommended_model = str(summary_payload.get("recommended_model", "")).strip()
        recommended_row = next(
            (row for row in model_rows if str(row.get("model_name", "")).strip() == recommended_model),
            None,
        )
        best_row = _select_best_combined(model_rows)
        per_source_rows.append(
            {
                "source_region": source_region,
                "recommended_model": recommended_model or None,
                "recommended_combined_pass": bool(recommended_row.get("combined_pass")) if recommended_row else False,
                "recommended_negative_pair_count": (recommended_row.get("negative_pair_count") if recommended_row else None),
                "recommended_max_target_ece": (recommended_row.get("max_target_ece") if recommended_row else None),
                "recommended_mean_delta_f1_fixed_threshold": (
                    recommended_row.get("mean_delta_f1_fixed_threshold") if recommended_row else None
                ),
                "recommended_min_delta_f1_fixed_threshold": (
                    recommended_row.get("min_delta_f1_fixed_threshold") if recommended_row else None
                ),
                "best_combined_model": (best_row.get("model_name") if best_row else None),
                "best_combined_negative_pair_count": (best_row.get("negative_pair_count") if best_row else None),
                "best_combined_max_target_ece": (best_row.get("max_target_ece") if best_row else None),
                "best_combined_mean_delta_f1_fixed_threshold": (
                    best_row.get("mean_delta_f1_fixed_threshold") if best_row else None
                ),
                "best_combined_min_delta_f1_fixed_threshold": (
                    best_row.get("min_delta_f1_fixed_threshold") if best_row else None
                ),
                "best_combined_pass": bool(best_row.get("combined_pass")) if best_row else False,
                "model_count": len(model_rows),
                "target_pair_count": len(detail_rows),
            }
        )

    source_rows_sorted = sorted(per_source_rows, key=lambda row: str(row.get("source_region", "")))
    model_rows_sorted = sorted(
        per_model_rows,
        key=lambda row: (str(row.get("source_region", "")), str(row.get("model_name", ""))),
    )
    recommended_pass_count = sum(1 for row in source_rows_sorted if bool(row.get("recommended_combined_pass")))
    best_pass_count = sum(1 for row in source_rows_sorted if bool(row.get("best_combined_pass")))
    recommendation_mismatch_count = sum(
        1
        for row in source_rows_sorted
        if str(row.get("recommended_model", "")) and str(row.get("recommended_model", "")) != str(row.get("best_combined_model", ""))
    )

    prefix = Path(output_prefix)
    detail_csv_path = prefix.with_name(f"{prefix.name}_detail.csv")
    source_summary_csv_path = prefix.with_name(f"{prefix.name}_source_summary.csv")
    summary_md_path = prefix.with_suffix(".md")
    summary_json_path = prefix.with_suffix(".json")

    _write_csv(detail_csv_path, model_rows_sorted, MODEL_DETAIL_FIELDS)
    _write_csv(source_summary_csv_path, source_rows_sorted, SOURCE_SUMMARY_FIELDS)

    lines = [
        "# Multi-Source Transfer-Model-Scan Summary",
        "",
        f"- scan_output_root: `{scan_root}`",
        f"- source_regions: `{', '.join(source_list)}`",
        f"- max_target_ece: `{float(max_target_ece):.4f}`",
        f"- max_negative_pairs_allowed: `{int(max_negative_pairs_allowed)}`",
        f"- recommended_combined_pass_count: `{recommended_pass_count}/{len(source_rows_sorted)}`",
        f"- best_combined_pass_count: `{best_pass_count}/{len(source_rows_sorted)}`",
        f"- recommendation_mismatch_count: `{recommendation_mismatch_count}`",
        "",
        "| Source | Recommended | Rec Combined Pass | Rec Neg Pairs | Rec Max ECE | Best Combined | Best Neg Pairs | Best Max ECE |",
        "|---|---|---:|---:|---:|---|---:|---:|",
    ]
    for row in source_rows_sorted:
        lines.append(
            "| "
            + f"{row.get('source_region', '')} | "
            + f"{row.get('recommended_model', 'n/a')} | "
            + f"{'yes' if row.get('recommended_combined_pass') else 'no'} | "
            + f"{row.get('recommended_negative_pair_count', 'n/a')} | "
            + f"{_fmt(row.get('recommended_max_target_ece'))} | "
            + f"{row.get('best_combined_model', 'n/a')} | "
            + f"{row.get('best_combined_negative_pair_count', 'n/a')} | "
            + f"{_fmt(row.get('best_combined_max_target_ece'))} |"
        )
    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {
        "status": "completed",
        "scan_output_root": str(scan_root),
        "source_regions": source_list,
        "max_target_ece": float(max_target_ece),
        "max_negative_pairs_allowed": int(max_negative_pairs_allowed),
        "recommended_combined_pass_count": int(recommended_pass_count),
        "source_count": int(len(source_rows_sorted)),
        "best_combined_pass_count": int(best_pass_count),
        "recommendation_mismatch_count": int(recommendation_mismatch_count),
        "detail_csv_path": str(detail_csv_path),
        "source_summary_csv_path": str(source_summary_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
    }
    summary_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

