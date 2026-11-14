#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

VENV_DIR="${FALL_DETECTOR_VENV:-${HOME}/.venv}"
PYTHON_BIN="${VENV_DIR}/bin/python"
export PYTORCH_ENABLE_MPS_FALLBACK="${PYTORCH_ENABLE_MPS_FALLBACK:-1}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python was not found at ${PYTHON_BIN}." >&2
  echo "Set FALL_DETECTOR_VENV to your existing virtual-environment directory." >&2
  exit 1
fi

command_name="${1:-help}"
if [[ $# -gt 0 ]]; then
  shift
fi

case "${command_name}" in
  validate)
    "${PYTHON_BIN}" validate_setup.py "$@"
    ;;
  test)
    "${PYTHON_BIN}" -m unittest discover -s tests -v
    "${PYTHON_BIN}" -m compileall -q .
    ;;
  smoke)
    "${PYTHON_BIN}" smoke_test.py
    ;;
  real)
    "${PYTHON_BIN}" train_scenario.py --scenario real_fall_real_adl "$@"
    ;;
  synthetic|syn)
    "${PYTHON_BIN}" train_scenario.py --scenario synthetic_fall_real_adl "$@"
    ;;
  combined)
    "${PYTHON_BIN}" train_scenario.py --scenario real_synthetic_fall_real_adl "$@"
    ;;
  all)
    "${PYTHON_BIN}" train_scenario.py --scenario real_fall_real_adl "$@"
    "${PYTHON_BIN}" train_scenario.py --scenario synthetic_fall_real_adl "$@"
    "${PYTHON_BIN}" train_scenario.py --scenario real_synthetic_fall_real_adl "$@"
    "${PYTHON_BIN}" compare_scenarios.py
    ;;
  compare)
    "${PYTHON_BIN}" compare_scenarios.py "$@"
    "${PYTHON_BIN}" make_comparison_figures.py "$@"
    ;;
  package-results)
    "${PYTHON_BIN}" package_results.py "$@"
    ;;
  help|-h|--help)
    echo "Usage: ./run.sh {validate|test|smoke|real|synthetic|combined|all|compare|package-results} [arguments]"
    ;;
  *)
    echo "Unknown command: ${command_name}" >&2
    exit 2
    ;;
esac

