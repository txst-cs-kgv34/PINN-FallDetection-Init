#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

command_name="${1:-help}"
if [[ $# -gt 0 ]]; then
  shift
fi

case "${command_name}" in
  test)
    python3 -m unittest discover -s tests -v
    python3 -m compileall -q .
    ;;
  prepare)
    python3 prepare_detector_data.py "$@"
    ;;
  validate)
    python3 validate_dataset.py "$@"
    ;;
  analyze)
    python3 analyze_prepared_data.py "$@"
    ;;
  package)
    python3 package_results.py
    ;;
  help|-h|--help)
    echo "Usage: ./run.sh {test|prepare|validate|analyze|package} [arguments]"
    ;;
  *)
    echo "Unknown command: ${command_name}" >&2
    exit 2
    ;;
esac
