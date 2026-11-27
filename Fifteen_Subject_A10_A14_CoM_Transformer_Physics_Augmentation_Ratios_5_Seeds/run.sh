#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${FALL_DETECTOR_VENV:-${HOME}/.venv}"
PYTHON_BIN="${VENV_DIR}/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python not found at ${PYTHON_BIN}. Set FALL_DETECTOR_VENV." >&2
  exit 1
fi

command_name="${1:-}"
if [[ -z "${command_name}" ]]; then
  echo "Usage: ./run.sh {setup|test|smoke|validate|train|compare|all|package-results} [arguments]" >&2
  exit 2
fi
shift
cd "${ROOT_DIR}"

case "${command_name}" in
  setup) "${PYTHON_BIN}" -m pip install -r requirements.txt ;;
  test) "${PYTHON_BIN}" -m unittest discover -s tests -v ;;
  smoke) "${PYTHON_BIN}" smoke_test.py "$@" ;;
  validate) "${PYTHON_BIN}" validate_setup.py "$@" ;;
  train) "${PYTHON_BIN}" train_ratios.py "$@" ;;
  compare) "${PYTHON_BIN}" compare_ratios.py "$@" ;;
  all)
    "${PYTHON_BIN}" validate_setup.py
    "${PYTHON_BIN}" train_ratios.py "$@"
    "${PYTHON_BIN}" compare_ratios.py
    ;;
  package-results) "${PYTHON_BIN}" package_results.py "$@" ;;
  *) echo "Unknown command: ${command_name}" >&2; exit 2 ;;
esac
