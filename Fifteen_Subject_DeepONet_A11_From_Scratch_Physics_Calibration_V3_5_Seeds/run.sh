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

candidate_weights() {
  python - <<'PY'
import json
config = json.load(open("experiment.json"))
for value in [config["calibration"]["baseline_weight"], *config["calibration"]["candidate_weights"]]:
    print(value)
PY
}

weight_label() {
  python - "$1" <<'PY'
import sys
value = float(sys.argv[1])
print("lambda_0" if value == 0.0 else "lambda_" + f"{value:.0e}".replace("+", "").replace("e-0", "e-"))
PY
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

run_candidate() {
  local data_mode="$1" seed_index="$2" fold_id="$3" weight="$4" device="$5"
  local seed tag selection checkpoint
  seed="$(seed_label "$seed_index")"
  tag="$(weight_label "$weight")"
  selection="results/candidates/${data_mode}/${tag}/${seed}/fold_$(printf '%02d' "$fold_id")/training_selection.json"
  checkpoint="results/candidates/${data_mode}/${tag}/${seed}/fold_$(printf '%02d' "$fold_id")/final_best_model_state.pt"
  if [[ -f "$selection" && -f "$checkpoint" && "${FORCE:-0}" != "1" ]]; then
    echo "Skipping completed ${tag} ${seed} fold ${fold_id}"
    return
  fi
  mkdir -p results/logs
  python -u train_candidate.py \
    --mode "$data_mode" \
    --seed-index "$seed_index" \
    --fold "$fold_id" \
    --target-weight "$weight" \
    --device "$device" \
    2>&1 | tee "results/logs/${tag}_${data_mode}_${seed}_fold_${fold_id}.log"
}

select_fold() {
  local data_mode="$1" seed_index="$2" fold_id="$3" device="$4"
  local seed summary baseline_summary
  seed="$(seed_label "$seed_index")"
  summary="results/selected/${data_mode}/${seed}/fold_$(printf '%02d' "$fold_id")/summary.json"
  baseline_summary="results/matched_no_physics/${data_mode}/${seed}/fold_$(printf '%02d' "$fold_id")/summary.json"
  if [[ -f "$summary" && -f "$baseline_summary" && "${FORCE:-0}" != "1" ]]; then
    echo "Skipping completed selection ${seed} fold ${fold_id}"
    return
  fi
  python -u select_fold.py \
    --mode "$data_mode" \
    --seed-index "$seed_index" \
    --fold "$fold_id" \
    --device "$device" \
    2>&1 | tee "results/logs/select_${data_mode}_${seed}_fold_${fold_id}.log"
}

run_fold() {
  local data_mode="$1" seed_index="$2" fold_id="$3" device="$4"
  while IFS= read -r weight; do
    run_candidate "$data_mode" "$seed_index" "$fold_id" "$weight" "$device"
  done < <(candidate_weights)
  select_fold "$data_mode" "$seed_index" "$fold_id" "$device"
}

run_seed() {
  local seed_index="$1" device="$2"
  for fold in 1 2 3 4 5; do
    run_fold full "$seed_index" "$fold" "$device"
  done
  python -u aggregate_calibration.py --seed-index "$seed_index"
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
    run_fold smoke 1 1 "$DEVICE"
    ;;
  fold)
    activate_python
    FOLD="${2:?fold}"
    DEVICE="${3:-auto}"
    SEED="${4:-1}"
    ensure_data
    run_fold full "$SEED" "$FOLD" "$DEVICE"
    ;;
  seed)
    activate_python
    SEED="${2:?seed index}"
    DEVICE="${3:-auto}"
    ensure_data
    run_seed "$SEED" "$DEVICE"
    ;;
  pilot)
    activate_python
    python -u validate_setup.py
    ensure_data
    DEVICE="${2:-auto}"
    run_seed 1 "$DEVICE"
    python -u compare_calibration.py --seed-index 1
    python -u package_results.py --pilot-seed 1
    ;;
  full)
    activate_python
    python -u validate_setup.py
    ensure_data
    DEVICE="${2:-auto}"
    for seed in $(seq 1 "$(seed_count)"); do
      run_seed "$seed" "$DEVICE"
    done
    python -u aggregate_calibration.py
    python -u compare_calibration.py
    python -u package_results.py
    ;;
  aggregate)
    activate_python
    python -u aggregate_calibration.py
    ;;
  compare)
    activate_python
    python -u compare_calibration.py
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
config = json.load(open("experiment.json"))
weights = [config["calibration"]["baseline_weight"], *config["calibration"]["candidate_weights"]]
seeds = config["optimization_seeds"]
candidate_done = 0
selected_done = 0
for index, seed in enumerate(seeds, 1):
    seed_label = f"seed_{index:02d}_{seed}"
    states = []
    for fold in range(1, 6):
        complete = 0
        for weight in weights:
            tag = "lambda_0" if weight == 0.0 else "lambda_" + f"{weight:.0e}".replace("+", "").replace("e-0", "e-")
            complete += int(Path(f"results/candidates/full/{tag}/{seed_label}/fold_{fold:02d}/training_selection.json").is_file())
        selected = Path(f"results/selected/full/{seed_label}/fold_{fold:02d}/summary.json").is_file()
        baseline = Path(f"results/matched_no_physics/full/{seed_label}/fold_{fold:02d}/summary.json").is_file()
        candidate_done += complete
        selected_done += int(selected)
        states.append(f"fold {fold}: candidates {complete}/{len(weights)}, selected {'done' if selected else 'pending'}, matched λ=0 {'done' if baseline else 'pending'}")
    print(seed_label + "\n  " + "\n  ".join(states))
print(f"Completed from-scratch candidate models: {candidate_done}/{len(weights)*len(seeds)*5}")
print(f"Completed validation-selected models: {selected_done}/{len(seeds)*5}")
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
    echo "  ./run.sh fold FOLD [device] [seed-index]"
    echo "  ./run.sh seed SEED [device]"
    echo "  ./run.sh pilot [device]        # seed 1, all folds, then comparison"
    echo "  ./run.sh full [device]         # all five seeds"
    echo "  ./run.sh aggregate|compare|package|status|test"
    ;;
esac
