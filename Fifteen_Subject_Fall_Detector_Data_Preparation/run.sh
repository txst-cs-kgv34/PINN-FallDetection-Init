#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

VENV_DIR="${FALL_DETECTOR_VENV:-${HOME}/.venv}"
PYTHON_BIN="${VENV_DIR}/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python was not found at ${PYTHON_BIN}." >&2
  echo "Set FALL_DETECTOR_VENV to the existing virtual-environment directory if it is stored elsewhere." >&2
  exit 1
fi

command_name="${1:-help}"
if [[ $# -gt 0 ]]; then
  shift
fi

case "${command_name}" in
  test)
    "${PYTHON_BIN}" -m unittest discover -s tests -v
    "${PYTHON_BIN}" -m compileall -q .
    ;;
  prepare)
    "${PYTHON_BIN}" prepare_detector_data.py "$@"
    ;;
  all)
    output_dir="${ROOT_DIR}/outputs"
    all_args=("$@")
    for ((index=0; index<${#all_args[@]}; index++)); do
      if [[ "${all_args[index]}" == "--output-dir" && $((index + 1)) -lt ${#all_args[@]} ]]; then
        output_dir="${all_args[index + 1]}"
      elif [[ "${all_args[index]}" == --output-dir=* ]]; then
        output_dir="${all_args[index]#--output-dir=}"
      fi
    done
    "${PYTHON_BIN}" prepare_detector_data.py "$@"
    "${PYTHON_BIN}" validate_dataset.py --output-dir "${output_dir}"
    "${PYTHON_BIN}" analyze_prepared_data.py --output-dir "${output_dir}"
    ;;
  validate)
    "${PYTHON_BIN}" validate_dataset.py "$@"
    ;;
  analyze)
    "${PYTHON_BIN}" analyze_prepared_data.py "$@"
    ;;
  package)
    "${PYTHON_BIN}" package_results.py
    ;;
  help|-h|--help)
    echo "Usage: ./run.sh {test|prepare|all|validate|analyze|package} [arguments]"
    ;;
  *)
    echo "Unknown command: ${command_name}" >&2
    exit 2
    ;;
esac
