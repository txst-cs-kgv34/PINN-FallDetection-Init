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
  all)
    output_dir="${ROOT_DIR}/outputs"
    all_args=("$@")
    for ((index=0; index<${#all_args[@]}; index++)); do
      if [[ "${all_args[index]}" == "--output-dir" && $((index + 1)) -lt ${#all_args[@]} ]]; then
        output_dir="${all_args[index + 1]}"
      elif [[ "${all_args[index]}" == --output-dir=* ]]; then
        output_dir="${all_args[index]#--output-dir=}"
      fi
    done
    python3 prepare_detector_data.py "$@"
    python3 validate_dataset.py --output-dir "${output_dir}"
    python3 analyze_prepared_data.py --output-dir "${output_dir}"
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
    echo "Usage: ./run.sh {test|prepare|all|validate|analyze|package} [arguments]"
    ;;
  *)
    echo "Unknown command: ${command_name}" >&2
    exit 2
    ;;
esac
