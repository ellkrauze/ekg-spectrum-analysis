#!/bin/bash

set -euox pipefail

cd "$(dirname "$0")/.."

FORMAT_OPTS="${FORMAT_OPTS:-""}"  # Set --check to just verify files

# docformatter takes its mode as a flag of its own, so FORMAT_OPTS has to be
# mirrored into it explicitly. Otherwise --check still rewrites every file.
# docformatter exits 3 per file it touches: in --check mode that means "would
# rewrite" and must fail the run, in --in-place mode it just did the rewrite.
if [ "${FORMAT_OPTS}" = "--check" ]; then
    DOC_MODE="--check"
    DOC_REWRITE_IS_OK=0
    # Return a non-zero exit code if any files were changed,
    # Implies --dry-run
    NBSTRIPMODE="--verify"
else
    DOC_MODE="--in-place"
    DOC_REWRITE_IS_OK=1
    NBSTRIPMODE=""
fi
DOC_FORMAT_OPTS="${DOC_FORMAT_OPTS:-"${DOC_MODE} --recursive --config $(pwd)/pyproject.toml"}"

PINS="$(grep -E '^(black|isort|docformatter|nbqa|nbstripout)==' requirements.dev.txt)"
CI_PYTHON_VERSION="3.12"

has_pinned_tools() {
    local pin
    for pin in ${PINS}; do
        [ "$("$1" -c "import importlib.metadata as m; print(m.version('${pin%%==*}'))" 2>/dev/null)" \
            = "${pin#*==}" ] || return 1
    done
}

PYTHON="${PYTHON:-.venv/bin/python3}"
if ! has_pinned_tools "${PYTHON}"; then
    if ! command -v uv >/dev/null; then
        echo "need ${PINS//$'\n'/ } under ${PYTHON}, or uv to set them up"
        exit 1
    fi
    # Throwaway: uv's wheel cache makes a rebuild take seconds.
    VENV="$(mktemp -d)"
    trap 'rm -rf -- "${VENV}"' EXIT
    uv venv --quiet --python "${CI_PYTHON_VERSION}" "${VENV}"
    uv pip install --quiet --python "${VENV}/bin/python" ${PINS}
    PYTHON="${VENV}/bin/python"
fi

BLACK="${PYTHON} -m black"
ISORT="${PYTHON} -m isort"
DOCFORMATTER="${PYTHON} -m docformatter"
NBQA="${PYTHON} -m nbqa"
NBSTRIPOUT="${PYTHON} -m nbstripout"

if ! ${BLACK} --version >/dev/null 2>&1; then
    echo "black is not found, please check it is installed"
    exit 1
fi
if ! ${ISORT} --version >/dev/null 2>&1; then
    echo "isort is not found, please check it is installed"
    exit 1
fi
if ! ${DOCFORMATTER} --version >/dev/null 2>&1; then
    echo "docformatter is not found, please check it is installed"
    exit 1
fi
if ! ${NBQA} --version >/dev/null 2>&1; then
    echo "nbqa is not found, please check it is installed"
    exit 1
fi
if ! ${NBSTRIPOUT} --version >/dev/null 2>&1; then
    echo "nbstripout is not found, please check it is installed"
    exit 1
fi

# Format each jupyter notebook individually to avoid tool confusion
for base_path in \
    "notebooks/" \
    ; do
    ${NBQA} black ${FORMAT_OPTS} -- "${base_path}"
    ${NBQA} isort ${FORMAT_OPTS} -- "${base_path}"
    find "${base_path}" -name '*.ipynb' -exec ${NBSTRIPOUT} ${NBSTRIPMODE} {} +
done

# Format *.py files
for base_path in \
    "src/ekg/" \
    "scripts/" \
    "tests/" \
    ; do
    ${BLACK} ${FORMAT_OPTS} -- "${base_path}"
    ${ISORT} ${FORMAT_OPTS} -- "${base_path}"
    if [ "${DOC_REWRITE_IS_OK}" -eq 1 ]; then
        ${DOCFORMATTER} ${DOC_FORMAT_OPTS} -- "$base_path" || [ $? -eq 3 ]
    else
        ${DOCFORMATTER} ${DOC_FORMAT_OPTS} -- "$base_path"
    fi

done

