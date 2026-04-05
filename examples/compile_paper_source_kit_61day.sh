#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  compile_paper_source_kit_61day.sh [KIT_DIR] [--engine auto|tectonic|xelatex|lualatex|latexmk|pdflatex] [--dry-run]

Description:
  Compile the asset-locked paper source kit if a Unicode-capable LaTeX toolchain is available.

Defaults:
  KIT_DIR  outputs/presentation_deck_outline_61day_2026-03-13/paper_source_kit_61day
  ENGINE   auto

Notes:
  --dry-run validates the kit structure and prints the intended compile command
  even when a local LaTeX toolchain is not installed.
EOF
}

ROOT_DIR="/Users/seoki/Desktop/research"
DEFAULT_KIT_DIR="${ROOT_DIR}/outputs/presentation_deck_outline_61day_2026-03-13/paper_source_kit_61day"
KIT_DIR="${DEFAULT_KIT_DIR}"
ENGINE="auto"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --engine)
      ENGINE="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      if [[ "${KIT_DIR}" == "${DEFAULT_KIT_DIR}" ]]; then
        KIT_DIR="$1"
        shift
      else
        echo "Unexpected argument: $1" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

if [[ ! -d "${KIT_DIR}" ]]; then
  echo "Kit directory not found: ${KIT_DIR}" >&2
  exit 1
fi

TEX_FILE="${KIT_DIR}/paper_conference_8page_asset_locked_61day.tex"
ASSET_DIR="${KIT_DIR}/conference_print_assets_61day"

if [[ ! -f "${TEX_FILE}" ]]; then
  echo "Missing TeX source: ${TEX_FILE}" >&2
  exit 1
fi

if [[ ! -d "${ASSET_DIR}" ]]; then
  echo "Missing asset directory: ${ASSET_DIR}" >&2
  exit 1
fi

resolve_engine() {
  case "${ENGINE}" in
    auto)
      if command -v tectonic >/dev/null 2>&1; then
        echo "tectonic"
      elif command -v xelatex >/dev/null 2>&1; then
        echo "xelatex"
      elif command -v lualatex >/dev/null 2>&1; then
        echo "lualatex"
      elif command -v latexmk >/dev/null 2>&1; then
        echo "latexmk"
      elif command -v pdflatex >/dev/null 2>&1; then
        echo "pdflatex"
      else
        echo "none"
      fi
      ;;
    tectonic|xelatex|lualatex|latexmk|pdflatex)
      echo "${ENGINE}"
      ;;
    *)
      echo "invalid"
      ;;
  esac
}

SELECTED_ENGINE="$(resolve_engine)"

if [[ "${SELECTED_ENGINE}" == "invalid" ]]; then
  echo "Unsupported engine: ${ENGINE}" >&2
  exit 1
fi

if [[ "${SELECTED_ENGINE}" == "none" ]]; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "Kit directory: ${KIT_DIR}"
    echo "Selected engine: none (dry-run only)"
    echo "Command: unavailable locally; install tectonic, xelatex, lualatex, latexmk, or pdflatex to compile"
    exit 0
  fi
  echo "No LaTeX toolchain found. Install tectonic, xelatex, lualatex, latexmk, or pdflatex, then retry." >&2
  exit 2
fi

if [[ "${SELECTED_ENGINE}" == "tectonic" ]] && ! command -v tectonic >/dev/null 2>&1; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "Kit directory: ${KIT_DIR}"
    echo "Selected engine: tectonic (not found locally, dry-run only)"
    echo "Command: tectonic --keep-logs --keep-intermediates $(basename "${TEX_FILE}")"
    exit 0
  fi
  echo "tectonic requested but not found in PATH." >&2
  exit 2
fi

if [[ "${SELECTED_ENGINE}" == "xelatex" ]] && ! command -v xelatex >/dev/null 2>&1; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "Kit directory: ${KIT_DIR}"
    echo "Selected engine: xelatex (not found locally, dry-run only)"
    echo "Command: xelatex -interaction=nonstopmode -halt-on-error $(basename "${TEX_FILE}")"
    exit 0
  fi
  echo "xelatex requested but not found in PATH." >&2
  exit 2
fi

if [[ "${SELECTED_ENGINE}" == "lualatex" ]] && ! command -v lualatex >/dev/null 2>&1; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "Kit directory: ${KIT_DIR}"
    echo "Selected engine: lualatex (not found locally, dry-run only)"
    echo "Command: lualatex -interaction=nonstopmode -halt-on-error $(basename "${TEX_FILE}")"
    exit 0
  fi
  echo "lualatex requested but not found in PATH." >&2
  exit 2
fi

if [[ "${SELECTED_ENGINE}" == "latexmk" ]] && ! command -v latexmk >/dev/null 2>&1; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "Kit directory: ${KIT_DIR}"
    echo "Selected engine: latexmk (not found locally, dry-run only)"
    echo "Command: latexmk -xelatex -interaction=nonstopmode -halt-on-error $(basename "${TEX_FILE}")"
    exit 0
  fi
  echo "latexmk requested but not found in PATH." >&2
  exit 2
fi

if [[ "${SELECTED_ENGINE}" == "pdflatex" ]] && ! command -v pdflatex >/dev/null 2>&1; then
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "Kit directory: ${KIT_DIR}"
    echo "Selected engine: pdflatex (not found locally, dry-run only)"
    echo "Command: pdflatex -interaction=nonstopmode -halt-on-error $(basename "${TEX_FILE}")"
    exit 0
  fi
  echo "pdflatex requested but not found in PATH." >&2
  exit 2
fi

if [[ "${SELECTED_ENGINE}" == "tectonic" ]]; then
  CMD=(tectonic --keep-logs --keep-intermediates "$(basename "${TEX_FILE}")")
elif [[ "${SELECTED_ENGINE}" == "xelatex" ]]; then
  CMD=(xelatex -interaction=nonstopmode -halt-on-error "$(basename "${TEX_FILE}")")
elif [[ "${SELECTED_ENGINE}" == "lualatex" ]]; then
  CMD=(lualatex -interaction=nonstopmode -halt-on-error "$(basename "${TEX_FILE}")")
elif [[ "${SELECTED_ENGINE}" == "latexmk" ]]; then
  CMD=(latexmk -xelatex -interaction=nonstopmode -halt-on-error "$(basename "${TEX_FILE}")")
else
  CMD=(pdflatex -interaction=nonstopmode -halt-on-error "$(basename "${TEX_FILE}")")
fi

echo "Kit directory: ${KIT_DIR}"
echo "Selected engine: ${SELECTED_ENGINE}"
echo "Command: ${CMD[*]}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  exit 0
fi

pushd "${KIT_DIR}" >/dev/null
if [[ "${SELECTED_ENGINE}" == "latexmk" || "${SELECTED_ENGINE}" == "tectonic" ]]; then
  "${CMD[@]}"
else
  "${CMD[@]}"
  "${CMD[@]}"
fi
popd >/dev/null
