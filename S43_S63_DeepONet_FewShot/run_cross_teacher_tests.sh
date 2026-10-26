#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${script_dir}"

if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

for teacher in s43_chunk1 s63_chunk1 s63_chunk6; do
  python train_operator.py --mode full --device auto --holdout-teacher "${teacher}"
done

python package_results.py
echo "All three leave-one-teacher-out tests complete."
