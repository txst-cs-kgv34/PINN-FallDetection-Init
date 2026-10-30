#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_ACTIVATE="$HOME/.venv/bin/activate"

cd "${ROOT_DIR}"

if [[ ! -f "${VENV_ACTIVATE}" ]]; then
  echo "Home virtual environment not found: ${VENV_ACTIVATE}" >&2
  exit 1
fi

source "${VENV_ACTIVATE}"
PYTHON_BIN="$(command -v python)"

if ! "${PYTHON_BIN}" -c "import tensorflow, scipy, matplotlib, resampy" >/dev/null 2>&1; then
  echo "Required Python packages are missing from the active environment." >&2
  echo "Install the project requirements in ~/.venv, then retry." >&2
  exit 1
fi

"${PYTHON_BIN}" "experiments/stage3_gain_sweep/validate_setup.py"

command=(
  "${PYTHON_BIN}"
  "experiments/stage3_gain_sweep/run_gain_sweep.py"
  "--chunks" "all"
  "--epochs" "5000"
  "--batch-size" "4096"
)

export PYTHONUNBUFFERED=1
mkdir -p "experiments/stage3_gain_sweep/results"
LOG_FILE="experiments/stage3_gain_sweep/results/gain_sweep.log"

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -i "${command[@]}" 2>&1 | tee "${LOG_FILE}"
else
  "${command[@]}" 2>&1 | tee "${LOG_FILE}"
fi

echo
echo "Gain sweep finished. Package results with:"
echo "  bash experiments/stage3_gain_sweep/package_results.sh"
