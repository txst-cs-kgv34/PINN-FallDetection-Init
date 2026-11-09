#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

MODE="${1:-help}"
export PYTHONUNBUFFERED=1
export PYTORCH_ENABLE_MPS_FALLBACK=1
VENV_ACTIVATE="${HOME}/.venv/bin/activate"

activate_python() {
  if [[ ! -f "$VENV_ACTIVATE" ]]; then
    echo "Missing ${HOME}/.venv. Run './run.sh setup' first." >&2
    exit 1
  fi
  source "$VENV_ACTIVATE"
}

run_logged() {
  local log_file="$1"
  shift
  mkdir -p "$(dirname "$log_file")"
  "$@" 2>&1 | tee "$log_file"
}

prepare_data() {
  local data_mode="${1:-full}"
  run_logged results/logs/prepare_audit_inputs.log \
    python -u prepare_audit_inputs.py --overwrite
  run_logged "results/logs/prepare_real_${data_mode}.log" \
    python -u prepare_real_data.py --mode "$data_mode" --overwrite
}

case "$MODE" in
  setup)
    if [[ ! -f "$VENV_ACTIVATE" ]]; then
      python3 -m venv "${HOME}/.venv"
    fi
    source "$VENV_ACTIVATE"
    python -m pip install --upgrade pip wheel
    python -m pip install -r requirements.txt
    ;;
  validate)
    activate_python
    python -u validate_setup.py
    ;;
  prepare)
    activate_python
    prepare_data full
    ;;
  smoke)
    activate_python
    python -u validate_setup.py
    prepare_data smoke
    DEVICE="${2:-auto}"
    run_logged results/logs/smoke_fold1.log \
      python -u train_fold.py --mode smoke --fold 1 --device "$DEVICE"
    ;;
  fold)
    activate_python
    FOLD_ID="${2:?Usage: ./run.sh fold FOLD_ID [auto|cuda|mps|cpu]}"
    DEVICE="${3:-auto}"
    if [[ ! -f outputs/real_data_full/real_manifest.json ]]; then
      prepare_data full
    fi
    run_logged "results/logs/full_fold_${FOLD_ID}.log" \
      python -u train_fold.py --mode full --fold "$FOLD_ID" --device "$DEVICE"
    ;;
  full)
    activate_python
    DEVICE="${2:-auto}"
    python -u validate_setup.py
    prepare_data full
    for fold_id in 1 2 3 4 5; do
      run_logged "results/logs/full_fold_${fold_id}.log" \
        python -u train_fold.py --mode full --fold "$fold_id" --device "$DEVICE"
    done
    python -u aggregate_results.py --mode full
    python -u package_results.py
    ;;
  aggregate)
    activate_python
    python -u aggregate_results.py --mode full
    ;;
  package)
    activate_python
    python -u package_results.py
    ;;
  test)
    activate_python
    python -m unittest discover -s tests -v
    python -m compileall -q .
    ;;
  help|*)
    sed -n '/^Usage:/,$p' README.md
    ;;
esac
