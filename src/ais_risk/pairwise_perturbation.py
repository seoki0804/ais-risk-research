from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path
from typing import Any

from .config import load_config
from .geo import m_to_nm, nm_to_m
from .models import RelativeKinematics
from .risk_scoring import compute_pairwise_risk


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp_nonnegative(value: float) -> float:
    return max(0.0, float(value))


def _clamp_course_difference(value: float) -> float:
    wrapped = abs(float(value)) % 360.0
    return wrapped if wrapped <= 180.0 else 360.0 - wrapped


def _bearing_to_xy_m(distance_nm: float, relative_bearing_deg: float) -> tuple[float, float]:
    distance_m = nm_to_m(distance_nm)
    radians = math.radians(relative_bearing_deg)
    return distance_m * math.sin(radians), distance_m * math.cos(radians)


def _xy_to_distance_bearing(x_m: float, y_m: float) -> tuple[float, float]:
    distance_nm = m_to_nm(math.hypot(x_m, y_m))
    bearing_deg = math.degrees(math.atan2(x_m, y_m))
    return distance_nm, bearing_deg


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def build_pairwise_perturbation_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Pairwise Perturbation Summary",
        "",
        "## Inputs",
        "",
        f"- input_csv: `{summary['input_csv_path']}`",
        f"- config_path: `{summary['config_path']}`",
        f"- profile_name: `{summary['profile_name']}`",
        f"- random_seed: `{summary['random_seed']}`",
        "",
        "## Perturbation Parameters",
        "",
        f"- position_jitter_m: `{summary['position_jitter_m']:.2f}`",
        f"- speed_jitter_frac: `{summary['speed_jitter_frac']:.4f}`",
        f"- course_jitter_deg: `{summary['course_jitter_deg']:.2f}`",
        f"- drop_rate: `{summary['drop_rate']:.4f}`",
        "",
        "## Drift Summary",
        "",
        f"- input_rows: `{summary['input_rows']}`",
        f"- output_rows: `{summary['output_rows']}`",
        f"- dropped_rows: `{summary['dropped_rows']}`",
        f"- keep_ratio: `{summary['keep_ratio']:.4f}`",
        f"- mean_abs_distance_delta_nm: `{summary['mean_abs_distance_delta_nm']:.4f}`",
        f"- mean_abs_bearing_delta_deg: `{summary['mean_abs_bearing_delta_deg']:.4f}`",
        f"- mean_abs_relspeed_delta_knots: `{summary['mean_abs_relspeed_delta_knots']:.4f}`",
        f"- mean_abs_course_delta_deg: `{summary['mean_abs_course_delta_deg']:.4f}`",
        f"- mean_abs_rule_score_delta: `{summary['mean_abs_rule_score_delta']:.4f}`",
        "",
        "## Outputs",
        "",
        f"- perturbed_csv: `{summary['perturbed_csv_path']}`",
        f"- summary_json: `{summary['summary_json_path']}`",
        f"- summary_md: `{summary['summary_md_path']}`",
        "",
    ]
    return "\n".join(lines)


def run_pairwise_perturbation(
    input_csv_path: str | Path,
    output_prefix: str | Path,
    config_path: str | Path = "configs/base.toml",
    profile_name: str = "custom",
    position_jitter_m: float = 0.0,
    speed_jitter_frac: float = 0.0,
    course_jitter_deg: float = 0.0,
    drop_rate: float = 0.0,
    random_seed: int = 42,
) -> dict[str, Any]:
    if position_jitter_m < 0.0:
        raise ValueError("position_jitter_m must be >= 0.")
    if speed_jitter_frac < 0.0:
        raise ValueError("speed_jitter_frac must be >= 0.")
    if course_jitter_deg < 0.0:
        raise ValueError("course_jitter_deg must be >= 0.")
    if not 0.0 <= float(drop_rate) < 1.0:
        raise ValueError("drop_rate must be in [0, 1).")

    input_path = Path(input_csv_path)
    with input_path.open("r", encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    if not rows:
        raise ValueError("Pairwise CSV is empty.")

    output_root = Path(output_prefix)
    output_root.parent.mkdir(parents=True, exist_ok=True)
    perturbed_csv_path = output_root.with_name(f"{output_root.name}_pairwise.csv")
    summary_json_path = output_root.with_name(f"{output_root.name}_summary.json")
    summary_md_path = output_root.with_name(f"{output_root.name}_summary.md")

    config = load_config(config_path)
    generator = random.Random(int(random_seed))
    output_rows: list[dict[str, str]] = []

    distance_deltas: list[float] = []
    bearing_deltas: list[float] = []
    relspeed_deltas: list[float] = []
    course_deltas: list[float] = []
    rule_score_deltas: list[float] = []
    dropped_rows = 0

    for row in rows:
        if drop_rate > 0.0 and generator.random() < float(drop_rate):
            dropped_rows += 1
            continue

        base_distance_nm = _safe_float(row.get("distance_nm"))
        base_bearing_deg = _safe_float(row.get("relative_bearing_deg"))
        base_relspeed_knots = _safe_float(row.get("relative_speed_knots"))
        base_course_diff_deg = _safe_float(row.get("course_difference_deg"))
        base_tcpa_min = _safe_float(row.get("tcpa_min"))
        base_dcpa_nm = _safe_float(row.get("dcpa_nm"))
        base_rule_score = _safe_float(row.get("rule_score"))

        x_m, y_m = _bearing_to_xy_m(base_distance_nm, base_bearing_deg)
        if position_jitter_m > 0.0:
            x_m += generator.gauss(0.0, float(position_jitter_m))
            y_m += generator.gauss(0.0, float(position_jitter_m))
        perturbed_distance_nm, perturbed_bearing_deg = _xy_to_distance_bearing(x_m, y_m)
        perturbed_bearing_abs_deg = abs(perturbed_bearing_deg)

        relspeed_multiplier = 1.0 + generator.gauss(0.0, float(speed_jitter_frac)) if speed_jitter_frac > 0.0 else 1.0
        perturbed_relspeed_knots = _clamp_nonnegative(base_relspeed_knots * relspeed_multiplier)

        course_delta = generator.gauss(0.0, float(course_jitter_deg)) if course_jitter_deg > 0.0 else 0.0
        perturbed_course_diff_deg = _clamp_course_difference(base_course_diff_deg + course_delta)

        if base_relspeed_knots > 1e-6 and perturbed_relspeed_knots > 1e-6:
            perturbed_tcpa_min = base_tcpa_min * (base_relspeed_knots / perturbed_relspeed_knots)
        else:
            perturbed_tcpa_min = base_tcpa_min
        if base_distance_nm > 1e-6:
            perturbed_dcpa_nm = base_dcpa_nm * (perturbed_distance_nm / base_distance_nm)
        else:
            perturbed_dcpa_nm = base_dcpa_nm

        kinematics = RelativeKinematics(
            dx_m=x_m,
            dy_m=y_m,
            distance_nm=perturbed_distance_nm,
            relative_bearing_deg=perturbed_bearing_deg,
            relative_speed_knots=perturbed_relspeed_knots,
            tcpa_min=perturbed_tcpa_min,
            dcpa_nm=perturbed_dcpa_nm,
            course_difference_deg=perturbed_course_diff_deg,
            encounter_type=str(row.get("encounter_type") or "unknown"),
        )
        risk = compute_pairwise_risk(
            mmsi=str(row.get("target_mmsi") or ""),
            kinematics=kinematics,
            local_target_count=int(_safe_float(row.get("local_target_count"), default=0.0)),
            config=config,
        )

        output_row = dict(row)
        output_row["distance_nm"] = f"{perturbed_distance_nm:.6f}"
        output_row["dcpa_nm"] = f"{perturbed_dcpa_nm:.6f}"
        output_row["tcpa_min"] = f"{perturbed_tcpa_min:.6f}"
        output_row["relative_speed_knots"] = f"{perturbed_relspeed_knots:.6f}"
        output_row["relative_bearing_deg"] = f"{perturbed_bearing_deg:.6f}"
        output_row["bearing_abs_deg"] = f"{perturbed_bearing_abs_deg:.6f}"
        output_row["course_difference_deg"] = f"{perturbed_course_diff_deg:.6f}"
        output_row["rule_score"] = f"{risk.score:.6f}"
        output_row["rule_component_distance"] = f"{risk.components['distance']:.6f}"
        output_row["rule_component_dcpa"] = f"{risk.components['dcpa']:.6f}"
        output_row["rule_component_tcpa"] = f"{risk.components['tcpa']:.6f}"
        output_row["rule_component_bearing"] = f"{risk.components['bearing']:.6f}"
        output_row["rule_component_relspeed"] = f"{risk.components['relspeed']:.6f}"
        output_row["rule_component_encounter"] = f"{risk.components['encounter']:.6f}"
        output_row["rule_component_density"] = f"{risk.components['density']:.6f}"
        output_rows.append(output_row)

        distance_deltas.append(abs(perturbed_distance_nm - base_distance_nm))
        bearing_deltas.append(abs(perturbed_bearing_deg - base_bearing_deg))
        relspeed_deltas.append(abs(perturbed_relspeed_knots - base_relspeed_knots))
        course_deltas.append(abs(perturbed_course_diff_deg - base_course_diff_deg))
        rule_score_deltas.append(abs(risk.score - base_rule_score))

    fieldnames = list(rows[0].keys())
    with perturbed_csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    summary = {
        "status": "completed",
        "input_csv_path": str(input_path),
        "config_path": str(config_path),
        "profile_name": profile_name,
        "random_seed": int(random_seed),
        "position_jitter_m": float(position_jitter_m),
        "speed_jitter_frac": float(speed_jitter_frac),
        "course_jitter_deg": float(course_jitter_deg),
        "drop_rate": float(drop_rate),
        "input_rows": len(rows),
        "output_rows": len(output_rows),
        "dropped_rows": int(dropped_rows),
        "keep_ratio": (len(output_rows) / len(rows)) if rows else 0.0,
        "mean_abs_distance_delta_nm": (sum(distance_deltas) / len(distance_deltas)) if distance_deltas else 0.0,
        "mean_abs_bearing_delta_deg": (sum(bearing_deltas) / len(bearing_deltas)) if bearing_deltas else 0.0,
        "mean_abs_relspeed_delta_knots": (sum(relspeed_deltas) / len(relspeed_deltas)) if relspeed_deltas else 0.0,
        "mean_abs_course_delta_deg": (sum(course_deltas) / len(course_deltas)) if course_deltas else 0.0,
        "mean_abs_rule_score_delta": (sum(rule_score_deltas) / len(rule_score_deltas)) if rule_score_deltas else 0.0,
        "perturbed_csv_path": str(perturbed_csv_path),
        "summary_json_path": str(summary_json_path),
        "summary_md_path": str(summary_md_path),
    }

    summary_json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary_md_path.write_text(build_pairwise_perturbation_summary_markdown(summary), encoding="utf-8")
    return summary
