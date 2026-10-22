#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

MODE="${1:-help}"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

case "$MODE" in
  setup)
    python3 -m venv .venv
    "$PYTHON_BIN" -m pip install --upgrade pip
    "$PYTHON_BIN" -m pip install -r requirements.txt
    ;;
  build)
    "$PYTHON_BIN" tests/validate_project.py
    "$PYTHON_BIN" adapter/build_s63_pole_inputs.py
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
  *)
    echo "Usage: ./run_on_mac.sh {setup|build|input-check|smoke|full|analyze|package}"
    exit 2
    ;;
esac
