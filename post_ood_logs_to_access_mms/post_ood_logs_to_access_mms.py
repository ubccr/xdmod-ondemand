#!/usr/bin/env python3

# Find Open OnDemand logs, parse them, and send them via POST request to the
# endpoint run by the ACCESS Monitoring and Measurement (ACCESS MMS) team who
# will ingest and aggregate the data to be included in ACCESS XDMoD.

# Import required libraries.
import configparser
import subprocess

# If true, print debugging statements as the script runs.
DEBUG = True

# Name of the configuration file in which metadata about the logs and the runs
# of this script are read/written. Assumed to be in the same directory as this
# script.
CONF_FILENAME = 'conf.ini'

# Read this script's configuration file.
conf = configparser.ConfigParser(
    # Empty values are OK and will be handled by this script.
    allow_no_value=True,
    # Make sure not to try to interpolate % signs in the log format.
    interpolation=None,
)
parsed_filenames = conf.read(CONF_FILENAME)

# If the configuration file cannot be read, raise an exception.
if not parsed_filenames:
    raise FileNotFoundError(CONF_FILENAME + ' not found.')

# Read the [logs] properties from the configuration file.
log_dir = conf.get('logs', 'dir')
log_format = conf.get('logs', 'format')

# Read the [runs] properties from the configuration file.
last_run = conf.get('runs', 'last_run')

# Write the configuration values back to the configuration file.
comment_header = """\
# This is a configuration file used by post_ood_logs_to_access_mms.py.
#
# Set the values in the [logs] section to tell the script where to find logs
# and how to parse them.
#
# The values in the [runs] section will be overwritten in-place in this file by
# the script when it runs.
"""
with open(CONF_FILENAME, 'w') as conf_file:
    conf_file.write(comment_header)
with open(CONF_FILENAME, 'a') as conf_file:
    conf.write(conf_file)
