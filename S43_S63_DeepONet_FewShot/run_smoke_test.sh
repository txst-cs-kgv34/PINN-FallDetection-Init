#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${script_dir}"

if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

python validate_setup.py
python export_teacher_data.py --mode smoke --overwrite
python train_operator.py --mode smoke --device auto

echo "Smoke test complete. These outputs verify execution only and are not scientific results."
