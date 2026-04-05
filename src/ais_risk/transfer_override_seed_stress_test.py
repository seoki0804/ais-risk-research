from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

from .transfer_calibration_probe import run_transfer_calibration_probe
from .transfer_model_scan import run_transfer_model_scan


PER_SEED_FIELDS = [
    "seed",
    "status",
    "notes",
    "baseline_model",
    "baseline_method",
    "baseline_pair_count",
    "baseline_negative_fixed_count",
    "baseline_max_target_ece",
    "baseline_combined_pass_fixed",
    "baseline_mean_delta_f1_fixed",
    "baseline_mean_source_f1_fixed",
    "baseline_mean_target_f1_fixed",
    "override_model",
    "override_method",
    "override_pair_count",
    "override_negative_fixed_count",
    "override_max_target_ece",
    "override_combined_pass_fixed",
    "override_mean_delta_f1_fixed",
    "override_mean_source_f1_fixed",
    "override_mean_target_f1_fixed",
    "source_f1_loss_override_vs_baseline",
    "target_f1_gain_override_vs_baseline",
    "negative_pair_delta_override_minus_baseline",
    "override_better_transfer_gate",
    "transfer_scan_detail_csv_path",
    "calibration_probe_detail_csv_path",
    "calibration_probe_model_method_summary_csv_path",
]


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def _fmt(value: Any, digits: int = 4) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return "n/a"
    return f"{numeric:.{digits}f}"


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


def _parse_int_list(raw: str | list[int] | tuple[int, ...]) -> list[int]:
    if isinstance(raw, (list, tuple)):
        return [int(value) for value in raw]
    tokens = [token.strip() for token in str(raw).split(",") if token.strip()]
    if not tokens:
        raise ValueError("No seed parsed.")
    return [int(token) for token in tokens]


def _find_summary_row(
    rows: list[dict[str, str]],
    model_name: str,
    method: str,
) -> dict[str, str] | None:
    model_value = str(model_name).strip()
    method_value = str(method).strip().lower()
    for row in rows:
        if str(row.get("model_name", "")).strip() != model_value:
            continue
        if str(row.get("method", "")).strip().lower() != method_value:
            continue
        return row
    return None


def _collect_detail_stats(
    rows: list[dict[str, str]],
    model_name: str,
    method: str,
) -> dict[str, float | None]:
    filtered = [
        row
        for row in rows
        if str(row.get("status", "")).strip() == "completed"
        and str(row.get("model_name", "")).strip() == str(model_name).strip()
        and str(row.get("method", "")).strip().lower() == str(method).strip().lower()
    ]
    source_values = [_safe_float(row.get("source_f1_fixed")) for row in filtered]
    target_values = [_safe_float(row.get("target_f1_fixed")) for row in filtered]
    source_numeric = [value for value in source_values if value is not None]
    target_numeric = [value for value in target_values if value is not None]
    return {
        "mean_source_f1_fixed": float(mean(source_numeric)) if source_numeric else None,
        "mean_target_f1_fixed": float(mean(target_numeric)) if target_numeric else None,
    }


def run_transfer_override_seed_stress_test(
    input_dir: str | Path,
    output_prefix: str | Path,
    source_region: str = "houston",
    target_regions: list[str] | None = None,
    baseline_model: str = "hgbt",
    override_model: str = "rule_score",
    override_method: str = "isotonic",
    random_seeds: list[int] | tuple[int, ...] | str = "41,42,43,44,45",
    split_strategy: str = "own_ship",
    train_fraction: float = 0.6,
    val_fraction: float = 0.2,
    threshold_grid_step: float = 0.01,
    ece_gate_max: float = 0.10,
    max_negative_pairs_allowed: int = 1,
    torch_device: str = "auto",
    calibration_bins: int = 10,
) -> dict[str, Any]:
    seeds = _parse_int_list(random_seeds)
    source_region_value = str(source_region).strip().lower()
    if not source_region_value:
        raise ValueError("source_region is required.")

    targets = [str(item).strip().lower() for item in (target_regions or ["nola", "seattle"]) if str(item).strip()]
    if not targets:
        raise ValueError("target_regions must be non-empty.")

    input_root = Path(input_dir).resolve()
    source_input_path = input_root / f"{source_region_value}_pooled_pairwise.csv"
    if not source_input_path.exists():
        raise FileNotFoundError(f"Missing source input: {source_input_path}")

    target_mapping: dict[str, str] = {}
    for target_region in targets:
        target_path = input_root / f"{target_region}_pooled_pairwise.csv"
        if not target_path.exists():
            raise FileNotFoundError(f"Missing target input: {target_path}")
        target_mapping[target_region] = str(target_path)

    output_prefix_path = Path(output_prefix).resolve()
    output_prefix_path.parent.mkdir(parents=True, exist_ok=True)
    run_root = output_prefix_path.parent / f"{output_prefix_path.name}_runs"
    run_root.mkdir(parents=True, exist_ok=True)

    per_seed_rows: list[dict[str, Any]] = []
    for seed in seeds:
        seed_root = run_root / f"seed_{int(seed)}"
        try:
            transfer_summary = run_transfer_model_scan(
                source_region=source_region_value,
                source_input_path=source_input_path,
                target_input_paths_by_region=target_mapping,
                model_names=[str(baseline_model).strip(), str(override_model).strip()],
                output_root=seed_root / "transfer_scan",
                split_strategy=split_strategy,
                train_fraction=float(train_fraction),
                val_fraction=float(val_fraction),
                threshold_grid_step=float(threshold_grid_step),
                torch_device=torch_device,
                random_seed=int(seed),
                calibration_bins=int(calibration_bins),
                calibration_ece_max=float(ece_gate_max),
            )
            calibration_summary = run_transfer_calibration_probe(
                transfer_scan_detail_csv_path=transfer_summary["detail_csv_path"],
                output_prefix=seed_root / "transfer_calibration_probe",
                source_region_filter=source_region_value,
                model_names=[str(baseline_model).strip(), str(override_model).strip()],
                methods=["none", str(override_method).strip().lower()],
                threshold_grid_step=float(threshold_grid_step),
                ece_gate_max=float(ece_gate_max),
                max_negative_pairs_allowed=int(max_negative_pairs_allowed),
                random_seed=int(seed),
            )

            model_method_rows = _parse_csv_rows(calibration_summary["model_method_summary_csv_path"])
            detail_rows = _parse_csv_rows(calibration_summary["detail_csv_path"])
            baseline_row = _find_summary_row(model_method_rows, model_name=baseline_model, method="none")
            override_row = _find_summary_row(model_method_rows, model_name=override_model, method=override_method)
            if baseline_row is None or override_row is None:
                per_seed_rows.append(
                    {
                        "seed": int(seed),
                        "status": "incomplete",
                        "notes": "baseline or override row not found in calibration probe summary",
                        "baseline_model": baseline_model,
                        "baseline_method": "none",
                        "baseline_pair_count": None,
                        "baseline_negative_fixed_count": None,
                        "baseline_max_target_ece": None,
                        "baseline_combined_pass_fixed": False,
                        "baseline_mean_delta_f1_fixed": None,
                        "baseline_mean_source_f1_fixed": None,
                        "baseline_mean_target_f1_fixed": None,
                        "override_model": override_model,
                        "override_method": override_method,
                        "override_pair_count": None,
                        "override_negative_fixed_count": None,
                        "override_max_target_ece": None,
                        "override_combined_pass_fixed": False,
                        "override_mean_delta_f1_fixed": None,
                        "override_mean_source_f1_fixed": None,
                        "override_mean_target_f1_fixed": None,
                        "source_f1_loss_override_vs_baseline": None,
                        "target_f1_gain_override_vs_baseline": None,
                        "negative_pair_delta_override_minus_baseline": None,
                        "override_better_transfer_gate": False,
                        "transfer_scan_detail_csv_path": transfer_summary.get("detail_csv_path", ""),
                        "calibration_probe_detail_csv_path": calibration_summary.get("detail_csv_path", ""),
                        "calibration_probe_model_method_summary_csv_path": calibration_summary.get(
                            "model_method_summary_csv_path", ""
                        ),
                    }
                )
                continue

            baseline_stats = _collect_detail_stats(detail_rows, model_name=baseline_model, method="none")
            override_stats = _collect_detail_stats(detail_rows, model_name=override_model, method=override_method)

            baseline_neg = int(_safe_float(baseline_row.get("negative_fixed_count")) or 0)
            override_neg = int(_safe_float(override_row.get("negative_fixed_count")) or 0)
            baseline_max_ece = _safe_float(baseline_row.get("max_target_ece"))
            override_max_ece = _safe_float(override_row.get("max_target_ece"))
            baseline_source_f1 = _safe_float(baseline_stats.get("mean_source_f1_fixed"))
            override_source_f1 = _safe_float(override_stats.get("mean_source_f1_fixed"))
            baseline_target_f1 = _safe_float(baseline_stats.get("mean_target_f1_fixed"))
            override_target_f1 = _safe_float(override_stats.get("mean_target_f1_fixed"))

            source_loss = (
                float(baseline_source_f1 - override_source_f1)
                if baseline_source_f1 is not None and override_source_f1 is not None
                else None
            )
            target_gain = (
                float(override_target_f1 - baseline_target_f1)
                if baseline_target_f1 is not None and override_target_f1 is not None
                else None
            )
            override_better_transfer_gate = bool(
                override_neg < baseline_neg and (override_max_ece is not None and override_max_ece <= float(ece_gate_max))
            )

            per_seed_rows.append(
                {
                    "seed": int(seed),
                    "status": "completed",
                    "notes": "",
                    "baseline_model": baseline_model,
                    "baseline_method": "none",
                    "baseline_pair_count": int(_safe_float(baseline_row.get("pair_count")) or 0),
                    "baseline_negative_fixed_count": baseline_neg,
                    "baseline_max_target_ece": baseline_max_ece,
                    "baseline_combined_pass_fixed": _to_bool(baseline_row.get("combined_pass_fixed")),
                    "baseline_mean_delta_f1_fixed": _safe_float(baseline_row.get("mean_delta_f1_fixed")),
                    "baseline_mean_source_f1_fixed": baseline_source_f1,
                    "baseline_mean_target_f1_fixed": baseline_target_f1,
                    "override_model": override_model,
                    "override_method": override_method,
                    "override_pair_count": int(_safe_float(override_row.get("pair_count")) or 0),
                    "override_negative_fixed_count": override_neg,
                    "override_max_target_ece": override_max_ece,
                    "override_combined_pass_fixed": _to_bool(override_row.get("combined_pass_fixed")),
                    "override_mean_delta_f1_fixed": _safe_float(override_row.get("mean_delta_f1_fixed")),
                    "override_mean_source_f1_fixed": override_source_f1,
                    "override_mean_target_f1_fixed": override_target_f1,
                    "source_f1_loss_override_vs_baseline": source_loss,
                    "target_f1_gain_override_vs_baseline": target_gain,
                    "negative_pair_delta_override_minus_baseline": int(override_neg - baseline_neg),
                    "override_better_transfer_gate": override_better_transfer_gate,
                    "transfer_scan_detail_csv_path": transfer_summary.get("detail_csv_path", ""),
                    "calibration_probe_detail_csv_path": calibration_summary.get("detail_csv_path", ""),
                    "calibration_probe_model_method_summary_csv_path": calibration_summary.get(
                        "model_method_summary_csv_path", ""
                    ),
                }
            )
        except Exception as exc:
            per_seed_rows.append(
                {
                    "seed": int(seed),
                    "status": "failed",
                    "notes": str(exc),
                    "baseline_model": baseline_model,
                    "baseline_method": "none",
                    "baseline_pair_count": None,
                    "baseline_negative_fixed_count": None,
                    "baseline_max_target_ece": None,
                    "baseline_combined_pass_fixed": False,
                    "baseline_mean_delta_f1_fixed": None,
                    "baseline_mean_source_f1_fixed": None,
                    "baseline_mean_target_f1_fixed": None,
                    "override_model": override_model,
                    "override_method": override_method,
                    "override_pair_count": None,
                    "override_negative_fixed_count": None,
                    "override_max_target_ece": None,
                    "override_combined_pass_fixed": False,
                    "override_mean_delta_f1_fixed": None,
                    "override_mean_source_f1_fixed": None,
                    "override_mean_target_f1_fixed": None,
                    "source_f1_loss_override_vs_baseline": None,
                    "target_f1_gain_override_vs_baseline": None,
                    "negative_pair_delta_override_minus_baseline": None,
                    "override_better_transfer_gate": False,
                    "transfer_scan_detail_csv_path": "",
                    "calibration_probe_detail_csv_path": "",
                    "calibration_probe_model_method_summary_csv_path": "",
                }
            )

    completed_rows = [row for row in per_seed_rows if str(row.get("status", "")) == "completed"]
    completed_count = len(completed_rows)
    seed_count = len(per_seed_rows)

    baseline_pass_count = sum(1 for row in completed_rows if _to_bool(row.get("baseline_combined_pass_fixed")))
    override_pass_count = sum(1 for row in completed_rows if _to_bool(row.get("override_combined_pass_fixed")))
    override_better_negative_count = sum(
        1
        for row in completed_rows
        if (_safe_float(row.get("negative_pair_delta_override_minus_baseline")) or 0.0) < 0.0
    )
    override_better_transfer_gate_count = sum(1 for row in completed_rows if _to_bool(row.get("override_better_transfer_gate")))

    source_loss_values = [
        float(row["source_f1_loss_override_vs_baseline"])
        for row in completed_rows
        if _safe_float(row.get("source_f1_loss_override_vs_baseline")) is not None
    ]
    target_gain_values = [
        float(row["target_f1_gain_override_vs_baseline"])
        for row in completed_rows
        if _safe_float(row.get("target_f1_gain_override_vs_baseline")) is not None
    ]
    override_max_ece_values = [
        float(row["override_max_target_ece"]) for row in completed_rows if _safe_float(row.get("override_max_target_ece")) is not None
    ]

    target_gate_stable = bool(completed_count > 0 and override_pass_count == completed_count)
    source_loss_disclosed = bool(source_loss_values)
    required_better_count = int(math.ceil(float(completed_count) * 0.5)) if completed_count else 0
    dq3_acceptance_met = bool(
        completed_count >= 3
        and target_gate_stable
        and source_loss_disclosed
        and override_better_transfer_gate_count >= required_better_count
    )

    summary_md_path = output_prefix_path.with_suffix(".md")
    summary_json_path = output_prefix_path.with_suffix(".json")
    per_seed_csv_path = output_prefix_path.with_name(f"{output_prefix_path.name}_per_seed").with_suffix(".csv")
    _write_csv(per_seed_csv_path, per_seed_rows, PER_SEED_FIELDS)

    md_lines = [
        "# Transfer Override Seed Stress Test",
        "",
        "## Configuration",
        "",
        f"- input_dir: `{input_root}`",
        f"- source_region: `{source_region_value}`",
        f"- target_regions: `{', '.join(targets)}`",
        f"- baseline_model/method: `{baseline_model}/none`",
        f"- override_model/method: `{override_model}/{override_method}`",
        f"- seeds: `{', '.join(str(seed) for seed in seeds)}`",
        f"- threshold_grid_step: `{_fmt(threshold_grid_step)}`",
        f"- ece_gate_max: `{_fmt(ece_gate_max)}`",
        f"- max_negative_pairs_allowed: `{int(max_negative_pairs_allowed)}`",
        "",
        "## Headline",
        "",
        f"- completed seeds: `{completed_count}/{seed_count}`",
        f"- baseline combined-pass(fixed): `{baseline_pass_count}/{completed_count or 1}`",
        f"- override combined-pass(fixed): `{override_pass_count}/{completed_count or 1}`",
        f"- override better negative-pair count: `{override_better_negative_count}/{completed_count or 1}`",
        f"- override better transfer-gate count: `{override_better_transfer_gate_count}/{completed_count or 1}`",
        f"- mean source F1 loss (override-baseline): `{_fmt(mean(source_loss_values) if source_loss_values else None)}`",
        f"- max source F1 loss (override-baseline): `{_fmt(max(source_loss_values) if source_loss_values else None)}`",
        f"- mean target F1 gain (override-baseline): `{_fmt(mean(target_gain_values) if target_gain_values else None)}`",
        f"- max override target ECE across seeds: `{_fmt(max(override_max_ece_values) if override_max_ece_values else None)}`",
        f"- DQ-3 acceptance met: `{dq3_acceptance_met}`",
        "",
        "## Per-Seed Summary",
        "",
        "| Seed | Status | Baseline Neg | Override Neg | Baseline Pass | Override Pass | Source F1 Loss | Target F1 Gain |",
        "|---:|---|---:|---:|---|---|---:|---:|",
    ]
    for row in per_seed_rows:
        md_lines.append(
            "| {seed} | {status} | {bneg} | {oneg} | {bpass} | {opass} | {sloss} | {tgain} |".format(
                seed=row.get("seed", ""),
                status=row.get("status", ""),
                bneg=row.get("baseline_negative_fixed_count", "n/a"),
                oneg=row.get("override_negative_fixed_count", "n/a"),
                bpass="pass" if _to_bool(row.get("baseline_combined_pass_fixed")) else "fail",
                opass="pass" if _to_bool(row.get("override_combined_pass_fixed")) else "fail",
                sloss=_fmt(row.get("source_f1_loss_override_vs_baseline")),
                tgain=_fmt(row.get("target_f1_gain_override_vs_baseline")),
            )
        )

    md_lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- summary_md: `{summary_md_path}`",
            f"- summary_json: `{summary_json_path}`",
            f"- per_seed_csv: `{per_seed_csv_path}`",
            f"- run_root: `{run_root}`",
        ]
    )
    summary_md_path.write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")

    summary: dict[str, Any] = {
        "status": "completed",
        "input_dir": str(input_root),
        "source_region": source_region_value,
        "target_regions": targets,
        "baseline_model": str(baseline_model).strip(),
        "baseline_method": "none",
        "override_model": str(override_model).strip(),
        "override_method": str(override_method).strip().lower(),
        "random_seeds": [int(seed) for seed in seeds],
        "seed_count": seed_count,
        "completed_seed_count": completed_count,
        "baseline_combined_pass_fixed_count": baseline_pass_count,
        "override_combined_pass_fixed_count": override_pass_count,
        "override_better_negative_pair_count": override_better_negative_count,
        "override_better_transfer_gate_count": override_better_transfer_gate_count,
        "mean_source_f1_loss_override_vs_baseline": float(mean(source_loss_values)) if source_loss_values else None,
        "max_source_f1_loss_override_vs_baseline": max(source_loss_values) if source_loss_values else None,
        "mean_target_f1_gain_override_vs_baseline": float(mean(target_gain_values)) if target_gain_values else None,
        "max_override_target_ece": max(override_max_ece_values) if override_max_ece_values else None,
        "target_gate_stable": bool(target_gate_stable),
        "source_loss_disclosed": bool(source_loss_disclosed),
        "dq3_acceptance_met": bool(dq3_acceptance_met),
        "per_seed_csv_path": str(per_seed_csv_path),
        "run_root": str(run_root),
        "summary_md_path": str(summary_md_path),
        "summary_json_path": str(summary_json_path),
    }
    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


__all__ = ["run_transfer_override_seed_stress_test"]

