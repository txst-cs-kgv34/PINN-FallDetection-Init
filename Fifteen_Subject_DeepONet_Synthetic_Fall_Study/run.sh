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
    ;;
  smoke)
    python3 smoke_test.py
    ;;
  validate)
    python3 select_generators.py "$@"
    ;;
  select)
    python3 select_generators.py --copy-checkpoints --overwrite "$@"
    ;;
  help|-h|--help)
    echo "Usage: ./run.sh {test|smoke|validate|select} [selector arguments]"
    echo
    echo "  test      Run fixture-based unit tests."
    echo "  smoke     Run a dependency-free 5-fold x 5-seed smoke test."
    echo "  validate  Validate/rank the real runs and write tables only."
    echo "  select    Rank and copy the top two checkpoints per fold."
    ;;
  *)
    echo "Unknown command: ${command_name}" >&2
    exit 2
    ;;
esac
