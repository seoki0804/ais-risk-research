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

usage() {
  cat <<'EOF'
Usage:
  noaa_validation_date_expansion_61day.sh plan [DATE ...]
  noaa_validation_date_expansion_61day.sh bundle [--run-date YYYY-MM-DD] [DATE ...]

Description:
  Print or execute the reviewer-safe same-area NOAA validation date expansion set.
  If no DATE arguments are provided, the script uses the built-in six-date bundle:
    2023-08-08 2023-08-09 2023-09-01 2023-09-05 2023-10-08 2023-10-09

Examples:
  /Users/seoki/Desktop/research/examples/noaa_validation_date_expansion_61day.sh plan
  /Users/seoki/Desktop/research/examples/noaa_validation_date_expansion_61day.sh bundle --run-date 2026-03-17 2023-08-08
EOF
}

mode="plan"
run_date="$(date +%F)"
declare -a selected_dates=()

while (($#)); do
  case "$1" in
    plan|bundle)
      mode="$1"
      shift
      ;;
    --run-date)
      if (($# < 2)); then
        echo "error=missing_run_date_value" >&2
        exit 1
      fi
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

archive_path() {
  local date="$1"
  local dataset_id="noaa_us_coastal_all_${date}_${date}_v1"
  printf '%s/data/raw/noaa/%s/downloads/AIS_%s.zip' \
    "${REPO_ROOT}" \
    "${dataset_id}" \
    "${date//-/_}"
}

dataset_root() {
  local date="$1"
  local dataset_id="noaa_us_coastal_all_${date}_${date}_v1"
  printf '%s/data/raw/noaa/%s' "${REPO_ROOT}" "${dataset_id}"
}

raw_csv_path() {
  local date="$1"
  printf '%s/raw.csv' "$(dataset_root "$date")"
}

focus_csv_path() {
  local date="$1"
  local region="$2"
  printf '%s/raw_focus_%s_0000_2359.csv' "$(dataset_root "$date")" "$region"
}

date_status() {
  local date="$1"
  local zip_path
  local raw_csv
  zip_path="$(archive_path "$date")"
  raw_csv="$(raw_csv_path "$date")"
  if [[ -f "${zip_path}" && -f "${raw_csv}" ]]; then
    printf 'bundle-ready'
  elif [[ -f "${zip_path}" ]]; then
    printf 'archive-ready'
  else
    printf 'fetch-needed'
  fi
}

print_plan() {
  printf 'mode=%s\n' "${mode}"
  printf 'run_date=%s\n' "${run_date}"
  printf 'date_count=%s\n' "${#selected_dates[@]}"
  printf '%-12s %-14s %-5s %-7s %-7s %s\n' "date" "status" "zip" "raw" "focus3" "archive_path"
  for date in "${selected_dates[@]}"; do
    local zip_path
    local raw_csv
    local focus_count=0
    zip_path="$(archive_path "$date")"
    raw_csv="$(raw_csv_path "$date")"
    for region in houston nola seattle; do
      if [[ -f "$(focus_csv_path "$date" "$region")" ]]; then
        focus_count=$((focus_count + 1))
      fi
    done
    printf '%-12s %-14s %-5s %-7s %-7s %s\n' \
      "${date}" \
      "$(date_status "$date")" \
      "$([[ -f "${zip_path}" ]] && printf 'yes' || printf 'no')" \
      "$([[ -f "${raw_csv}" ]] && printf 'yes' || printf 'no')" \
      "${focus_count}/3" \
      "${zip_path}"
  done
}

run_bundle() {
  local date="$1"
  local zip_path
  zip_path="$(archive_path "$date")"

  if [[ ! -f "${zip_path}" ]]; then
    echo "fetch_date=${date}"
    (
      cd "${REPO_ROOT}"
      PYTHONPATH=src python "${REPO_ROOT}/examples/noaa_parallel_download.py" \
        --date "${date}" \
        --parts 8 \
        --max-retries 3 \
        --timeout-sec 90
    )
  fi

  echo "bundle_date=${date}"
  (
    cd "${REPO_ROOT}"
    "${REPO_ROOT}/examples/noaa_daily_bundle_shift_tuning.sh" "${date}" "${run_date}"
  )
}

print_plan

if [[ "${mode}" == "bundle" ]]; then
  for date in "${selected_dates[@]}"; do
    run_bundle "${date}"
  done
fi
