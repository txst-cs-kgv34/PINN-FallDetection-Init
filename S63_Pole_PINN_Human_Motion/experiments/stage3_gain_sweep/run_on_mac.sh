#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"

cd "${ROOT_DIR}"

"${PYTHON_BIN}" "experiments/stage3_gain_sweep/check_setup.py"

if ! "${PYTHON_BIN}" -c "import tensorflow, scipy, matplotlib, resampy" >/dev/null 2>&1; then
  echo "Required Python packages are missing from the active environment." >&2
  echo "Activate the environment used for the completed S63 full run, then retry." >&2
  exit 1
fi

command=(
  "${PYTHON_BIN}"
  "experiments/stage3_gain_sweep/run_gain_sweep.py"
  "--chunks" "all"
  "--epochs" "5000"
  "--batch-size" "4096"
)

export PYTHONUNBUFFERED=1

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -i "${command[@]}"
else
  "${command[@]}"
fi

echo
echo "All S63 gain chunks finished. Package the results with:"
echo "  bash experiments/stage3_gain_sweep/package_results.sh"
