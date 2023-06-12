#!/bin/bash

set -a
XDMOD_ONDEMAND_EXPORT_TOKEN=
set +a

ENV_DIR="${HOME}/xdmod-ondemand-export/env"
PYTHON="${ENV_DIR}/bin/python3"
PACKAGE_DIR="${ENV_DIR}/lib/python3.*/site-packages/xdmod_ondemand_export"

${PYTHON} ${PACKAGE_DIR}/xdmod_ondemand_export.py "$@" --bash-script "$0"
