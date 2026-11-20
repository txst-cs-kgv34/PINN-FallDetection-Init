#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
MODE="${1:-help}"
VENV_DIR="${PINN_VENV_DIR:-$HOME/.venv}"
export PYTHONUNBUFFERED=1
export PYTORCH_ENABLE_MPS_FALLBACK=1

activate_python() {
  if [[ -f "$VENV_DIR/bin/activate" ]]; then source "$VENV_DIR/bin/activate"
  elif [[ -f .venv/bin/activate ]]; then source .venv/bin/activate
  else echo "Python environment not found. Run ./run.sh setup first." >&2; exit 1; fi
}
seed_count() { python -c 'import json; print(len(json.load(open("experiment.json"))["optimization_seeds"]))'; }
seed_label() { python - "$1" <<'PY'
import json,sys
seeds=json.load(open("experiment.json"))["optimization_seeds"]; i=int(sys.argv[1])
if not 1 <= i <= len(seeds): raise SystemExit("invalid seed index")
print(f"seed_{i:02d}_{int(seeds[i-1])}")
PY
}
prepare_data() {
  local data_mode="${1:-full}"
  mkdir -p results/logs
  python -u prepare_data.py --mode "$data_mode" --overwrite 2>&1 | tee "results/logs/prepare_${data_mode}.log"
  python -u validate_prepared_data.py --mode "$data_mode" 2>&1 | tee "results/logs/validate_prepared_${data_mode}.log"
}
ensure_data() { [[ -f outputs/real_data_full/planar_manifest.json && -f outputs/real_data_full/rotation_manifest.json ]] || prepare_data full; }
run_fold() {
  local group="$1" data_mode="$2" seed_index="$3" fold_id="$4" device="$5" label summary
  label="$(seed_label "$seed_index")"
  summary="results/${group}/${data_mode}/${label}/fold_$(printf '%02d' "$fold_id")/summary.json"
  if [[ -f "$summary" && "${FORCE:-0}" != "1" ]]; then echo "Skipping completed $group $label fold $fold_id"; return; fi
  mkdir -p results/logs
  python -u train_fold.py --mode "$data_mode" --model-group "$group" --seed-index "$seed_index" --fold "$fold_id" --device "$device" 2>&1 | tee "results/logs/${group}_${data_mode}_${label}_fold_${fold_id}.log"
}
run_seed() {
  local group="$1" seed_index="$2" device="$3"
  for fold in 1 2 3 4 5; do run_fold "$group" full "$seed_index" "$fold" "$device"; done
  python -u aggregate_results.py --mode full --model-group "$group" --seed-index "$seed_index"
}
run_group() {
  local group="$1" device="$2"
  for seed in $(seq 1 "$(seed_count)"); do run_seed "$group" "$seed" "$device"; done
  python -u aggregate_results.py --mode full --model-group "$group"
}

case "$MODE" in
  setup)
    [[ -d "$VENV_DIR" ]] || python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"; python -m pip install --upgrade pip wheel; python -m pip install -r requirements.txt
    ;;
  validate) activate_python; python -u validate_setup.py ;;
  prepare) activate_python; prepare_data full ;;
  smoke)
    activate_python; python -u validate_setup.py; prepare_data smoke; DEVICE="${2:-auto}"
    run_fold planar smoke 1 1 "$DEVICE"; run_fold rotation smoke 1 1 "$DEVICE"
    ;;
  fold)
    activate_python; GROUP="${2:?planar|rotation}"; FOLD="${3:?fold}"; DEVICE="${4:-auto}"; SEED="${5:-1}"; ensure_data; run_fold "$GROUP" full "$SEED" "$FOLD" "$DEVICE"
    ;;
  seed)
    activate_python; GROUP="${2:?planar|rotation}"; SEED="${3:?seed index}"; DEVICE="${4:-auto}"; ensure_data; run_seed "$GROUP" "$SEED" "$DEVICE"
    ;;
  planar|rotation)
    activate_python; python -u validate_setup.py; ensure_data; run_group "$MODE" "${2:-auto}"
    ;;
  full)
    activate_python; python -u validate_setup.py; prepare_data full; DEVICE="${2:-auto}"; run_group planar "$DEVICE"; run_group rotation "$DEVICE"; python -u package_results.py
    ;;
  aggregate) activate_python; python -u aggregate_results.py --mode full --model-group all ;;
  package) activate_python; python -u package_results.py ;;
  status)
    activate_python; python - <<'PY'
import json
from pathlib import Path
seeds=json.load(open("experiment.json"))["optimization_seeds"]
done=0
for group in ("planar","rotation"):
 print(group.upper())
 for i,seed in enumerate(seeds,1):
  label=f"seed_{i:02d}_{seed}"; states=[]
  for fold in range(1,6):
   ok=Path(f"results/{group}/full/{label}/fold_{fold:02d}/summary.json").is_file(); done+=int(ok); states.append("done" if ok else "pending")
  print(label+": "+", ".join(f"fold {j} {state}" for j,state in enumerate(states,1)))
print(f"Completed models: {done}/50")
PY
    ;;
  test) activate_python; python -m unittest discover -s tests -v; python -m compileall -q . ;;
  help|*)
    echo "Usage:"
    echo "  ./run.sh setup|validate|prepare|smoke [device]"
    echo "  ./run.sh fold planar|rotation FOLD [device] [seed-index]"
    echo "  ./run.sh seed planar|rotation SEED [device]"
    echo "  ./run.sh planar|rotation [device]"
    echo "  ./run.sh full [device]"
    echo "  ./run.sh aggregate|package|status|test"
    ;;
esac
