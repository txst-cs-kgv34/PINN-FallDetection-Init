#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${script_dir}"

if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

python validate_setup.py
python export_teacher_data.py --mode full --overwrite
python train_operator.py --mode full --device auto
python package_results.py

echo "Full pooled experiment complete."
echo "Send S43_S63_DeepONet_FewShot_Results.zip back for analysis."
