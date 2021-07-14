#!/bin/bash
# Bootstrap XDMoD with the OnDemand module. This script calls the main XDMoD
# integration test bootstrap do configure & start the core.

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOGPATH=/tmp/ondemand
XDMOD_SRC_DIR=${XDMOD_SRC_DIR:-$BASEDIR/../../../xdmod}

set -e
set -o pipefail

# bootstrap XDMoD
$XDMOD_SRC_DIR/tests/ci/bootstrap.sh

# Run the interactive setup to add a new resource and setup the database.
expect $BASEDIR/setup.tcl | col -b

# run xdmod-ingestor to add the new resource to the datawarehouse.
sudo -u xdmod xdmod-ingestor

# Copy example log files into a temp directory since the
# import process runs as xdmod user and needs read access.
mkdir $LOGPATH
cp $BASEDIR/../artifacts/*.log $LOGPATH
cp $BASEDIR/../artifacts/empty.mmdb /tmp

sudo -u xdmod /usr/share/xdmod/tools/etl/etl_overseer.php \
    -p ondemand.log-ingestion \
    -p ondemand.aggregation \
    -d GEOIP_FILE_PATH=/tmp/empty.mmdb \
    -d OOD_LOG_PATH=$LOGPATH \
    -d OOD_HOSTNAME=https://localhost:3443 \
    -d OOD_RESOURCE_CODE=styx \
    -v debug

