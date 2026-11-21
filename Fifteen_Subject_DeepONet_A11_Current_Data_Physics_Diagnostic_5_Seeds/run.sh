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
    source "$VENV_DIR/bin/activate"
  elif [[ -f .venv/bin/activate ]]; then
    source .venv/bin/activate
  else
    echo "Python environment not found. Run ./run.sh setup first." >&2
    exit 1
  fi
}

seed_count() {
  python -c 'import json; print(len(json.load(open("experiment.json"))["optimization_seeds"]))'
}

seed_label() {
  python - "$1" <<'PY'
import json, sys
seeds = json.load(open("experiment.json"))["optimization_seeds"]
index = int(sys.argv[1])
if not 1 <= index <= len(seeds):
    raise SystemExit("invalid seed index")
print(f"seed_{index:02d}_{int(seeds[index-1])}")
PY
}

validate_condition() {
  case "$1" in
    physics|no_physics) ;;
    *) echo "Condition must be physics or no_physics" >&2; exit 2 ;;
  esac
}

prepare_data() {
  local data_mode="${1:-full}"
  mkdir -p results/logs
  python -u prepare_data.py --mode "$data_mode" --overwrite 2>&1 | tee "results/logs/prepare_${data_mode}.log"
  python -u validate_prepared_data.py --mode "$data_mode" 2>&1 | tee "results/logs/validate_prepared_${data_mode}.log"
}

ensure_data() {
  [[ -f outputs/real_data_full/planar_manifest.json ]] || prepare_data full
}

run_fold() {
  local condition="$1" data_mode="$2" seed_index="$3" fold_id="$4" device="$5" label summary
  validate_condition "$condition"
  label="$(seed_label "$seed_index")"
  summary="results/${condition}/${data_mode}/${label}/fold_$(printf '%02d' "$fold_id")/summary.json"
  if [[ -f "$summary" && "${FORCE:-0}" != "1" ]]; then
    echo "Skipping completed ${condition} ${label} fold ${fold_id}"
    return
  fi
  mkdir -p results/logs
  python -u train_fold.py \
    --mode "$data_mode" \
    --model-group planar \
    --condition "$condition" \
    --seed-index "$seed_index" \
    --fold "$fold_id" \
    --device "$device" \
    2>&1 | tee "results/logs/${condition}_${data_mode}_${label}_fold_${fold_id}.log"
}

run_seed() {
  local condition="$1" seed_index="$2" device="$3"
  for fold in 1 2 3 4 5; do
    run_fold "$condition" full "$seed_index" "$fold" "$device"
  done
  python -u aggregate_results.py --mode full --condition "$condition" --seed-index "$seed_index"
}

run_condition() {
  local condition="$1" device="$2"
  for seed in $(seq 1 "$(seed_count)"); do
    run_seed "$condition" "$seed" "$device"
  done
  python -u aggregate_results.py --mode full --condition "$condition"
}

case "$MODE" in
  setup)
    [[ -d "$VENV_DIR" ]] || python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
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
    run_fold physics smoke 1 1 "$DEVICE"
    run_fold no_physics smoke 1 1 "$DEVICE"
    ;;
  fold)
    activate_python
    CONDITION="${2:?physics|no_physics}"
    FOLD="${3:?fold}"
    DEVICE="${4:-auto}"
    SEED="${5:-1}"
    ensure_data
    run_fold "$CONDITION" full "$SEED" "$FOLD" "$DEVICE"
    ;;
  seed)
    activate_python
    CONDITION="${2:?physics|no_physics}"
    SEED="${3:?seed index}"
    DEVICE="${4:-auto}"
    ensure_data
    run_seed "$CONDITION" "$SEED" "$DEVICE"
    ;;
  condition)
    activate_python
    CONDITION="${2:?physics|no_physics}"
    DEVICE="${3:-auto}"
    validate_condition "$CONDITION"
    python -u validate_setup.py
    ensure_data
    run_condition "$CONDITION" "$DEVICE"
    ;;
  full)
    activate_python
    python -u validate_setup.py
    prepare_data full
    DEVICE="${2:-auto}"
    run_condition physics "$DEVICE"
    run_condition no_physics "$DEVICE"
    python -u compare_results.py
    python -u package_results.py
    ;;
  aggregate)
    activate_python
    python -u aggregate_results.py --mode full --condition all
    ;;
  compare)
    activate_python
    python -u compare_results.py
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
seeds = json.load(open("experiment.json"))["optimization_seeds"]
done = 0
for condition in ("physics", "no_physics"):
    print(condition.upper())
    for index, seed in enumerate(seeds, 1):
        label = f"seed_{index:02d}_{seed}"
        states = []
        for fold in range(1, 6):
            complete = Path(f"results/{condition}/full/{label}/fold_{fold:02d}/summary.json").is_file()
            done += int(complete)
            states.append("done" if complete else "pending")
        print(label + ": " + ", ".join(f"fold {number} {state}" for number, state in enumerate(states, 1)))
print(f"Completed models: {done}/50")
PY
    ;;
  test)
    activate_python
    python -m unittest discover -s tests -v
    python -m compileall -q .
    ;;
  help|*)
    echo "Usage:"
    echo "  ./run.sh setup|validate|prepare|smoke [device]"
    echo "  ./run.sh fold physics|no_physics FOLD [device] [seed-index]"
    echo "  ./run.sh seed physics|no_physics SEED [device]"
    echo "  ./run.sh condition physics|no_physics [device]"
    echo "  ./run.sh full [device]"
    echo "  ./run.sh aggregate|compare|package|status|test"
    ;;
esac
