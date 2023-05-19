#!/usr/bin/env python3

# Find Open OnDemand logs, parse them, and send them via POST request to the
# endpoint run by the ACCESS Monitoring and Measurement (ACCESS MMS) team who
# will ingest and aggregate the data to be included in ACCESS XDMoD.

# Import required libraries.
import argparse
import configparser
import glob
import logging
import os
import subprocess
import time

# Read version number from file.
with open('VERSION', 'r') as version_file:
    version = version_file.read()

# Parse arguments.
parser = argparse.ArgumentParser(
    description='Parse Open OnDemand logs and POST them to the ACCESS MMS team'
    + ' for inclusion in XDMoD.',
    allow_abbrev=False,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    '-c',
    '--conf-path',
    default='conf.ini',
    help='path to the configuration file that declares where to'
    + ' find log files and how to parse them',
)
parser.add_argument(
    '-l',
    '--log-level',
    choices=('DEBUG', 'WARNING', 'ERROR'),
    default='WARN',
)
parser.add_argument(
    '-t',
    '--token-path',
    default='/root/.access_mms_ood_token',
    help='path to the file containing the API token obtained from the ACCESS'
    + ' MMS team',
)
parser.add_argument(
    '--version',
    action='version',
    version=version,
)
args = parser.parse_args()

# Initialize the logger.
logging.basicConfig()
logger = logging.getLogger(__file__)
logger.setLevel(args.log_level)

logger.debug('Using arguments:' + str(args))

logger.debug('Initializing configuration file parser.')
conf = configparser.ConfigParser(
    # Empty values are OK and will be handled by this script.
    allow_no_value=True,
    # Make sure not to try to interpolate % signs in the log format.
    interpolation=None,
)

logger.debug("Parsing this script's configuration file.")
parsed_filenames = conf.read(args.conf_path)
if not parsed_filenames:
    raise FileNotFoundError(args.conf_path + ' not found.')

# Define a function to get a property from the configuration file.
def __get_conf_property(conf, section, key):
    logger.debug(
        'Getting ' + key + ' property from the [' + section
        + '] section of the configuration file:'
    )
    value = conf.get(section, key)
    logger.debug(value)
    return value

log_dir = __get_conf_property(conf, 'logs', 'dir')
log_format = __get_conf_property(conf, 'logs', 'format')
filename_pattern = __get_conf_property(conf, 'logs', 'filename_pattern')
last_run = __get_conf_property(conf, 'runs', 'last_run')

logger.debug('Recording current time just before processing logs:')
current_time = time.time()
logger.debug(current_time)

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
with open(args.conf_path, 'w') as conf_file:
    conf_file.write(comment_header)
with open(args.conf_path, 'a') as conf_file:
    conf.write(conf_file)
