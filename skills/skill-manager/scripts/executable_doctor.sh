#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="${SCRIPT_PATH%/*}"
if [[ "${SCRIPT_DIR}" == "${SCRIPT_PATH}" ]]; then
  SCRIPT_DIR="."
fi
SCRIPT_DIR="$(cd "${SCRIPT_DIR}" && pwd)"
LIB_SCRIPT="${SCRIPT_DIR}/lib/doctor_data.py"

GIT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"

# lib/common.py imports tomllib, so doctor needs Python 3.11+. Non-interactive
# shells on macOS often resolve python3 to /usr/bin/python3 (3.9), so pick the
# first 3.11+ interpreter on PATH in this order.
PYTHON=""
for candidate in python3 python3.14 python3.13 python3.12 python3.11; do
  if command -v "${candidate}" >/dev/null 2>&1 \
    && "${candidate}" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
    PYTHON="$(command -v "${candidate}")"
    break
  fi
done

if [[ -z "${PYTHON}" ]]; then
  printf '%s\n' '{"summary":{"pass":0,"warn":0,"fail":1},"checks":{},"errors":[{"code":"NO_PYTHON3","path":"","reason":"python3 >= 3.11 (tomllib) not found in PATH; tried python3, python3.14, python3.13, python3.12, python3.11"}],"project_root":null}'
  exit 0
fi
printf 'doctor: using %s\n' "${PYTHON}" >&2

exec "${PYTHON}" "${LIB_SCRIPT}" \
  --git-root="${GIT_ROOT}"
