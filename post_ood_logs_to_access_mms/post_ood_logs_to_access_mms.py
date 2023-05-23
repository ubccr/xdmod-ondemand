#!/usr/bin/env python3

# Find Open OnDemand logs, parse them, and send them via POST request to the
# endpoint run by the ACCESS Monitoring and Measurement (ACCESS MMS) team who
# will ingest and aggregate the data to be included in ACCESS XDMoD.

# Import required libraries.
import apachelogs
import argparse
import configparser
from datetime import datetime, timezone
import glob
import logging
import operator
import os
import requests
import subprocess
import sys
import time

class LogPoster:
    def __init__(self):
        self.__access_mms_server_url = 'http://localhost:1234'
        self.__datetime_format = '%Y-%m-%d %H:%M:%S%z'
        self.__version = self.__read_version()
        self.__args = self.__parse_args()
        self.__logger = self.__init_logger()
        self.__logger.info('Script starting.')
        sys.excepthook = self.__excepthook
        self.__logger.debug('Using arguments: ' + str(self.__args))
        self.__logger = self.__init_logger()
        self.__conf_parser = self.__init_conf_parser()
        self.__parse_conf()
        self.__log_parser = self.__init_log_parser()
        self.__log_file_paths = self.__find_log_files()
        self.__previous_entry = self.__get_previous_entry()
        self.__last_timestamps = self.__filter_log_files()
        self.__sorted_log_file_paths = self.__sort_log_files()
        try:
            self.__parse_and_post()
        finally:
            self.__write_conf()
        self.__logger.info('Script finished.')


    def __read_version(self):
        with open('VERSION', 'r') as version_file:
            version = version_file.read()
        return version


    def __parse_args(self):
        arg_parser = argparse.ArgumentParser(
            description='Parse Open OnDemand logs and POST them to the ACCESS'
            + ' MMS team for inclusion in XDMoD.',
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
            help='path to the file containing the API token obtained from the'
            + ' ACCESS MMS team',
        )
        arg_parser.add_argument(
            '--version',
            action='version',
            version=self.__version,
        )
        args = arg_parser.parse_args()
        return args


    def __excepthook(self, exctype, value, traceback):
        if self.__args.log_level == 'DEBUG':
            sys.__excepthook__(exctype, value, traceback)
        else:
            self.__logger.error(value)


    def __init_logger(self):
        logging.basicConfig()
        logger = logging.getLogger(__file__)
        logger.setLevel(self.__args.log_level)
        return logger


    def __init_conf_parser(self):
        self.__logger.debug('Initializing configuration file parser.')
        conf_parser = configparser.ConfigParser(
            # Empty values are OK and will be handled by this script.
            allow_no_value=True,
            # Make sure not to try to interpolate % signs in the log format.
            interpolation=None,
        )
        return conf_parser


    def __parse_conf(self):
        self.__logger.debug("Parsing this script's configuration file.")
        parsed_filenames = self.__conf_parser.read(self.__args.conf_path)
        if not parsed_filenames:
            raise FileNotFoundError(self.__args.conf_path + ' not found.')


    def __init_log_parser(self):
        self.__logger.debug('Initializing the log parser.')
        log_parser = apachelogs.LogParser(
            self.__get_conf_property('logs', 'format')
        )
        return log_parser


    def __get_conf_property(self, section, key):
        self.__logger.debug(
            'Getting `' + key + '` property from the [' + section
            + '] section of the configuration file:'
        )
        value = self.__conf_parser.get(section, key)
        self.__logger.debug(value)
        return value


    def __find_log_files(self):
        self.__logger.debug('Finding the log files.')
        log_file_paths = glob.glob(
            self.__get_conf_property('logs', 'dir')
            + '/'
            + self.__get_conf_property('logs', 'filename_pattern')
        )
        self.__logger.debug('Found log files:')
        self.__logger.debug(log_file_paths)
        return log_file_paths


    def __get_previous_entry(self):
        previous_entry_str = self.__get_conf_property('runs', 'previous_entry')
        if previous_entry_str == '':
            previous_entry = self.__str_to_datetime('1970-01-01 00:00:00+0000')
            self.__logger.debug(
                'previous_entry is empty, setting to '
                + self.__datetime_to_str(previous_entry)
            )
        else:
            previous_entry = self.__str_to_datetime(previous_entry_str)
        return previous_entry


    def __str_to_datetime(self, string):
        dt = datetime.strptime(string, self.__datetime_format)
        return dt


    def __datetime_to_str(self, dt):
        string = datetime.strftime(dt, self.__datetime_format)
        return string


    def __filter_log_files(self):
        self.__logger.debug(
            'Parsing last timestamps in files and excluding old files.'
        )
        last_timestamps = {}
        for log_file_path in self.__log_file_paths:
            last_line = self.__get_last_line_in_file(log_file_path)
            try:
                entry = self.__log_parser.parse(last_line)
                last_timestamps[log_file_path] = entry.request_time
                self.__logger.debug(
                    'Last timestamp of ' + log_file_path + ' is '
                    + self.__datetime_to_str(last_timestamps[log_file_path])
                )
                if last_timestamps[log_file_path] <= self.__previous_entry:
                    self.__logger.debug(
                        'which is not after previous_entry,'
                        + ' so will not be parsing it.'
                    )
                    del last_timestamps[log_file_path]
            except apachelogs.errors.InvalidEntryError:
                self.__logger.warn('Skipping invalid file: ' + log_file_path)
        return last_timestamps


    def __get_last_line_in_file(self, file_path):
        with open(file_path, 'rb') as file:
            try:
                # Move to the second-to-last character in the file.
                file.seek(-2, os.SEEK_END)
                # Read the character, which seeks forward one character.
                char = file.read(1)
                # Until the character is a newline,
                while char != b'\n':
                    # Seek back two characters.
                    file.seek(-2, os.SEEK_CUR)
                    # Read the character, which seeks forward one character.
                    char = file.read(1)
            # An error will occur if the file is fewer than two lines long, in
            # which case,
            except OSError:
                # Seek to the beginning of the file.
                file.seek(0)
            # Read the current line.
            last_line = file.readline().decode('utf-8')
        return last_line


    def __sort_log_files(self):
        self.__logger.debug('Sorting list of log files:')
        sorted_last_timestamps = sorted(
            self.__last_timestamps.items(),
            key=operator.itemgetter(1),
        )
        sorted_log_file_paths = [i[0] for i in sorted_last_timestamps]
        self.__logger.debug(sorted_log_file_paths)
        return sorted_log_file_paths


    def __parse_and_post(self):
        self.__logger.debug('Starting parsing and POSTing of log files.')
        for log_file_path in self.__sorted_log_file_paths:
            self.__logger.info('Parsing and posting ' + log_file_path)
            response = requests.post(
                self.__access_mms_server_url,
                data=self.__parse_log_file(log_file_path),
            )
            self.__conf_parser.set(
                'runs',
                'previous_entry',
                self.__datetime_to_str(self.__last_timestamps[log_file_path]),
            )


    def __parse_log_file(self, log_file_path):
        with open(log_file_path, 'r') as log_file:
            line_num = 0
            for line in log_file:
                try:
                    entry = self.__log_parser.parse(line)
                    # Only include lines for which a user is logged in.
                    if entry.remote_user is not None:
                        # TODO: reformat into default LogFormat if needed.
                        yield line.encode()
                except apachelogs.errors.InvalidEntryError:
                    self.__logger.warn(
                        'Skipping invalid entry: ' + log_file_path
                        + ' line ' + line_num + ': ' + line
                    )
                line_num += 1


    def __write_conf(self):
        self.__logger.debug('Writing values back to configuration file.')
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
        with open(self.__args.conf_path, 'w') as conf_file:
            conf_file.write(comment_header)
            self.__conf_parser.write(conf_file)


if __name__ == '__main__':
    LogPoster()
