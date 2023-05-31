#!/usr/bin/env python3

from __version__ import __title__, __version__
import apachelogs
import argparse
import configparser
from datetime import datetime, timezone
import glob
import gzip
import logging
import operator
import os
import re
import requests
import sys

class LogPoster:
    def __init__(self):
        self.__access_mms_server_url = 'http://localhost:1234'
        self.__api_token_pattern = re.compile('^[0-9a-f]{4}$')
        self.__args = self.__parse_args()
        self.__logger = self.__init_logger()
        self.__logger.info('Script starting.')
        # Override how exceptions are handled.
        sys.excepthook = self.__excepthook
        self.__logger.debug('Using arguments: ' + str(self.__args))
        self.__api_token = self.__load_api_token()
        self.__conf_parser = self.__init_conf_parser()
        self.__parse_conf()
        self.__log_parser = self.__init_log_parser()
        (self.__last_line, self.__last_request_time) = self.__parse_last_line()
        self.__compressed = configparser.ConfigParser.BOOLEAN_STATES[
            self.__get_conf_property('logs', 'compressed')
        ]
        self.__log_file_paths = self.__find_log_files()
        try:
            self.__parse_and_post()
        finally:
            self.__write_conf()
        self.__logger.info('Script finished.')


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
            default=os.path.realpath(os.path.dirname(__file__)) + '/conf.ini',
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
            '--version',
            action='version',
            version=__version__,
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
        logger = logging.getLogger(__title__)
        logger.setLevel(self.__args.log_level)
        return logger


    def __load_api_token(self):
        self.__logger.debug('Loading the API token.')
        try:
            api_token = os.environ['ACCESS_OOD_TOKEN']
        except KeyError:
            raise KeyError(
                'ACCESS_OOD_TOKEN environment variable is undefined.'
            )
        if not self.__api_token_pattern.match(api_token):
            raise ValueError(
                'ACCESS_OOD_TOKEN environment variable is in the wrong format.'
            )
        return api_token


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
            self.__get_conf_property('logs', 'format').replace('\\', '')
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


    def __parse_last_line(self):
        last_line = self.__get_conf_property('prev_run', 'last_line')
        if last_line == '':
            last_line = None
            last_request_time = datetime.fromtimestamp(0, tz=timezone.utc)
        else:
            entry = self.__log_parser.parse(last_line)
            last_request_time = entry.request_time
        self.__logger.debug('Previous line: ' + str(last_line))
        self.__logger.debug('Previous request time: ' + str(last_request_time))
        return (last_line, last_request_time)


    def __find_log_files(self):
        self.__logger.debug('Finding, sorting, and filtering the log files.')
        log_file_paths = glob.glob(
            self.__get_conf_property('logs', 'dir')
            + '/'
            + self.__get_conf_property('logs', 'filename_pattern')
        )
        # If the log files are compressed, we cannot efficiently parse just the
        # last line without parsing the entire file anyway, in which case we go
        # ahead and include all the files.
        if not self.__compressed:
            last_request_times = self.__filter_log_files(log_file_paths)
            log_file_paths = self.__sort_log_files(last_request_times)
        self.__logger.debug('Will process these log files:')
        self.__logger.debug(log_file_paths)
        if not log_file_paths:
            self.__logger.info('No log files to process.')
        return log_file_paths


    def __filter_log_files(self, log_file_paths):
        self.__logger.debug(
            'Parsing last request times in files and excluding old files.'
        )
        last_request_times = {}
        for log_file_path in log_file_paths:
            last_line = self.__get_last_line_in_file(log_file_path)
            try:
                if last_line.strip() == self.__last_line:
                    self.__logger.debug(
                        'Last line of '
                        + log_file_path
                        + ' is the configured last_line,'
                        + ' so will not be parsing it.'
                    )
                    continue
                entry = self.__log_parser.parse(last_line)
                last_request_times[log_file_path] = entry.request_time
                self.__logger.debug(
                    'Last request time of ' + log_file_path + ' is:'
                    + str(last_request_times[log_file_path])
                )
                if (
                    last_request_times[log_file_path]
                    < self.__last_request_time
                ):
                    self.__logger.debug(
                        'which is before the request time of the last line of'
                        + ' the previous run, so will not be parsing it.'
                    )
                    del last_request_times[log_file_path]
            except apachelogs.errors.InvalidEntryError:
                self.__logger.warn('Skipping invalid file: ' + log_file_path)
        return last_request_times


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


    def __sort_log_files(self, last_request_times):
        self.__logger.debug('Sorting list of log files:')
        sorted_last_request_times = sorted(
            last_request_times.items(),
            key=operator.itemgetter(1),
        )
        sorted_log_file_paths = [i[0] for i in sorted_last_request_times]
        self.__logger.debug(sorted_log_file_paths)
        return sorted_log_file_paths


    def __parse_and_post(self):
        self.__logger.debug('Starting parsing and POSTing of log files.')
        for log_file_path in self.__log_file_paths:
            self.__logger.info('Parsing and posting ' + log_file_path)
            try:
                response = requests.post(
                    self.__access_mms_server_url,
                    data=self.__parse_log_file(log_file_path),
                    headers={
                        'content-type': 'text/plain',
                        'authorization': 'Bearer ' + self.__api_token
                    },
                )
            except requests.exceptions.ConnectionError as e:
                if '[Errno 32] Broken pipe' in str(e):
                    raise requests.exceptions.ConnectionError(
                        'Server closed connection.'
                        + ' Please make sure API token is valid.'
                    ) from e
                else:
                    raise e
            self.__logger.debug(response.text)
            self.__conf_parser.set('prev_run', 'line', self.__new_last_line)


    def __parse_log_file(self, log_file_path):
        open_function = gzip.open if self.__compressed else open
        with open_function(log_file_path, 'rt') as log_file:
            line_num = 0
            for line in log_file:
                try:
                    entry = self.__log_parser.parse(line)
                    # Ignore lines that are before the configured last line.
                    if entry.request_time < self.__last_request_time:
                        continue
                    # If we come across the configured last line, skip it.
                    elif (
                        entry.request_time == self.__last_request_time
                        and line.strip() == self.__last_line
                    ):
                        continue
                    self.__new_last_line = line.strip()
                    if entry.format == apachelogs.COMBINED.replace(
                        'User-Agent', 
                        'User-agent'
                    ):
                        combined_line = line
                    else:
                        combined_line = self.__convert_to_combined_logformat(
                            entry
                        )
                    yield combined_line.encode()
                except apachelogs.errors.InvalidEntryError:
                    self.__logger.warn(
                        'Skipping invalid entry: ' + log_file_path
                        + ' line ' + line_num + ': ' + line
                    )
                line_num += 1


    def __convert_to_combined_logformat(self, entry):
        return (
            self.__entry_value_to_str(entry.remote_host)
            + ' ' + self.__entry_value_to_str(entry.remote_logname)
            + ' ' + self.__entry_value_to_str(entry.remote_user)
            + ' ' + self.__entry_time_field_to_str(
                entry.request_time_fields,
                'timestamp',
            )
            + ' "' + self.__entry_value_to_str(entry.request_line)
            + '" ' + self.__entry_value_to_str(entry.final_status)
            + ' ' + self.__entry_value_to_str(entry.bytes_sent)
            + ' "' + self.__entry_headers_in_to_str(entry, 'Referer')
            + '" "' + self.__entry_headers_in_to_str(entry, 'User-Agent')
            + '"\n'
        )


    def __entry_value_to_str(self, value):
        return '-' if value is None else str(value)


    def __entry_time_field_to_str(self, time_fields, key):
        return (
            time_fields[key].strftime('[%d/%b/%Y:%I:%M:%S %z]') \
            if key in time_fields \
                and time_fields[key] is not None \
            else '-'
        )


    def __entry_headers_in_to_str(self, entry, key):
        return (
            entry.headers_in[key] \
            if hasattr(entry, 'headers_in') \
                and key in entry.headers_in \
                and entry.headers_in[key] is not None \
            else '-'
        )


    def __write_conf(self):
        self.__logger.debug('Writing values back to configuration file.')
        comment_header = """\
# This is a configuration file used by post_ood_logs_to_access_mms.py.
#
# Set the values in the [logs] section to tell the script where to find logs
# and how to parse them.
#
# The value of "time" in the [prev_run] section will be overwritten in-place in
# this file by the script when it runs. The value of "last_line" will be set to
# the last line in the last successfully-POSTed file. In subsequent runs, lines
# will only be processed if their %t value is greater than or equal to the %t
# value of "last_line" (but if a line identical to "last_line" is encountered,
# it will be ignored). Thus, to control which lines are processed, you can set
# the value of "last_line" to have a particular %t value that is before the %t
# value of the first line you want processed (just make sure the value of
# "last_line" is in the proper LogFormat).

"""
        with open(self.__args.conf_path, 'w') as conf_file:
            conf_file.write(comment_header)
            self.__conf_parser.write(conf_file)


if __name__ == '__main__':
    LogPoster()
