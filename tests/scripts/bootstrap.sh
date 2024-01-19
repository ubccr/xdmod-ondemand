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

sudo -u xdmod xdmod-ondemand-ingestor -d $LOGPATH -r styx --debug
