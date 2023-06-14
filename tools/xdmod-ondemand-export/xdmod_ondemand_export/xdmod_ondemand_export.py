#!/usr/bin/env python3

from __version__ import __title__, __version__, __description__
import apachelogs
import argparse
import configparser
from datetime import datetime, timezone
import glob
import gzip
import logging
import operator
import os
import requests
import sys


class LogPoster:
    def __init__(self):
        self.__api_token_name = 'XDMOD_ONDEMAND_EXPORT_TOKEN'
        self.__time_format = '[%d/%b/%Y:%H:%M:%S %z]'
        self.__args = self.__parse_args()
        self.__logger = self.__init_logger()
        self.__logger.info('Script starting.')
        # Override how exceptions are handled.
        sys.excepthook = self.__excepthook
        self.__logger.debug('Using arguments: ' + str(self.__args))
        self.__validate_file_permissions()
        self.__api_token = self.__load_api_token()
        self.__conf_parser = self.__init_conf_parser()
        self.__parse_conf()
        self.__dir = self.__parse_dir()
        self.__log_parser = self.__init_log_parser()
        self.__last_line = self.__parse_last_line()
        self.__last_request_time = self.__parse_last_request_time()
        self.__compressed = configparser.ConfigParser.BOOLEAN_STATES[
            self.__get_conf_property('logs', 'compressed')
        ]
        self.__log_file_paths = self.__find_log_files()
        self.__url = self.__get_conf_property('destination', 'url')
        if self.__args.check_config:
            self.__logger.info(
                'Finished checking config, not parsing or POSTing any files.'
            )
        else:
            self.__new_last_line = None
            self.__new_last_request_time = None
            try:
                self.__parse_and_post()
            finally:
                self.__write_conf()
        self.__logger.info('Script finished.')

    def __parse_args(self):
        arg_parser = argparse.ArgumentParser(
            description=__description__,
            # Add information about default arguments to the help message.
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        arg_parser.add_argument(
            '-c',
            '--conf-path',
            default=os.path.realpath(os.path.dirname(__file__)) + '/conf.ini',
            help='path to the configuration file that declares where to'
            + ' find log files, how to parse them, and where to POST them',
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
        arg_parser.add_argument(
            '--bash-script',
            help='path to the Bash script that is calling this Python script'
            + ' (this parameter is used to validate file permissions)',
        )
        arg_parser.add_argument(
            '--check-config',
            action='store_true',
            help='if provided, will simply check file permissions,'
            + ' make sure the API token exists, validate the configuration'
            + ' file, and exit',
        )
        args = arg_parser.parse_args()
        return args

    def __init_logger(self):
        logging.basicConfig()
        logger = logging.getLogger(__title__)
        logger.setLevel(self.__args.log_level)
        return logger

    def __excepthook(self, exctype, value, traceback):
        if self.__args.log_level == 'DEBUG':
            sys.__excepthook__(exctype, value, traceback)
        else:
            self.__logger.error(value)

    def __validate_file_permissions(self):
        if self.__args.bash_script is not None:
            bash_script_permissions = self.__get_file_permissions(
                self.__args.bash_script
            )
            if bash_script_permissions != '700':
                self.__logger.warning(
                    'File permissions on Bash script not set to 700'
                )
        conf_file_permissions = self.__get_file_permissions(
            self.__args.conf_path
        )
        if conf_file_permissions != '600':
            self.__logger.warning(
                'File permissions on configuration file not set to 600'
            )

    def __get_file_permissions(self, path):
        mode = os.stat(path).st_mode
        permissions = oct(mode)[-3:]
        return permissions

    def __load_api_token(self):
        self.__logger.debug('Loading the API token.')
        try:
            api_token = os.environ[self.__api_token_name]
        except KeyError:
            raise KeyError(
                self.__api_token_name + ' environment variable is undefined.'
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
            raise FileNotFoundError(
                'Configuration file ' + self.__args.conf_path + ' not found.'
            )

    def __init_log_parser(self):
        self.__logger.debug('Initializing the log parser.')
        log_parser = apachelogs.LogParser(
            self.__get_conf_property('logs', 'format').replace('\\', '')
        )
        return log_parser

    def __parse_dir(self):
        dir_ = self.__get_conf_property('logs', 'dir')
        if not os.path.isdir(dir_):
            raise FileNotFoundError("No such directory: '" + dir_ + "'")
        return dir_

    def __get_conf_property(self, section, key):
        self.__logger.debug(
            'Getting `' + key + '` property from the [' + section
            + '] section of the configuration file:'
        )
        value = self.__conf_parser.get(section, key)
        # Do not log the "last_line" value since it might contain sensitive
        # information (e.g., IP address and username).
        if section == 'prev_run' and key == 'last_line':
            self.__logger.debug('[redacted]')
        else:
            self.__logger.debug(value)
        return value

    def __parse_last_line(self):
        last_line = self.__get_conf_property('prev_run', 'last_line')
        if last_line == '':
            last_line = None
        return last_line

    def __parse_last_request_time(self):
        last_request_time = self.__get_conf_property(
            'prev_run',
            'last_request_time',
        )
        last_request_time = (
            datetime.fromtimestamp(0, tz=timezone.utc)
            if last_request_time == ''
            else datetime.strptime(last_request_time, self.__time_format)
        )
        self.__logger.debug('Last request time: ' + str(last_request_time))
        return last_request_time

    def __find_log_files(self):
        self.__logger.debug('Finding, sorting, and filtering the log files.')
        log_file_paths = glob.glob(
            self.__dir
            + '/'
            + self.__get_conf_property('logs', 'filename_pattern')
        )
        self.__logger.debug('Found list of log files:')
        self.__logger.debug(log_file_paths)
        # If the log files are uncompressed, we will read each file's last line
        # to filter out certain files and determine the ordering of the rest.
        # If the files are compressed, we cannot efficiently parse just the
        # last line without parsing the entire file anyway, in which case we
        # will include all the files and sort them by their first line.
        if self.__compressed:
            request_times = self.__parse_first_request_times(log_file_paths)
        else:
            request_times = self.__filter_log_files(log_file_paths)
        log_file_paths = self.__sort_log_files(request_times)
        if not log_file_paths:
            self.__logger.info('No log files to process.')
        return log_file_paths

    def __parse_first_request_times(self, log_file_paths):
        self.__logger.debug('Parsing first request time in each log file.')
        first_request_times = {}
        for log_file_path in log_file_paths:
            try:
                first_request_times[log_file_path] = next(
                    self.__parse_log_file(
                        log_file_path,
                        parse_line_method=self.__get_request_time,
                    )
                )
            except StopIteration:
                self.__logger.warning(
                    'Skipping invalid file: ' + log_file_path
                )
        return first_request_times

    def __parse_log_file(self, log_file_path, parse_line_method):
        line_num = 0
        num_invalid_entries = 0
        open_function = gzip.open if self.__compressed else open
        with open_function(log_file_path, 'rt') as log_file:
            for line in log_file:
                try:
                    parsed_line = parse_line_method(line, line_num)
                    if parsed_line is not None:
                        yield parsed_line
                except apachelogs.errors.InvalidEntryError:
                    self.__logger.debug(
                        'Skipping invalid entry: ' + log_file_path
                        + ' line ' + str(line_num)
                    )
                    num_invalid_entries += 1
                line_num += 1
            if num_invalid_entries > 0:
                self.__logger.warning(
                    'Skipped ' + str(num_invalid_entries)
                    + ' invalid entr' + (
                        'y' if num_invalid_entries == 1 else 'ies'
                    ) + ' in ' + log_file_path
                )

    def __get_request_time(self, line, line_num):
        entry = self.__log_parser.parse(line)
        return entry.request_time

    def __filter_log_files(self, log_file_paths):
        self.__logger.debug(
            'Parsing last request times in files and excluding old files.'
        )
        last_request_times = {}
        for log_file_path in log_file_paths:
            last_request_time = self.__get_last_request_time(log_file_path)
            # If the last request time can be parsed and is not older than the
            # configured "last_request_time", include the file.
            if last_request_time is not None:
                last_request_times[log_file_path] = last_request_time
        return last_request_times

    def __get_last_request_time(self, log_file_path):
        # Open the file in binary mode so we can seek backwards from the end
        # of the file.
        with open(log_file_path, 'rb') as file:
            # Start on the last line of the file.
            on_last_line = True
            # Until we hit the top of the file,
            hit_top = False
            while not hit_top:
                # Seek back one line.
                (file, hit_top) = self.__seek_back_one_line(
                    file,
                    hit_top,
                    on_last_line,
                )
                # Read the current line.
                line = file.readline().decode('utf-8').strip()
                # If the line is the configured value of "last_line", skip the
                # file.
                if line == self.__last_line:
                    self.__logger.debug(
                        'Last line of ' + log_file_path + ' is the configured'
                        + '"last_line", so will not be parsing the file.'
                    )
                    return None
                # Try parsing the line.
                try:
                    entry = self.__log_parser.parse(line)
                    # If the line can be parsed, get the request time from it.
                    last_request_time = entry.request_time
                    self.__logger.debug(
                        'Last request time of ' + log_file_path + ' is:'
                        + str(last_request_time)
                    )
                    # If the request time is before the configured value of
                    # "last_request_time", skip the file.
                    if (last_request_time < self.__last_request_time):
                        self.__logger.debug(
                            'which is before the request time of the last line'
                            ' of the previous run, so will not be parsing it.'
                        )
                        return None
                    # Otherwise, return the last request time.
                    return last_request_time
                # If the line couldn't be parsed, log it and move on to the
                # next one.
                except apachelogs.errors.InvalidEntryError:
                    self.__logger.debug(
                        'Skipping invalid entry at end of ' + log_file_path
                    )
                # Flag that we are no longer on the last line.
                on_last_line = False
        # If we hit the top of the file without finding a valid line, the file
        # is invalid.
        self.__logger.warning(
            'Skipping invalid file: ' + log_file_path
        )

    def __seek_back_one_line(self, file, hit_top, on_last_line):
        # If we're on the last line, we seek back to the previous newline in
        # preparation for reading the line; otherwise, we need to seek back two
        # newlines, because we previously read past a newline when trying to
        # parse the line we just tried to parse.
        try:
            for _ in range(0, 1 if on_last_line else 2):
                # Move to the second-to-last character in the file if we are on
                # the last line, otherwise two characters before the current
                # character.
                file.seek(
                    -2,
                    os.SEEK_END if on_last_line else os.SEEK_CUR,
                )
                # Read the character, which seeks forward one character.
                char = file.read(1)
                # Until the character is a newline,
                while char != b'\n':
                    # Seek back two characters.
                    file.seek(-2, os.SEEK_CUR)
                    # Read the character, which seeks forward one character.
                    char = file.read(1)
        # If we seek past the top of the file,
        except OSError:
            # Flag that we hit the top.
            hit_top = True
            # Seek to the top of the file.
            file.seek(0)
        return (file, hit_top)

    def __sort_log_files(self, request_times):
        self.__logger.debug('Sorting list of log files:')
        sorted_request_times = sorted(
            request_times.items(),
            key=operator.itemgetter(1),
        )
        sorted_log_file_paths = [i[0] for i in sorted_request_times]
        self.__logger.debug(sorted_log_file_paths)
        return sorted_log_file_paths

    def __parse_and_post(self):
        self.__logger.debug('Starting parsing and POSTing of log files.')
        for log_file_path in self.__log_file_paths:
            self.__logger.info('Parsing and POSTing ' + log_file_path)
            try:
                response = requests.post(
                    self.__url,
                    data=self.__parse_log_file(
                        log_file_path,
                        parse_line_method=self.__parse_line,
                    ),
                    headers={
                        'content-type': 'text/plain',
                        'authorization': 'Bearer ' + self.__api_token,
                    },
                )
            except Exception as e:
                if '[Errno 32] Broken pipe' in str(e):
                    raise requests.exceptions.ConnectionError(
                        'Server closed connection.'
                        + ' Please make sure API token is valid.'
                    ) from e
                else:
                    raise e
            self.__logger.debug('Got response:')
            self.__logger.debug(response.text)
            if response.status_code != 200:
                raise RuntimeError(
                    'Server returned ' + str(response.status_code)
                )
            self.__conf_parser.set(
                'prev_run',
                'last_line',
                self.__new_last_line,
            )
            self.__conf_parser.set(
                'prev_run',
                'last_request_time',
                self.__new_last_request_time,
            )

    def __parse_line(self, line, line_num):
        entry = self.__log_parser.parse(line)
        # Skip lines that are before the configured "last_request_time".
        if entry.request_time < self.__last_request_time:
            return
        # If we come across the configured "last_line", skip it.
        elif (
            entry.request_time == self.__last_request_time
            and line.strip() == self.__last_line
        ):
            return
        # Skip lines for which a user is not logged in.
        if entry.remote_user is None:
            return
        # Convert the line to combined log format if it isn't already.
        if entry.format == apachelogs.COMBINED.replace(
            'User-Agent',
            'User-agent',
        ):
            combined_line = line
        else:
            combined_line = self.__convert_to_combined_logformat(
                entry
            )
        # Encode the line.
        encoded_line = combined_line.encode()
        # Prepare to set the configured values for "last_line" and
        # "last_request_time".
        self.__new_last_line = line.strip()
        self.__new_last_request_time = (
            self.__entry_time_field_to_str(
                entry.request_time_fields,
                'timestamp',
            )
        )
        return encoded_line

    def __entry_time_field_to_str(self, time_fields, key):
        return (
            time_fields[key].strftime(self.__time_format)
            if key in time_fields
            and time_fields[key] is not None
            else '-'
        )

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

    def __entry_headers_in_to_str(self, entry, key):
        return (
            entry.headers_in[key]
            if hasattr(entry, 'headers_in')
            and key in entry.headers_in
            and entry.headers_in[key] is not None
            else '-'
        )

    def __write_conf(self):
        self.__logger.debug('Writing values back to configuration file.')
        comment_header = """\
# This is a configuration file used by xdmod_ondemand_export.py.
#
# Set the value of "url" in the [destination] section to specify where the logs
# will be POSTed.
#
# Set the values in the [logs] section to tell the script where to find logs
# and how to parse them.
#
# The values in the [prev_run] section will be overwritten in-place in this
# file by the script when it runs. The value of "last_line" will be set to the
# last line in the last successfully-POSTed file. The value of
# "last_request_time" will be set to the %t value of "last_line". In subsequent
# runs, lines will only be processed if their %t value is greater than or equal
# to "last_request_time" (but if a line identical to "last_line" is
# encountered, it will be ignored). Thus, to control which lines are processed,
# you can set the value of "last_request_time" to be before the %t value of the
# first line you want processed; just make sure the value of
# "last_request_time" is in the format {0}, e.g.,
# [31/May/2023:23:59:59 -0500].

"""
        comment_header = comment_header.format(self.__time_format)
        with open(self.__args.conf_path, 'w') as conf_file:
            conf_file.write(comment_header)
            self.__conf_parser.write(conf_file)


if __name__ == '__main__':
    LogPoster()
