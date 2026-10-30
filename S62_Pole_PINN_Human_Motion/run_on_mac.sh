#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

MODE="${1:-help}"
VENV_ACTIVATE="$HOME/.venv/bin/activate"

if [[ ! -f "$VENV_ACTIVATE" ]]; then
  echo "Home virtual environment not found: $VENV_ACTIVATE" >&2
  echo "Create it first with: python3 -m venv \"$HOME/.venv\"" >&2
  exit 1
fi

# Use the existing home virtual environment for every command.
source "$VENV_ACTIVATE"
PYTHON_BIN="$(command -v python)"

case "$MODE" in
  setup)
    "$PYTHON_BIN" -m pip install --upgrade pip
    "$PYTHON_BIN" -m pip install -r requirements.txt
    "$PYTHON_BIN" -c 'import platform, tensorflow as tf; print("Python:", platform.python_version()); print("Machine:", platform.machine()); print("TensorFlow:", tf.__version__)'
    ;;
  build)
    "$PYTHON_BIN" tests/validate_project.py
    "$PYTHON_BIN" adapter/build_s62_pole_inputs.py
    "$PYTHON_BIN" tests/validate_inputs.py
    ;;
  input-check)
    "$PYTHON_BIN" runner/run_pipeline.py --mode input-check
    ;;
  smoke)
    mkdir -p results/smoke_run
    "$PYTHON_BIN" runner/run_pipeline.py --mode smoke 2>&1 | tee results/smoke_run/smoke_run.log
    "$PYTHON_BIN" tests/validate_smoke.py
    ;;
  full)
    mkdir -p results/full_run
    "$PYTHON_BIN" runner/run_pipeline.py --mode full 2>&1 | tee results/full_run/full_run.log
    ;;
  analyze)
    "$PYTHON_BIN" analysis/evaluate_full_run.py
    "$PYTHON_BIN" analysis/compare_original_synthetic_distributions.py
    "$PYTHON_BIN" analysis/visualize_trajectories.py --horizon 5
    ;;
  package)
    "$PYTHON_BIN" runner/package_results.py
    ;;
  gain-sweep)
    bash experiments/stage3_gain_sweep/run_on_mac.sh
    ;;
  gain-sweep-package)
    bash experiments/stage3_gain_sweep/package_results.sh
    ;;
  *)
    echo "Usage: ./run_on_mac.sh {setup|build|input-check|smoke|full|analyze|package|gain-sweep|gain-sweep-package}"
    exit 2
    ;;
esac
