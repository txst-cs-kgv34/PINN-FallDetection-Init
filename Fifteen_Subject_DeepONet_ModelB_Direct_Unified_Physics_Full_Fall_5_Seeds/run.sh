#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

MODE="${1:-help}"
VENV_DIR="${PINN_VENV_DIR:-$HOME/.venv}"
export PYTHONUNBUFFERED=1
export PYTORCH_ENABLE_MPS_FALLBACK=1

activate_python() {
  if [[ -f "$VENV_DIR/bin/activate" ]]; then
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
  elif [[ -f .venv/bin/activate ]]; then
    echo "Using legacy project environment .venv; run ./run.sh setup to create $VENV_DIR." >&2
    # shellcheck disable=SC1091
    source .venv/bin/activate
  else
    echo "Python environment not found. Run ./run.sh setup first (default: $VENV_DIR)." >&2
    exit 1
  fi
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
  run_logged "results/logs/validate_full_fall_${data_mode}.log" \
    python -u validate_prepared_full_fall.py --mode "$data_mode"
}

seed_count() {
  python - <<'PY'
import json
print(len(json.load(open("experiment.json", encoding="utf-8"))["optimization_seeds"]))
PY
}

seed_label() {
  local seed_index="$1"
  python - "$seed_index" <<'PY'
import json, sys
seeds = json.load(open("experiment.json", encoding="utf-8"))["optimization_seeds"]
index = int(sys.argv[1])
if index < 1 or index > len(seeds):
    raise SystemExit(f"seed index must be between 1 and {len(seeds)}")
print(f"seed_{index:02d}_{int(seeds[index - 1])}")
PY
}

ensure_full_data() {
  if [[ ! -f outputs/real_data_full/real_manifest.json ]]; then
    prepare_data full
  fi
}

run_one_fold() {
  local data_mode="$1"
  local seed_index="$2"
  local fold_id="$3"
  local device="$4"
  local label
  label="$(seed_label "$seed_index")"
  local summary="results/${data_mode}/${label}/fold_$(printf '%02d' "$fold_id")/summary.json"
  if [[ -f "$summary" && "${FORCE:-0}" != "1" ]]; then
    echo "Skipping completed ${data_mode} ${label} fold ${fold_id}; set FORCE=1 to rerun."
    return
  fi
  run_logged "results/logs/${data_mode}_${label}_fold_${fold_id}.log" \
    python -u train_fold.py \
      --mode "$data_mode" \
      --seed-index "$seed_index" \
      --fold "$fold_id" \
      --device "$device"
}

run_seed() {
  local seed_index="$1"
  local device="$2"
  for fold_id in 1 2 3 4 5; do
    run_one_fold full "$seed_index" "$fold_id" "$device"
  done
  python -u aggregate_results.py --mode full --seed-index "$seed_index"
}

case "$MODE" in
  setup)
    if [[ ! -d "$VENV_DIR" ]]; then
      python3 -m venv "$VENV_DIR"
    fi
    # shellcheck disable=SC1090
    source "$VENV_DIR/bin/activate"
    python -m pip install --upgrade pip wheel
    python -m pip install -r requirements.txt
    echo "Environment ready: $VENV_DIR"
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
    SEED_INDEX="${3:-1}"
    run_one_fold smoke "$SEED_INDEX" 1 "$DEVICE"
    ;;
  fold)
    activate_python
    FOLD_ID="${2:?Usage: ./run.sh fold FOLD_ID [auto|cuda|mps|cpu] [SEED_INDEX]}"
    DEVICE="${3:-auto}"
    SEED_INDEX="${4:-1}"
    ensure_full_data
    run_one_fold full "$SEED_INDEX" "$FOLD_ID" "$DEVICE"
    ;;
  seed)
    activate_python
    SEED_INDEX="${2:?Usage: ./run.sh seed SEED_INDEX [auto|cuda|mps|cpu]}"
    DEVICE="${3:-auto}"
    python -u validate_setup.py
    ensure_full_data
    run_seed "$SEED_INDEX" "$DEVICE"
    ;;
  full)
    activate_python
    DEVICE="${2:-auto}"
    python -u validate_setup.py
    prepare_data full
    NUMBER_OF_SEEDS="$(seed_count)"
    for seed_index in $(seq 1 "$NUMBER_OF_SEEDS"); do
      run_seed "$seed_index" "$DEVICE"
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
  status)
    activate_python
    python - <<'PY'
import json
from pathlib import Path
seeds = json.load(open("experiment.json", encoding="utf-8"))["optimization_seeds"]
complete = 0
for index, seed in enumerate(seeds, 1):
    label = f"seed_{index:02d}_{int(seed)}"
    folds = []
    for fold in range(1, 6):
        done = Path(f"results/full/{label}/fold_{fold:02d}/summary.json").is_file()
        folds.append("done" if done else "pending")
        complete += int(done)
    print(f"{label}: " + ", ".join(f"fold {i} {state}" for i, state in enumerate(folds, 1)))
print(f"Completed fold models: {complete}/25")
PY
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
