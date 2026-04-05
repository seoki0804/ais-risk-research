#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/seoki/Desktop/research"
RUN_TAG="${1:-2026-03-19_r1}"
OUT_ROOT="${ROOT}/outputs/${RUN_TAG}_leakfix_same_day_matrix"
mkdir -p "${OUT_ROOT}"

NY_NJ_2023_DATES=(2023-09-01 2023-09-05 2023-10-08)
LA_LB_2023_DATES=(2023-09-01 2023-09-02 2023-09-05)
NY_NJ_2024_DATES=(2024-09-01 2024-09-05 2024-10-08)
SEATTLE_2024_DATES=(2024-09-01 2024-09-05 2024-10-08)

RUN_NY_NJ_2023="${RUN_NY_NJ_2023:-1}"
RUN_LA_LB_2023="${RUN_LA_LB_2023:-1}"
RUN_NY_NJ_2024="${RUN_NY_NJ_2024:-1}"
RUN_SEATTLE_2024="${RUN_SEATTLE_2024:-1}"

ny_nj_2024_base() {
  case "$1" in
    2024-09-01) echo "${ROOT}/outputs/2026-03-17_r31_expand_cross_year_2024_candidate_scan/ny_nj_2024_20240901" ;;
    2024-09-05) echo "${ROOT}/outputs/2026-03-17_r27_expand_cross_year_2024_candidate_scan/ny_nj_2024_20240905" ;;
    2024-10-08) echo "${ROOT}/outputs/2026-03-17_r29_expand_cross_year_2024_candidate_scan/ny_nj_2024_20241008" ;;
    *)
      echo "error=unsupported_ny_nj_2024_date date=$1" >&2
      return 1
      ;;
  esac
}

seattle_2024_base() {
  case "$1" in
    2024-09-01) echo "${ROOT}/outputs/2026-03-17_r54_cross_year_2024_candidate_scan/seattle_2024_20240901" ;;
    2024-09-05) echo "${ROOT}/outputs/2026-03-17_r52_cross_year_2024_candidate_scan/seattle_2024_20240905" ;;
    2024-10-08) echo "${ROOT}/outputs/2026-03-17_r55_cross_year_2024_candidate_scan/seattle_2024_20241008" ;;
    *)
      echo "error=unsupported_seattle_2024_date date=$1" >&2
      return 1
      ;;
  esac
}

ny_nj_2023_region_spec() {
  case "$1" in
    2023-09-01) echo "ny_nj|40.3|41.1|-74.5|-73.5|367682610,338862000,366939710,367428270,338073000,368325040,367671080,368056750,367618310,366998820" ;;
    2023-09-05) echo "ny_nj|40.3|41.1|-74.5|-73.5|367351520,368056750,366952890,367682610,367770270,338073000,369131000,367618310" ;;
    2023-10-08) echo "ny_nj|40.3|41.1|-74.5|-73.5|368217570,368143050,368325040,367770270,366727190,367618310,367515850,367686910,367336190,367314640,367671080,338862000" ;;
    *)
      echo "error=unsupported_ny_nj_2023_date date=$1" >&2
      return 1
      ;;
  esac
}

la_lb_2023_region_spec() {
  case "$1" in
    2023-09-01) echo "la_long_beach|33.4|34.2|-118.6|-117.7|366755010,368010330,368024740,366892000,366760650" ;;
    2023-09-02) echo "la_long_beach|33.4|34.2|-118.6|-117.7|368171260,368171390,355263000,369207000,366892000,351848000,367199310" ;;
    2023-09-05) echo "la_long_beach|33.4|34.2|-118.6|-117.7|366755010,366892000,366760650,368010330" ;;
    *)
      echo "error=unsupported_la_lb_2023_date date=$1" >&2
      return 1
      ;;
  esac
}

echo "run_tag=${RUN_TAG}"
echo "out_root=${OUT_ROOT}"

if [[ "${RUN_NY_NJ_2023}" == "1" ]]; then
  for date in "${NY_NJ_2023_DATES[@]}"; do
    spec="$(ny_nj_2023_region_spec "${date}")"
    echo "run=ny_nj_2023 date=${date}"
    REGION_SPEC_OVERRIDE="${spec}" \
      bash "${ROOT}/examples/run_true_new_area_ny_nj_pilot_61day.sh" "${date}" "${RUN_TAG}_nynj2023"
  done
fi

if [[ "${RUN_LA_LB_2023}" == "1" ]]; then
  for date in "${LA_LB_2023_DATES[@]}"; do
    spec="$(la_lb_2023_region_spec "${date}")"
    echo "run=la_lb_2023 date=${date}"
    REGION_SPEC_OVERRIDE="${spec}" \
      bash "${ROOT}/examples/run_true_new_area_la_long_beach_pilot_61day.sh" "${date}" "${RUN_TAG}_lalb2023"
  done
fi

if [[ "${RUN_NY_NJ_2024}" == "1" ]]; then
  for date in "${NY_NJ_2024_DATES[@]}"; do
    base="$(ny_nj_2024_base "${date}")"
    echo "run=ny_nj_2024 date=${date} base=${base}"
    RAW_CSV_OVERRIDE="${base}/raw_from_parquet.csv" \
    QUALITY_ROWS_OVERRIDE="${base}/quality_gate_rows.csv" \
      bash "${ROOT}/examples/run_cross_year_2024_ny_nj_pilot_61day.sh" "${date}" "${RUN_TAG}_nynj2024"
  done
fi

if [[ "${RUN_SEATTLE_2024}" == "1" ]]; then
  for date in "${SEATTLE_2024_DATES[@]}"; do
    base="$(seattle_2024_base "${date}")"
    echo "run=seattle_2024 date=${date} base=${base}"
    RAW_CSV_OVERRIDE="${base}/raw_from_parquet.csv" \
    QUALITY_ROWS_OVERRIDE="${base}/quality_gate_rows.csv" \
      bash "${ROOT}/examples/run_cross_year_2024_seattle_pilot_61day.sh" "${date}" "${RUN_TAG}_seattle2024"
  done
fi

SUMMARY_CSV="${OUT_ROOT}/same_day_leakfix_matrix_summary_61day.csv"
SUMMARY_MD="${OUT_ROOT}/same_day_leakfix_matrix_summary_61day.md"

python - <<'PY' "${ROOT}" "${RUN_TAG}" "${SUMMARY_CSV}" "${SUMMARY_MD}"
import csv
import json
import os
import sys

root = sys.argv[1]
run_tag = sys.argv[2]
summary_csv = sys.argv[3]
summary_md = sys.argv[4]

records = []

def maybe_add(region, year, date, own_path, ts_path):
    for split, path in [("own_ship", own_path), ("timestamp", ts_path)]:
        if not os.path.exists(path):
            records.append(
                {
                    "region": region,
                    "year": year,
                    "date": date,
                    "split": split,
                    "status": "missing",
                    "summary_path": path,
                }
            )
            continue
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        hgbt = data.get("models", {}).get("hgbt", {})
        logreg = data.get("models", {}).get("logreg", {})
        status = "ok"
        if hgbt.get("status") == "skipped" or logreg.get("status") == "skipped":
            status = "skipped"
        records.append(
            {
                "region": region,
                "year": year,
                "date": date,
                "split": split,
                "status": status,
                "row_count": data.get("row_count"),
                "positive_rate": data.get("positive_rate"),
                "own_ship_count": data.get("own_ship_count"),
                "hgbt_f1": hgbt.get("f1"),
                "hgbt_auroc": hgbt.get("auroc"),
                "hgbt_auprc": hgbt.get("auprc"),
                "hgbt_threshold": hgbt.get("threshold"),
                "logreg_f1": logreg.get("f1"),
                "summary_path": path,
            }
        )

for date in ["2023-09-01", "2023-09-05", "2023-10-08"]:
    tag = date.replace("-", "")
    base = f"{root}/outputs/{run_tag}_nynj2023_true_new_area_ny_nj_{tag}"
    maybe_add(
        "ny_nj",
        "2023",
        date,
        f"{base}/ny_nj_{date}_own_ship_summary.json",
        f"{base}/ny_nj_{date}_timestamp_summary.json",
    )

for date in ["2023-09-01", "2023-09-02", "2023-09-05"]:
    tag = date.replace("-", "")
    base = f"{root}/outputs/{run_tag}_lalb2023_true_new_area_la_long_beach_{tag}"
    maybe_add(
        "la_long_beach",
        "2023",
        date,
        f"{base}/la_long_beach_{date}_own_ship_summary.json",
        f"{base}/la_long_beach_{date}_timestamp_summary.json",
    )

for date in ["2024-09-01", "2024-09-05", "2024-10-08"]:
    tag = date.replace("-", "")
    base = f"{root}/outputs/{run_tag}_nynj2024_cross_year_2024_ny_nj_pilot_{tag}"
    maybe_add(
        "ny_nj",
        "2024",
        date,
        f"{base}/ny_nj_2024_{date}_own_ship_summary.json",
        f"{base}/ny_nj_2024_{date}_timestamp_summary.json",
    )

for date in ["2024-09-01", "2024-09-05", "2024-10-08"]:
    tag = date.replace("-", "")
    base = f"{root}/outputs/{run_tag}_seattle2024_cross_year_2024_seattle_pilot_{tag}"
    maybe_add(
        "seattle",
        "2024",
        date,
        f"{base}/seattle_2024_{date}_own_ship_summary.json",
        f"{base}/seattle_2024_{date}_timestamp_summary.json",
    )

fieldnames = [
    "region",
    "year",
    "date",
    "split",
    "status",
    "row_count",
    "positive_rate",
    "own_ship_count",
    "hgbt_f1",
    "hgbt_auroc",
    "hgbt_auprc",
    "hgbt_threshold",
    "logreg_f1",
    "summary_path",
]

os.makedirs(os.path.dirname(summary_csv), exist_ok=True)
with open(summary_csv, "w", encoding="utf-8", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for row in records:
        writer.writerow(row)

with open(summary_md, "w", encoding="utf-8") as handle:
    def fmt_num(value, digits):
        if value is None:
            return "n/a"
        return f"{value:.{digits}f}"

    handle.write("# Same-Day Leak-Fix Matrix Summary 61day\n\n")
    handle.write("| Region | Year | Date | Split | hgbt F1 | hgbt AUROC | hgbt AUPRC | thr | logreg F1 | Status |\n")
    handle.write("|---|---:|---|---|---:|---:|---:|---:|---:|---|\n")
    for row in records:
        if row.get("status") != "ok":
            label = row.get("status") or "missing"
            handle.write(
                f"| {row['region']} | {row['year']} | {row['date']} | {row['split']} | n/a | n/a | n/a | n/a | n/a | {label} |\n"
            )
            continue
        handle.write(
            f"| {row['region']} | {row['year']} | {row['date']} | {row['split']} | "
            f"{fmt_num(row['hgbt_f1'], 4)} | {fmt_num(row['hgbt_auroc'], 4)} | {fmt_num(row['hgbt_auprc'], 4)} | "
            f"{fmt_num(row['hgbt_threshold'], 2)} | {fmt_num(row['logreg_f1'], 4)} | ok |\n"
        )

print(f"summary_csv={summary_csv}")
print(f"summary_md={summary_md}")
PY

echo "done=1"
