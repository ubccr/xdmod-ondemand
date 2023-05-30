#!/bin/bash

set -a
ACCESS_OOD_TOKEN=
set +a

ENV_DIR="${HOME}/post_ood_logs_to_access_mms/env"
PYTHON="${ENV_DIR}/bin/python3"
PACKAGE_DIR="${ENV_DIR}/lib/python3.6/site-packages/post_ood_logs_to_access_mms"

${PYTHON} ${PACKAGE_DIR}/post_ood_logs_to_access_mms.py "$@"
