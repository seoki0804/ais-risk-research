from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean
from typing import Any


DETAIL_FIELDS = [
    "evidence_type",
    "region",
    "scope",
    "split",
    "direction",
    "row_count",
    "positive_rate",
    "own_ship_count",
    "test_rows",
    "test_positive_count",
    "test_positive_support_flag",
    "hgbt_f1",
    "logreg_f1",
    "hgbt_minus_logreg_f1",
    "hgbt_auroc",
    "hgbt_auprc",
    "hgbt_threshold",
    "logreg_threshold",
    "hgbt_source_f1",
    "hgbt_target_f1",
    "hgbt_delta_f1",
    "logreg_source_f1",
    "logreg_target_f1",
    "logreg_delta_f1",
    "summary_json_path",
    "predictions_csv_path",
]

SUMMARY_FIELDS = [
    "true_area_row_count",
    "true_area_region_count",
    "true_area_split_count",
    "true_area_supported_split_count",
    "true_area_low_support_count",
    "low_support_region_splits",
    "own_ship_hgbt_f1_mean",
    "own_ship_hgbt_f1_min",
    "own_ship_hgbt_f1_max",
    "timestamp_hgbt_f1_mean",
    "timestamp_hgbt_f1_min",
    "timestamp_hgbt_f1_max",
    "transfer_row_count",
    "transfer_region_count",
    "transfer_negative_delta_count",
    "negative_transfer_pairs",
    "transfer_delta_f1_mean",
    "transfer_delta_f1_min",
    "transfer_delta_f1_max",
    "detail_csv_path",
]


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


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _count_test_support(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    total = 0
    positives = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            label_value = _safe_float(row.get("label_future_conflict"))
            if label_value is None:
                continue
            total += 1
            if int(label_value) == 1:
                positives += 1
    return total, positives


def _region_from_pairwise_summary(path: Path) -> str:
    suffix = "_pooled_pairwise_summary"
    if path.stem.endswith(suffix):
        return path.stem[: -len(suffix)]
    return path.stem


def _direction_region(direction: str) -> str:
    if "_2023_to_2024" in direction:
        return direction.split("_2023_to_2024", 1)[0]
    if "_2024_to_2023" in direction:
        return direction.split("_2024_to_2023", 1)[0]
    return direction


def _scope_from_pairwise_summary_path(path: Path) -> str:
    value = path.as_posix().lower()
    if "cross_year_2024" in value:
        return "cross_year_2024_unseen_region"
    return "pooled_true_new_area"


def _maybe_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(mean(values))


def _maybe_min(values: list[float]) -> float | None:
    if not values:
        return None
    return float(min(values))


def _maybe_max(values: list[float]) -> float | None:
    if not values:
        return None
    return float(max(values))


def run_unseen_area_evidence_report(
    true_area_pairwise_summary_json_paths: list[str | Path],
    transfer_summary_json_paths: list[str | Path],
    output_prefix: str | Path,
    min_test_positive_support: int = 10,
    target_model: str = "hgbt",
    comparator_model: str = "logreg",
) -> dict[str, Any]:
    true_area_paths = [Path(path).resolve() for path in true_area_pairwise_summary_json_paths]
    transfer_paths = [Path(path).resolve() for path in transfer_summary_json_paths]
    detail_rows: list[dict[str, Any]] = []
    missing_true_area_paths: list[str] = []
    missing_transfer_paths: list[str] = []

    for pairwise_summary_path in true_area_paths:
        if not pairwise_summary_path.exists():
            missing_true_area_paths.append(str(pairwise_summary_path))
            continue
        region = _region_from_pairwise_summary(pairwise_summary_path)
        region_dir = pairwise_summary_path.parent
        scope = _scope_from_pairwise_summary_path(pairwise_summary_path)

        for split in ["own_ship", "timestamp"]:
            summary_path = region_dir / f"{region}_pooled_{split}_summary.json"
            if not summary_path.exists():
                continue
            summary_payload = _load_json(summary_path)
            model_payload = summary_payload.get("models", {})
            target_metrics = dict(model_payload.get(target_model, {}))
            comparator_metrics = dict(model_payload.get(comparator_model, {}))

            predictions_csv_path = region_dir / f"{region}_pooled_{split}_test_predictions.csv"
            test_rows, test_positive_count = _count_test_support(predictions_csv_path)
            support_flag = "low" if test_positive_count < int(min_test_positive_support) else "ok"

            target_f1 = _safe_float(target_metrics.get("f1"))
            comparator_f1 = _safe_float(comparator_metrics.get("f1"))
            delta_f1 = None
            if target_f1 is not None and comparator_f1 is not None:
                delta_f1 = float(target_f1 - comparator_f1)

            detail_rows.append(
                {
                    "evidence_type": "true_unseen_area",
                    "region": region,
                    "scope": scope,
                    "split": split,
                    "direction": "",
                    "row_count": int(_safe_float(summary_payload.get("row_count")) or 0),
                    "positive_rate": _safe_float(summary_payload.get("positive_rate")),
                    "own_ship_count": int(_safe_float(summary_payload.get("own_ship_count")) or 0),
                    "test_rows": test_rows,
                    "test_positive_count": test_positive_count,
                    "test_positive_support_flag": support_flag,
                    "hgbt_f1": target_f1,
                    "logreg_f1": comparator_f1,
                    "hgbt_minus_logreg_f1": delta_f1,
                    "hgbt_auroc": _safe_float(target_metrics.get("auroc")),
                    "hgbt_auprc": _safe_float(target_metrics.get("auprc")),
                    "hgbt_threshold": _safe_float(target_metrics.get("threshold")),
                    "logreg_threshold": _safe_float(comparator_metrics.get("threshold")),
                    "hgbt_source_f1": "",
                    "hgbt_target_f1": "",
                    "hgbt_delta_f1": "",
                    "logreg_source_f1": "",
                    "logreg_target_f1": "",
                    "logreg_delta_f1": "",
                    "summary_json_path": str(summary_path),
                    "predictions_csv_path": str(predictions_csv_path) if predictions_csv_path.exists() else "",
                }
            )

    for transfer_summary_path in transfer_paths:
        if not transfer_summary_path.exists():
            missing_transfer_paths.append(str(transfer_summary_path))
            continue
        payload = _load_json(transfer_summary_path)
        direction = transfer_summary_path.stem.replace("_transfer_summary", "")
        region = _direction_region(direction)
        model_payload = dict(payload.get("models", {}))

        target_model_payload = dict(model_payload.get(target_model, {}))
        comparator_model_payload = dict(model_payload.get(comparator_model, {}))
        target_source = dict(target_model_payload.get("source_test", {}))
        target_transfer = dict(target_model_payload.get("target_transfer", {}))
        comparator_source = dict(comparator_model_payload.get("source_test", {}))
        comparator_transfer = dict(comparator_model_payload.get("target_transfer", {}))

        target_source_f1 = _safe_float(target_source.get("f1"))
        target_target_f1 = _safe_float(target_transfer.get("f1"))
        target_delta = None
        if target_source_f1 is not None and target_target_f1 is not None:
            target_delta = float(target_target_f1 - target_source_f1)

        comparator_source_f1 = _safe_float(comparator_source.get("f1"))
        comparator_target_f1 = _safe_float(comparator_transfer.get("f1"))
        comparator_delta = None
        if comparator_source_f1 is not None and comparator_target_f1 is not None:
            comparator_delta = float(comparator_target_f1 - comparator_source_f1)

        detail_rows.append(
            {
                "evidence_type": "cross_year_transfer",
                "region": region,
                "scope": "cross_year_transfer",
                "split": str(dict(payload.get("split", {})).get("strategy", "")),
                "direction": direction,
                "row_count": int(_safe_float(payload.get("target_row_count")) or 0),
                "positive_rate": _safe_float(payload.get("target_positive_rate")),
                "own_ship_count": int(_safe_float(payload.get("target_own_ship_count")) or 0),
                "test_rows": "",
                "test_positive_count": "",
                "test_positive_support_flag": "",
                "hgbt_f1": target_target_f1,
                "logreg_f1": comparator_target_f1,
                "hgbt_minus_logreg_f1": (
                    float(target_target_f1 - comparator_target_f1)
                    if target_target_f1 is not None and comparator_target_f1 is not None
                    else ""
                ),
                "hgbt_auroc": _safe_float(target_transfer.get("auroc")),
                "hgbt_auprc": _safe_float(target_transfer.get("auprc")),
                "hgbt_threshold": _safe_float(target_model_payload.get("threshold")),
                "logreg_threshold": _safe_float(comparator_model_payload.get("threshold")),
                "hgbt_source_f1": target_source_f1,
                "hgbt_target_f1": target_target_f1,
                "hgbt_delta_f1": target_delta,
                "logreg_source_f1": comparator_source_f1,
                "logreg_target_f1": comparator_target_f1,
                "logreg_delta_f1": comparator_delta,
                "summary_json_path": str(transfer_summary_path),
                "predictions_csv_path": str(payload.get("target_predictions_csv_path", "")),
            }
        )

    detail_rows.sort(
        key=lambda row: (
            str(row.get("evidence_type", "")),
            str(row.get("region", "")),
            str(row.get("split", "")),
            str(row.get("direction", "")),
        )
    )

    true_rows = [row for row in detail_rows if row.get("evidence_type") == "true_unseen_area"]
    transfer_rows = [row for row in detail_rows if row.get("evidence_type") == "cross_year_transfer"]
    low_support_rows = [row for row in true_rows if str(row.get("test_positive_support_flag")) == "low"]
    own_ship_values = [_safe_float(row.get("hgbt_f1")) for row in true_rows if str(row.get("split")) == "own_ship"]
    own_ship_values = [value for value in own_ship_values if value is not None]
    timestamp_values = [_safe_float(row.get("hgbt_f1")) for row in true_rows if str(row.get("split")) == "timestamp"]
    timestamp_values = [value for value in timestamp_values if value is not None]
    transfer_delta_values = [_safe_float(row.get("hgbt_delta_f1")) for row in transfer_rows]
    transfer_delta_values = [value for value in transfer_delta_values if value is not None]
    negative_transfer_rows = [row for row in transfer_rows if (_safe_float(row.get("hgbt_delta_f1")) or 0.0) < 0.0]

    low_support_labels = sorted({f"{row['region']}:{row['split']}" for row in low_support_rows})
    negative_transfer_labels = sorted(
        {
            f"{row['direction']}({(_safe_float(row.get('hgbt_delta_f1')) or 0.0):.4f})"
            for row in negative_transfer_rows
        }
    )

    output_root = Path(output_prefix).resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    detail_csv_path = output_root.with_name(f"{output_root.name}_detail.csv")
    summary_csv_path = output_root.with_name(f"{output_root.name}_summary.csv")
    summary_md_path = output_root.with_suffix(".md")
    summary_json_path = output_root.with_suffix(".json")

    _write_csv(detail_csv_path, detail_rows, DETAIL_FIELDS)

    summary_row = {
        "true_area_row_count": len(true_rows),
        "true_area_region_count": len({str(row.get("region", "")) for row in true_rows}),
        "true_area_split_count": len(true_rows),
        "true_area_supported_split_count": len([row for row in true_rows if str(row.get("test_positive_support_flag")) == "ok"]),
        "true_area_low_support_count": len(low_support_rows),
        "low_support_region_splits": ",".join(low_support_labels),
        "own_ship_hgbt_f1_mean": _maybe_mean(own_ship_values),
        "own_ship_hgbt_f1_min": _maybe_min(own_ship_values),
        "own_ship_hgbt_f1_max": _maybe_max(own_ship_values),
        "timestamp_hgbt_f1_mean": _maybe_mean(timestamp_values),
        "timestamp_hgbt_f1_min": _maybe_min(timestamp_values),
        "timestamp_hgbt_f1_max": _maybe_max(timestamp_values),
        "transfer_row_count": len(transfer_rows),
        "transfer_region_count": len({str(row.get("region", "")) for row in transfer_rows}),
        "transfer_negative_delta_count": len(negative_transfer_rows),
        "negative_transfer_pairs": ",".join(negative_transfer_labels),
        "transfer_delta_f1_mean": _maybe_mean(transfer_delta_values),
        "transfer_delta_f1_min": _maybe_min(transfer_delta_values),
        "transfer_delta_f1_max": _maybe_max(transfer_delta_values),
        "detail_csv_path": str(detail_csv_path),
    }
    _write_csv(summary_csv_path, [summary_row], SUMMARY_FIELDS)

    lines = [
        "# True Unseen-Area Evidence Report",
        "",
        "## Inputs",
        "",
        f"- target_model: `{target_model}`",
        f"- comparator_model: `{comparator_model}`",
        f"- min_test_positive_support: `{int(min_test_positive_support)}`",
    ]
    for path in true_area_paths:
        lines.append(f"- true_area_pairwise_summary: `{path}`")
    for path in transfer_paths:
        lines.append(f"- transfer_summary: `{path}`")
    if missing_true_area_paths:
        lines.append(f"- missing_true_area_summaries: `{len(missing_true_area_paths)}`")
    if missing_transfer_paths:
        lines.append(f"- missing_transfer_summaries: `{len(missing_transfer_paths)}`")

    lines.extend(
        [
            "",
            "## Pooled True New-Area Benchmark Snapshot",
            "",
            "| Region | Split | Rows | Pos rate | Test rows | Test pos | Support | hgbt F1 | logreg F1 | Δ(hgbt-logreg) | hgbt AUROC |",
            "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|",
        ]
    )
    for row in true_rows:
        lines.append(
            "| {region} | {split} | {rows} | {pos_rate} | {test_rows} | {test_pos} | {support} | {hgbt_f1} | {logreg_f1} | {delta} | {auroc} |".format(
                region=row.get("region", ""),
                split=row.get("split", ""),
                rows=row.get("row_count", ""),
                pos_rate=_fmt(row.get("positive_rate")),
                test_rows=row.get("test_rows", ""),
                test_pos=row.get("test_positive_count", ""),
                support=row.get("test_positive_support_flag", ""),
                hgbt_f1=_fmt(row.get("hgbt_f1")),
                logreg_f1=_fmt(row.get("logreg_f1")),
                delta=_fmt(row.get("hgbt_minus_logreg_f1")),
                auroc=_fmt(row.get("hgbt_auroc")),
            )
        )

    lines.extend(
        [
            "",
            "## Cross-Year Transfer Snapshot",
            "",
            "| Direction | Region | Target rows | Target pos rate | hgbt source F1 | hgbt target F1 | ΔF1(target-source) |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in transfer_rows:
        lines.append(
            "| {direction} | {region} | {rows} | {pos_rate} | {source_f1} | {target_f1} | {delta_f1} |".format(
                direction=row.get("direction", ""),
                region=row.get("region", ""),
                rows=row.get("row_count", ""),
                pos_rate=_fmt(row.get("positive_rate")),
                source_f1=_fmt(row.get("hgbt_source_f1")),
                target_f1=_fmt(row.get("hgbt_target_f1")),
                delta_f1=_fmt(row.get("hgbt_delta_f1")),
            )
        )

    lines.extend(
        [
            "",
            "## Examiner Interpretation",
            "",
            (
                f"- low-support true-area splits (`test positives < {int(min_test_positive_support)}`): "
                f"`{len(low_support_rows)}` ({', '.join(low_support_labels) if low_support_labels else 'none'})"
            ),
            (
                f"- own_ship hgbt F1 range: `{_fmt(summary_row['own_ship_hgbt_f1_min'])} - "
                f"{_fmt(summary_row['own_ship_hgbt_f1_max'])}`"
            ),
            (
                f"- timestamp hgbt F1 range: `{_fmt(summary_row['timestamp_hgbt_f1_min'])} - "
                f"{_fmt(summary_row['timestamp_hgbt_f1_max'])}`"
            ),
            (
                f"- transfer negative-ΔF1 pairs: `{len(negative_transfer_rows)}/{len(transfer_rows)}` "
                f"({', '.join(negative_transfer_labels) if negative_transfer_labels else 'none'})"
            ),
            (
                f"- transfer harbor coverage (regions): `{int(summary_row['transfer_region_count'])}`"
            ),
            "",
            "## Outputs",
            "",
            f"- detail_csv: `{detail_csv_path}`",
            f"- summary_csv: `{summary_csv_path}`",
            f"- summary_json: `{summary_json_path}`",
        ]
    )
    summary_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    summary_payload = {
        "status": "completed",
        "target_model": target_model,
        "comparator_model": comparator_model,
        "min_test_positive_support": int(min_test_positive_support),
        "true_area_pairwise_summary_json_paths": [str(path) for path in true_area_paths],
        "transfer_summary_json_paths": [str(path) for path in transfer_paths],
        "detail_row_count": len(detail_rows),
        "true_area_row_count": len(true_rows),
        "transfer_row_count": len(transfer_rows),
        "true_area_low_support_count": len(low_support_rows),
        "transfer_negative_delta_count": len(negative_transfer_rows),
        "missing_true_area_summary_paths": missing_true_area_paths,
        "missing_transfer_summary_paths": missing_transfer_paths,
        "detail_csv_path": str(detail_csv_path),
        "summary_csv_path": str(summary_csv_path),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
        "summary": summary_row,
    }
    summary_json_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary_payload
