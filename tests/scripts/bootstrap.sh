#!/bin/bash
# Bootstrap XDMoD with the OnDemand module. This script calls the main XDMoD
# integration test bootstrap do configure & start the core.

BASEDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOGPATH=/tmp/ondemand

set -e
set -o pipefail

# Get a copy of the GeoIP data (this is not up to date hence we don't explictly
# add it as a dependency)
yum install -y GeoIP-data

# bootstrap XDMoD
$BASEDIR/../../../../xdmod/tests/ci/bootstrap.sh

# Run the interactive setup to add a new resource and setup the database.
expect $BASEDIR/setup.tcl | col -b

# run xdmod-ingestor to add the new resource to the datawarehouse.
sudo -u xdmod xdmod-ingestor

# Copy example log files into a temp directory and import
mkdir $LOGPATH
cp $BASEDIR/../artifacts/*.log $LOGPATH

sudo -u xdmod /usr/share/xdmod/tools/etl/etl_overseer.php \
    -p ondemand.log-ingestion \
    -p ondemand.aggregation \
    -d GEOIP_FILE_PATH=/usr/share/GeoIP/GeoIPCity-initial.dat \
    -d OOD_LOG_PATH=$LOGPATH \
    -d OOD_HOSTNAME=https://localhost:3443 \
    -d OOD_RESOURCE_CODE=styx \
    -v debug

