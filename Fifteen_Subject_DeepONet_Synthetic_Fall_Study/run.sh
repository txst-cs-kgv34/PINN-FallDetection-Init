#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

VENV_DIR="${PINN_VENV_DIR:-${HOME}/.venv}"
export PYTHONUNBUFFERED=1
export PYTORCH_ENABLE_MPS_FALLBACK=1

activate_python() {
  if [[ -f "${VENV_DIR}/bin/activate" ]]; then
    # shellcheck disable=SC1090
    source "${VENV_DIR}/bin/activate"
  elif [[ -f .venv/bin/activate ]]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
  else
    echo "Python environment not found. Run ./run.sh setup first." >&2
    exit 1
  fi
}

command_name="${1:-help}"
if [[ $# -gt 0 ]]; then
  shift
fi

case "${command_name}" in
  setup)
    if [[ ! -d "${VENV_DIR}" ]]; then
      python3 -m venv "${VENV_DIR}"
    fi
    # shellcheck disable=SC1090
    source "${VENV_DIR}/bin/activate"
    python -m pip install --upgrade pip wheel
    python -m pip install -r requirements.txt
    echo "Environment ready: ${VENV_DIR}"
    ;;
  test)
    activate_python
    python -m unittest discover -s tests -v
    python -m compileall -q .
    ;;
  smoke)
    python3 smoke_test.py
    ;;
  validate)
    python3 select_generators.py "$@"
    ;;
  select)
    python3 select_generators.py --copy-checkpoints --overwrite "$@"
    ;;
  generate)
    activate_python
    device="auto"
    if [[ $# -gt 0 && "${1}" != --* ]]; then
      device="${1}"
      shift
    fi
    python generate_synthetic.py --device "${device}" "$@"
    ;;
  quality)
    activate_python
    python quality_check.py "$@"
    ;;
  package)
    python3 package_results.py
    ;;
  pipeline)
    activate_python
    device="auto"
    if [[ $# -gt 0 && "${1}" != --* ]]; then
      device="${1}"
      shift
    fi
    python select_generators.py --copy-checkpoints --overwrite
    python generate_synthetic.py --device "${device}" "$@"
    python quality_check.py
    ;;
  help|-h|--help)
    echo "Usage: ./run.sh {setup|test|smoke|validate|select|generate|quality|package|pipeline} [arguments]"
    echo
    echo "  setup     Install NumPy, SciPy, Matplotlib, and PyTorch."
    echo "  test      Run fixture-based unit tests."
    echo "  smoke     Run a dependency-free 5-fold x 5-seed smoke test."
    echo "  validate  Validate/rank the real runs and write tables only."
    echo "  select    Rank and copy the top two checkpoints per fold."
    echo "  generate  Generate training-context synthetic trajectories."
    echo "  quality   Compare synthetic-real with training real-real variability."
    echo "  package   Package trajectories and quality results without model weights."
    echo "  pipeline  Run select, generate, and quality in sequence."
    ;;
  *)
    echo "Unknown command: ${command_name}" >&2
    exit 2
    ;;
esac
