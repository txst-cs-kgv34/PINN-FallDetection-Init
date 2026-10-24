#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
ARCHIVE="${ROOT_DIR}/S63_Stage3_Gain_Sweep_Results.zip"

if [[ ! -f "${RESULTS_DIR}/summary.json" ]]; then
  echo "The aggregate summary is missing. Complete all eleven chunks first." >&2
  exit 1
fi

completed_count="$(find "${RESULTS_DIR}" -maxdepth 2 -name result.json -type f | wc -l | tr -d ' ')"
if [[ "${completed_count}" != "11" ]]; then
  echo "Expected 11 completed chunks, found ${completed_count}." >&2
  exit 1
fi

cd "${ROOT_DIR}"
if [[ -e "${ARCHIVE}" ]]; then
  echo "${ARCHIVE} already exists. Rename or move it, then rerun this command." >&2
  exit 1
fi
zip -r "${ARCHIVE}" \
  "experiments/stage3_gain_sweep/README.md" \
  "experiments/stage3_gain_sweep/FINDINGS.md" \
  "experiments/stage3_gain_sweep/check_setup.py" \
  "experiments/stage3_gain_sweep/run_gain_sweep.py" \
  "experiments/stage3_gain_sweep/run_on_mac.sh" \
  "experiments/stage3_gain_sweep/package_results.sh" \
  "experiments/stage3_gain_sweep/results" \
  -x '*/.DS_Store' '*/__MACOSX/*'

echo "Created ${ARCHIVE}"
