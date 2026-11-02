#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

MODE="${1:-help}"
export PYTHONUNBUFFERED=1
export PYTORCH_ENABLE_MPS_FALLBACK=1

activate_home_python() {
  if [[ ! -f ~/.venv/bin/activate ]]; then
    echo "Missing ~/.venv/bin/activate. Create the home virtual environment first." >&2
    exit 1
  fi
  # User-requested shared MacBook environment.
  source ~/.venv/bin/activate
}

run_logged() {
  local log_file="$1"
  shift
  mkdir -p "$(dirname "$log_file")"
  "$@" 2>&1 | tee "$log_file"
}

case "$MODE" in
  setup)
    activate_home_python
    python -m pip install --upgrade pip wheel
    python -m pip install -r requirements.txt
    ;;
  validate)
    activate_home_python
    python -u validate_setup.py
    ;;
  prepare)
    activate_home_python
    run_logged results/logs/export_teachers.log python -u export_teacher_data.py --mode full --overwrite
    run_logged results/logs/prepare_real.log python -u prepare_real_data.py --mode full --overwrite
    ;;
  smoke)
    activate_home_python
    python -u validate_setup.py
    run_logged results/logs/smoke_export.log python -u export_teacher_data.py --mode smoke --overwrite
    run_logged results/logs/smoke_real.log python -u prepare_real_data.py --mode smoke --overwrite
    run_logged results/logs/smoke_fold1.log python -u train_fold.py --mode smoke --fold 1 --device auto
    ;;
  fold)
    activate_home_python
    FOLD_ID="${2:?Usage: ./run_on_mac.sh fold FOLD_ID}"
    run_logged "results/logs/full_fold_${FOLD_ID}.log" python -u train_fold.py --mode full --fold "$FOLD_ID" --device auto
    ;;
  full)
    activate_home_python
    python -u validate_setup.py
    if [[ ! -f outputs/teacher_data_full/teacher_manifest.json ]]; then
      run_logged results/logs/export_teachers.log python -u export_teacher_data.py --mode full --overwrite
    fi
    if [[ ! -f outputs/real_data_full/real_manifest.json ]]; then
      run_logged results/logs/prepare_real.log python -u prepare_real_data.py --mode full --overwrite
    fi
    for fold_id in 1 2 3 4 5; do
      run_logged "results/logs/full_fold_${fold_id}.log" python -u train_fold.py --mode full --fold "$fold_id" --device auto
    done
    python -u aggregate_results.py --mode full
    python -u package_results.py
    ;;
  aggregate)
    activate_home_python
    python -u aggregate_results.py --mode full
    ;;
  package)
    activate_home_python
    python -u package_results.py
    ;;
  test)
    activate_home_python
    python -m unittest discover -s tests -v
    python -m compileall -q .
    ;;
  help|*)
    cat <<'EOF'
Usage: ./run_on_mac.sh MODE

Modes:
  setup              Install packages into ~/.venv
  validate           Check all five external subject projects and fold isolation
  prepare            Generate five teacher datasets and prepare held-out real data
  smoke              Small end-to-end test using fold 1
  fold FOLD_ID       Run one full fold (1-5)
  full               Prepare if needed, run all five folds, aggregate, and package
  aggregate          Rebuild cross-fold summary
  package            Create the result ZIP
  test               Run lightweight protocol and syntax tests
EOF
    ;;
esac

