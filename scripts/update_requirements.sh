#!/bin/bash

set -euox pipefail

cd "$(dirname "$0")/.."

REQ_DIR="requirements"
PYPROJECT="pyproject.toml"

PYTHON="${PYTHON:-.venv/bin/python3}"
PIP_COMPILE="${PYTHON} -m piptools compile"

# generate project requirements from PYPROJECT
${PIP_COMPILE} -o "${REQ_DIR}/requirements.txt" "${PYPROJECT}"

# generate project (dev) requirements from PYPROJECT
${PIP_COMPILE} --extra=dev -o "${REQ_DIR}/requirements-dev.txt" "${PYPROJECT}"
