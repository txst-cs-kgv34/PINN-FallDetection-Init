#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
ROOT_NAME="$(basename "${ROOT_DIR}")"
SUBJECT_ID="${ROOT_NAME%%_*}"
ARCHIVE="${ROOT_DIR}/${SUBJECT_ID}_Stage3_Gain_Sweep_Results.zip"

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
  "experiments/stage3_gain_sweep/results" \
  "experiments/stage3_gain_sweep/README.md" \
  "FINDINGS.md" \
  -x '*/.DS_Store' '*/__MACOSX/*'

echo "Created ${ARCHIVE}"
