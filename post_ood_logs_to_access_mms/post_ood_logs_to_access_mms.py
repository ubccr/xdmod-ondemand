#!/usr/bin/env python3

# Find Open OnDemand logs, parse them, and send them via POST request to the
# endpoint run by the ACCESS Monitoring and Measurement (ACCESS MMS) team who
# will ingest and aggregate the data to be included in ACCESS XDMoD.

# Import required libraries.
from apachelogs import LogParser
import argparse
import configparser
from datetime import datetime, timezone
import glob
import logging
import os
import subprocess
import time

# Read version number from file.
with open('VERSION', 'r') as version_file:
    version = version_file.read()

# Parse arguments.
arg_parser = argparse.ArgumentParser(
    description='Parse Open OnDemand logs and POST them to the ACCESS MMS team'
    + ' for inclusion in XDMoD.',
    allow_abbrev=False,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
arg_parser.add_argument(
    '-c',
    '--conf-path',
    default='conf.ini',
    help='path to the configuration file that declares where to'
    + ' find log files and how to parse them',
)
arg_parser.add_argument(
    '-l',
    '--log-level',
    choices=('DEBUG', 'INFO', 'WARNING', 'ERROR'),
    default='WARNING',
)
arg_parser.add_argument(
    '-t',
    '--token-path',
    default='/root/.access_mms_ood_token',
    help='path to the file containing the API token obtained from the ACCESS'
    + ' MMS team',
)
arg_parser.add_argument(
    '--version',
    action='version',
    version=version,
)
args = arg_parser.parse_args()

# Set datetime format.
datetime_format = '%Y-%m-%d %H:%M:%S%Z'

# Initialize the logger.
logging.basicConfig()
logger = logging.getLogger(__file__)
logger.setLevel(args.log_level)

logger.info('Script starting.')
logger.debug('Using arguments: ' + str(args))

logger.debug('Initializing configuration file parser.')
conf_parser = configparser.ConfigParser(
    # Empty values are OK and will be handled by this script.
    allow_no_value=True,
    # Make sure not to try to interpolate % signs in the log format.
    interpolation=None,
)

logger.debug("Parsing this script's configuration file.")
parsed_filenames = conf_parser.read(args.conf_path)
if not parsed_filenames:
    raise FileNotFoundError(args.conf_path + ' not found.')

# Define a function to get a property from the configuration file.
def __get_conf_property(conf_parser, section, key):
    logger.debug(
        'Getting ' + key + ' property from the [' + section
        + '] section of the configuration file:'
    )
    value = conf_parser.get(section, key)
    logger.debug(value)
    return value

# Get the properties from the configuration file.
log_dir = __get_conf_property(conf_parser, 'logs', 'dir')
log_format = __get_conf_property(conf_parser, 'logs', 'format')
filename_pattern = __get_conf_property(conf_parser, 'logs', 'filename_pattern')
before_time = __get_conf_property(conf_parser, 'runs', 'before_time')

if before_time == '':
    before_time = datetime.fromtimestamp(0, tz=timezone.utc)
    logger.debug('before_time is empty, setting to ' + str(before_time))
else:
    before_time = datetime.strptime(before_time, datetime_format)

logger.debug('Constructing the log parser')
log_parser = LogParser(log_format)

logger.debug('Finding the log files:')
log_file_paths = glob.glob(log_dir + '/' + filename_pattern)
logger.debug(log_file_paths)

logger.debug('Parsing last timestamps in files and excluding old files.')
last_timestamps = {}
for log_file_path in log_file_paths:
    # Open the log file so the last timestamp can be read.
    with open(log_file_path, 'rb') as log_file:
        try:
            # Move to the second-to-last character in the file.
            log_file.seek(-2, os.SEEK_END)
            # Read the character, which seeks forward one character.
            char = log_file.read(1)
            # Until the character is a newline,
            while char != b'\n':
                # Seek back two characters.
                log_file.seek(-2, os.SEEK_CUR)
                # Read the character, which seeks forward one character.
                char = log_file.read(1)
        # An error will occur if the file is fewer than two lines long, in
        # which case,
        except OSError:
            # Seek to the beginning of the file.
            log_file.seek(0)
        # Read the current line.
        last_line = log_file.readline().decode('utf-8')
    # Parse the line.
    entry = log_parser.parse(last_line)
    # Store the timestamp.
    last_timestamps[log_file_path] = entry.request_time
    logger.debug(
        'Last timestamp of ' + log_file_path + ' is '
        + str(last_timestamps[log_file_path])
    )
    if last_timestamps[log_file_path] <= before_time:
        logger.debug(
            'which is not after before_time, so will not be parsing it.'
        )
        del last_timestamps[log_file_path]

logger.debug('Sorting list of log files:')
sorted_log_file_paths = sorted(last_timestamps)
logger.debug(sorted_log_file_paths)

logger.debug('Starting parsing of log files.')
for log_file_path in sorted_log_file_paths:
    logger.debug('Parsing ' + log_file_path)
    with open(log_file_path, 'r') as log_file:
        for line in log_file:
            pass

logger.debug('Writing values back to configuration file.')
#conf_parser.set('runs', 'last_run', str(current_time))
comment_header = """\
# This is a configuration file used by post_ood_logs_to_access_mms.py.
#
# Set the values in the [logs] section to tell the script where to find logs
# and how to parse them.
#
# The values in the [runs] section will be overwritten in-place in this file by
# the script when it runs. Log files will only be processed whose modified
# times are greater than the value for last_run.

"""
with open(args.conf_path, 'w') as conf_file:
    conf_file.write(comment_header)
with open(args.conf_path, 'a') as conf_file:
    conf_parser.write(conf_file)

logger.info('Script finished.')
