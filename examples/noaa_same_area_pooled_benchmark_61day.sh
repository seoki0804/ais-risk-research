#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/seoki/Desktop/research"
DEFAULT_RUN_DATE="2026-03-17"
DEFAULT_DATES=(
  "2023-08-08"
  "2023-08-09"
  "2023-09-01"
  "2023-09-05"
  "2023-10-08"
  "2023-10-09"
)
REGIONS=(houston nola seattle)

usage() {
  cat <<'EOF'
Usage:
  noaa_same_area_pooled_benchmark_61day.sh plan
  noaa_same_area_pooled_benchmark_61day.sh run [--run-date YYYY-MM-DD]

Description:
  Pool the six main-label daily pairwise CSVs per region and run hgbt/logreg
  benchmarks for own_ship and timestamp split.
EOF
}

mode="plan"
run_date="${DEFAULT_RUN_DATE}"

while (($#)); do
  case "$1" in
    plan|run)
      mode="$1"
      shift
      ;;
    --run-date)
      run_date="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error=unknown_arg value=$1" >&2
      exit 1
      ;;
  esac
done

pooled_root="${REPO_ROOT}/outputs/noaa_same_area_pooled_benchmark_61day_${run_date}"

echo "mode=${mode}"
echo "run_date=${run_date}"
echo "pooled_root=${pooled_root}"
printf 'dates=%s\n' "$(IFS=,; echo "${DEFAULT_DATES[*]}")"

if [[ "${mode}" == "run" ]]; then
  mkdir -p "${pooled_root}"
  for region in "${REGIONS[@]}"; do
    pooled_csv="${pooled_root}/${region}_pooled_pairwise.csv"
    pooled_summary="${pooled_root}/${region}_pooled_pairwise_summary.json"
    (
      cd "${REPO_ROOT}"
      python "${REPO_ROOT}/examples/build_same_area_pooled_pairwise_61day.py" \
        --region "${region}" \
        --run-date "${run_date}" \
        --output "${pooled_csv}" \
        --summary-json "${pooled_summary}"
    )
    for split in own_ship timestamp; do
      out_prefix="${pooled_root}/${region}_pooled_${split}"
      (
        cd "${REPO_ROOT}"
        PYTHONPATH=src python -m ais_risk.benchmark_cli \
          --input "${pooled_csv}" \
          --output-prefix "${out_prefix}" \
          --models hgbt,logreg \
          --split-strategy "${split}"
      )
    done
  done
fi
