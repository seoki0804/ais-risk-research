#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="/Users/seoki/Desktop/research"
DEFAULT_DATES=(
  "2023-08-08"
  "2023-08-09"
  "2023-09-01"
  "2023-09-05"
  "2023-10-08"
  "2023-10-09"
)
REGION_SPECS=(
  "houston|29.0|30.5|-96.0|-94.5|368184980,368198210,368216230,368110070,368221490"
  "nola|29.0|30.5|-91.5|-89.5|368102290,368055920,368119110,367138710,367162750"
  "seattle|47.0|48.5|-123.5|-122.0|366929710,366772760,366759130,366749710,367608860"
)

usage() {
  cat <<'EOF'
Usage:
  noaa_same_area_main_benchmark_61day.sh plan [DATE ...]
  noaa_same_area_main_benchmark_61day.sh run [--run-date YYYY-MM-DD] [DATE ...]

Description:
  Rebuild same-area NOAA daily focus bundles with main benchmark label distance 0.5 nm
  and run hgbt/logreg benchmarks for both own_ship and timestamp split.

Examples:
  /Users/seoki/Desktop/research/examples/noaa_same_area_main_benchmark_61day.sh plan
  /Users/seoki/Desktop/research/examples/noaa_same_area_main_benchmark_61day.sh run --run-date 2026-03-17 2023-08-08
EOF
}

mode="plan"
run_date="$(date +%F)"
declare -a selected_dates=()

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
      selected_dates+=("$1")
      shift
      ;;
  esac
done

if ((${#selected_dates[@]} == 0)); then
  selected_dates=("${DEFAULT_DATES[@]}")
fi

raw_csv_path() {
  local date="$1"
  printf '%s/data/raw/noaa/noaa_us_coastal_all_%s_%s_v1/raw.csv' "${REPO_ROOT}" "${date}" "${date}"
}

bundle_prefix() {
  local date="$1"
  printf '%s/outputs/noaa_focus_pairwise_bundle_mainlabel_61day_%s/noaa_focus_pairwise_bundle_mainlabel_%s' \
    "${REPO_ROOT}" "${run_date}" "${date}"
}

bundle_dir() {
  local date="$1"
  printf '%s' "$(bundle_prefix "$date")"
}

region_dataset_path() {
  local date="$1"
  local region="$2"
  printf '%s/%s_pairwise_dataset.csv' "$(bundle_dir "$date")" "${region}"
}

benchmark_prefix() {
  local date="$1"
  local region="$2"
  local split="$3"
  printf '%s/outputs/noaa_same_area_main_benchmark_61day_%s/%s_%s_%s' \
    "${REPO_ROOT}" "${run_date}" "${region}" "${date}" "${split}"
}

print_plan() {
  printf 'mode=%s\n' "${mode}"
  printf 'run_date=%s\n' "${run_date}"
  printf 'date_count=%s\n' "${#selected_dates[@]}"
  printf '%-12s %-5s %s\n' "date" "raw" "main_bundle_prefix"
  for date in "${selected_dates[@]}"; do
    local raw_csv
    raw_csv="$(raw_csv_path "$date")"
    printf '%-12s %-5s %s\n' \
      "${date}" \
      "$([[ -f "${raw_csv}" ]] && printf 'yes' || printf 'no')" \
      "$(bundle_prefix "$date")"
  done
}

run_bundle() {
  local date="$1"
  local raw_csv
  raw_csv="$(raw_csv_path "$date")"
  if [[ ! -f "${raw_csv}" ]]; then
    echo "error=missing_raw_csv date=${date} path=${raw_csv}" >&2
    exit 1
  fi

  local out_prefix
  out_prefix="$(bundle_prefix "$date")"
  mkdir -p "$(dirname "${out_prefix}")"

  (
    cd "${REPO_ROOT}"
    PYTHONPATH=src python -m ais_risk.noaa_focus_pairwise_bundle_cli \
      --raw-input "${raw_csv}" \
      --output-prefix "${out_prefix}" \
      --source-preset noaa_accessais \
      --start-time "${date}T00:00:00Z" \
      --end-time "${date}T23:59:59Z" \
      --time-label 0000_2359 \
      --pairwise-sample-every 5 \
      --pairwise-max-timestamps-per-ship 120 \
      --pairwise-label-distance-nm 0.5 \
      --region "${REGION_SPECS[0]}" \
      --region "${REGION_SPECS[1]}" \
      --region "${REGION_SPECS[2]}"
  )
}

run_benchmark() {
  local date="$1"
  local region="$2"
  local split="$3"
  local dataset
  dataset="$(region_dataset_path "$date" "$region")"
  local out_prefix
  out_prefix="$(benchmark_prefix "$date" "$region" "$split")"
  mkdir -p "$(dirname "${out_prefix}")"

  (
    cd "${REPO_ROOT}"
    PYTHONPATH=src python -m ais_risk.benchmark_cli \
      --input "${dataset}" \
      --output-prefix "${out_prefix}" \
      --models hgbt,logreg \
      --split-strategy "${split}"
  )
}

print_plan

if [[ "${mode}" == "run" ]]; then
  for date in "${selected_dates[@]}"; do
    echo "main_bundle_date=${date}"
    run_bundle "${date}"
    for region in houston nola seattle; do
      echo "benchmark_date=${date} region=${region} split=own_ship"
      run_benchmark "${date}" "${region}" "own_ship"
      echo "benchmark_date=${date} region=${region} split=timestamp"
      run_benchmark "${date}" "${region}" "timestamp"
    done
  done
fi
