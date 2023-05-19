#!/usr/bin/env python3

# Find Open OnDemand logs, parse them, and send them via POST request to the
# endpoint run by the ACCESS Monitoring and Measurement (ACCESS MMS) team who
# will ingest and aggregate the data to be included in ACCESS XDMoD.

# Import required libraries.
import configparser
import glob
import os
import subprocess
import time

# If true, print debugging statements as the script runs.
DEBUG = True

# Name of the configuration file in which metadata about the logs and the runs
# of this script are read/written. Assumed to be in the same directory as this
# script.
CONF_FILENAME = 'conf.ini'

# Initialize a configuration file parser.
conf = configparser.ConfigParser(
    # Empty values are OK and will be handled by this script.
    allow_no_value=True,
    # Make sure not to try to interpolate % signs in the log format.
    interpolation=None,
)

# Parse this script's configuration file.
parsed_filenames = conf.read(CONF_FILENAME)

# If the configuration file cannot be read, raise an exception.
if not parsed_filenames:
    raise FileNotFoundError(CONF_FILENAME + ' not found.')

# Read the [logs] properties from the configuration file.
log_dir = conf.get('logs', 'dir')
log_format = conf.get('logs', 'format')
filename_pattern = conf.get('logs', 'filename_pattern')

# Read the [runs] properties from the configuration file.
last_run = conf.get('runs', 'last_run')

# Record the current time just before we start processing logs.
current_time = time.time()

# Find all the log files at the given directory whose name matches the given
# pattern.
log_files = glob.glob(log_dir + '/' + filename_pattern)

# For each file,
for log_file in log_files:

    # Get the last modified time.
    mtime = os.path.getmtime(log_file)

# Record the current time in the configuration file.
conf.set('runs', 'last_run', str(current_time))

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
