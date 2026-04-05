from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def _read_json(path_value: str | Path) -> dict[str, Any]:
    return json.loads(Path(path_value).read_text(encoding="utf-8"))


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _sanitize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _format_region(value: str | None) -> str:
    if not value:
        return "unknown"
    normalized = str(value).strip().lower()
    if normalized == "nola":
        return "NOLA"
    return normalized.capitalize()


def _extract_region_window_case(source_path: str | Path) -> tuple[str, str, str]:
    text = str(source_path).lower()
    case_mode = "multi" if "multiown" in text else "single"

    patterns = (
        r"noaa_([a-z0-9]+)_(\d+h)_seed_batch",
        r"([a-z0-9]+)_(\d+h)_multiown_summary",
    )
    for pattern in patterns:
        matched = re.search(pattern, text)
        if matched:
            return (_format_region(matched.group(1)), matched.group(2), case_mode)
    return ("unknown", "unknown", case_mode)


def _write_rows_csv(path_value: str | Path, rows: list[dict[str, Any]], candidate_models: list[str]) -> str:
    destination = Path(path_value)
    destination.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "region",
        "window",
        "case_mode",
        "plain_recommended",
        "governed_recommended",
        "governed_basis",
        "gate_pass_count",
        "source",
    ]
    for model in candidate_models:
        suffix = _sanitize_key(model)
        columns.extend(
            [
                f"score_{suffix}",
                f"ece_{suffix}",
                f"loo_{suffix}",
                f"gate_{suffix}",
            ]
        )

    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in columns})

    return str(destination)


def build_governed_selection_markdown(summary: dict[str, Any]) -> str:
    candidate_models: list[str] = list(summary.get("candidate_models", []))
    lines = [
        "# Governed Selection Matrix",
        "",
        "Gate:",
        f"- calibration ECE <= `{summary.get('ece_threshold')}`",
        f"- own-ship LOO F1 mean >= `{summary.get('loo_threshold')}`",
        "",
        f"Candidate models: `{candidate_models}`",
        "",
        "| region | window | case_mode | plain_recommended | governed_recommended | governed_basis | gate_pass_count |",
        "|---|---|---|---|---|---|---:|",
    ]
    for row in summary.get("rows", []):
        lines.append(
            "| {region} | {window} | {case_mode} | {plain_recommended} | {governed_recommended} | {governed_basis} | {gate_pass_count} |".format(
                region=row.get("region", "unknown"),
                window=row.get("window", "unknown"),
                case_mode=row.get("case_mode", "unknown"),
                plain_recommended=row.get("plain_recommended", ""),
                governed_recommended=row.get("governed_recommended", ""),
                governed_basis=row.get("governed_basis", ""),
                gate_pass_count=row.get("gate_pass_count", 0),
            )
        )
    lines.extend(
        [
            "",
            "## Governed Recommendation Count",
            "",
            "| model | count |",
            "|---|---:|",
        ]
    )
    for row in summary.get("governed_recommendation_counts", []):
        lines.append(f"| {row.get('model', 'unknown')} | {row.get('count', 0)} |")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            f"- changed_count (plain != governed): `{summary.get('changed_count', 0)}`",
            f"- source_count: `{summary.get('source_count', 0)}`",
            "",
        ]
    )
    return "\n".join(lines)


def build_governed_selection_matrix(
    summary_json_paths: list[str | Path],
    output_prefix: str | Path,
    candidate_models: list[str] | None = None,
    ece_threshold: float = 0.25,
    loo_threshold: float = 0.60,
    score_key: str = "selection_score",
) -> dict[str, Any]:
    models = [str(item).strip() for item in (candidate_models or ["logreg", "hgbt", "torch_mlp"]) if str(item).strip()]
    unique_models: list[str] = []
    seen_models: set[str] = set()
    for model in models:
        if model in seen_models:
            continue
        unique_models.append(model)
        seen_models.add(model)

    rows: list[dict[str, Any]] = []
    for source in summary_json_paths:
        payload = _read_json(source)
        aggregate_raw = payload.get("aggregate_by_model", {})
        aggregate: dict[str, dict[str, Any]] = aggregate_raw if isinstance(aggregate_raw, dict) else {}

        region, window, case_mode = _extract_region_window_case(source)
        plain_recommended = str(payload.get("recommended_model") or "")
        gate_pass_models: list[tuple[str, float]] = []
        scored_models: list[tuple[str, float]] = []
        row: dict[str, Any] = {
            "region": region,
            "window": window,
            "case_mode": case_mode,
            "plain_recommended": plain_recommended,
            "source": str(source),
        }

        for model in unique_models:
            metrics = aggregate.get(model, {})
            score = _safe_float(metrics.get(score_key))
            ece = _safe_float(metrics.get("calibration_ece_mean"))
            loo = _safe_float(metrics.get("loo_f1_mean_mean"))
            gate_pass = bool(
                score is not None
                and ece is not None
                and loo is not None
                and ece <= float(ece_threshold)
                and loo >= float(loo_threshold)
            )
            if score is not None:
                scored_models.append((model, float(score)))
            if gate_pass and score is not None:
                gate_pass_models.append((model, float(score)))

            suffix = _sanitize_key(model)
            row[f"score_{suffix}"] = score
            row[f"ece_{suffix}"] = ece
            row[f"loo_{suffix}"] = loo
            row[f"gate_{suffix}"] = gate_pass

        row["gate_pass_count"] = len(gate_pass_models)
        if gate_pass_models:
            governed_model, _ = max(gate_pass_models, key=lambda item: item[1])
            row["governed_recommended"] = governed_model
            row["governed_basis"] = "best_gate_passed_selection_score"
        elif scored_models:
            governed_model, _ = max(scored_models, key=lambda item: item[1])
            row["governed_recommended"] = governed_model
            row["governed_basis"] = "fallback_best_selection_score"
        else:
            row["governed_recommended"] = plain_recommended
            row["governed_basis"] = "fallback_plain_recommended"

        rows.append(row)

    rows.sort(
        key=lambda row: (
            str(row.get("region", "")),
            str(row.get("window", "")),
            str(row.get("case_mode", "")),
            str(row.get("source", "")),
        )
    )
    changed_count = sum(1 for row in rows if str(row.get("plain_recommended", "")) != str(row.get("governed_recommended", "")))
    governed_counter = Counter(str(row.get("governed_recommended", "")) for row in rows if row.get("governed_recommended"))

    prefix = Path(output_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    summary_json_path = prefix.with_name(f"{prefix.name}_summary.json")
    summary_md_path = prefix.with_name(f"{prefix.name}_summary.md")
    summary_csv_path = prefix.with_name(f"{prefix.name}_rows.csv")

    summary: dict[str, Any] = {
        "status": "completed",
        "source_count": len(rows),
        "candidate_models": unique_models,
        "ece_threshold": float(ece_threshold),
        "loo_threshold": float(loo_threshold),
        "score_key": score_key,
        "changed_count": changed_count,
        "governed_recommendation_counts": [
            {"model": model, "count": count}
            for model, count in sorted(governed_counter.items(), key=lambda item: (-item[1], item[0]))
        ],
        "rows": rows,
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
        "summary_csv_path": str(summary_csv_path),
    }

    summary_csv_written = _write_rows_csv(summary_csv_path, rows, unique_models)
    summary["summary_csv_path"] = summary_csv_written
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_governed_selection_markdown(summary), encoding="utf-8")
    return summary
