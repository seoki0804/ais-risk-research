#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: $0 <baseline_pairwise_csv> <baseline_predictions_csv> <output_dir> [config_path]" >&2
  exit 1
fi

BASELINE_PAIRWISE="$1"
BASELINE_PREDICTIONS="$2"
OUTPUT_DIR="$3"
CONFIG_PATH="${4:-configs/base.toml}"

mkdir -p "$OUTPUT_DIR"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export PYTHONPATH="$REPO_ROOT/src"

run_profile() {
  local profile="$1"
  local position_jitter="$2"
  local speed_jitter="$3"
  local course_jitter="$4"
  local drop_rate="$5"

  python -m ais_risk.perturbation_sensitivity_cli \
    --baseline-pairwise "$BASELINE_PAIRWISE" \
    --baseline-predictions "$BASELINE_PREDICTIONS" \
    --output-prefix "$OUTPUT_DIR/$profile" \
    --config "$CONFIG_PATH" \
    --model hgbt \
    --split-strategy own_ship \
    --profile-name "$profile" \
    --position-jitter-m "$position_jitter" \
    --speed-jitter-frac "$speed_jitter" \
    --course-jitter-deg "$course_jitter" \
    --drop-rate "$drop_rate" \
    --random-seed 42
}

run_profile "position_25m" 25 0.0 0.0 0.0
run_profile "position_50m" 50 0.0 0.0 0.0
run_profile "speed_10pct" 0 0.10 0.0 0.0
run_profile "course_5deg" 0 0.0 5.0 0.0
run_profile "dropout_10pct" 0 0.0 0.0 0.10
run_profile "combo_moderate" 25 0.10 5.0 0.05

python - <<'PY' "$OUTPUT_DIR"
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
summary_paths = sorted(output_dir.glob("*_summary.json"))
rows = []
for path in summary_paths:
    if path.name.endswith("_perturbation_summary.json"):
        continue
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "delta_f1" not in payload:
        continue
    rows.append(
        {
            "profile_name": payload["profile_name"],
            "delta_f1": payload["delta_f1"],
            "delta_ece": payload["delta_ece"],
            "mean_abs_score_drift": payload["score_drift"]["mean_abs_score_drift"],
            "prediction_flip_rate": payload["score_drift"]["prediction_flip_rate"],
            "top_case_preserved": payload["top_case_preserved"],
            "baseline_case_present_under_perturbation": payload["baseline_case_present_under_perturbation"],
            "delta_case_max_risk_mean": payload["delta_case_max_risk_mean"],
            "delta_case_warning_area_mean_nm2": payload["delta_case_warning_area_mean_nm2"],
            "delta_case_caution_area_mean_nm2": payload["delta_case_caution_area_mean_nm2"],
        }
    )

csv_path = output_dir / "ais_perturbation_profiles_summary_61day.csv"
md_path = output_dir / "ais_perturbation_profiles_summary_61day.md"

with csv_path.open("w", encoding="utf-8") as handle:
    handle.write(
        "profile_name,delta_f1,delta_ece,mean_abs_score_drift,prediction_flip_rate,top_case_preserved,baseline_case_present_under_perturbation,delta_case_max_risk_mean,delta_case_warning_area_mean_nm2,delta_case_caution_area_mean_nm2\n"
    )
    for row in rows:
        handle.write(
            "{profile_name},{delta_f1:.6f},{delta_ece:.6f},{mean_abs_score_drift:.6f},{prediction_flip_rate:.6f},{top_case_preserved},{baseline_case_present_under_perturbation},{delta_case_max_risk_mean},{delta_case_warning_area_mean_nm2},{delta_case_caution_area_mean_nm2}\n".format(
                **row
            )
        )

lines = [
    "# AIS Perturbation Profiles Summary 61day",
    "",
    "| Profile | delta F1 | delta ECE | mean abs score drift | flip rate | top case preserved | same case present | delta case max risk | delta warning area | delta caution area |",
    "|---|---:|---:|---:|---:|---|---|---:|---:|---:|",
]
for row in rows:
    lines.append(
        "| {profile_name} | {delta_f1:.4f} | {delta_ece:.4f} | {mean_abs_score_drift:.4f} | {prediction_flip_rate:.4f} | {top_case_preserved} | {baseline_case_present_under_perturbation} | {delta_case_max_risk_mean} | {delta_case_warning_area_mean_nm2} | {delta_case_caution_area_mean_nm2} |".format(
            **row
        )
    )
md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(csv_path)
print(md_path)
PY
