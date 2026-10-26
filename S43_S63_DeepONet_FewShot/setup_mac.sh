#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${script_dir}"

python_command="python3"
if command -v python3.11 >/dev/null 2>&1; then
  python_command="python3.11"
fi

"${python_command}" -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt

echo "Environment ready. Activate it with:"
echo "source ${script_dir}/.venv/bin/activate"
