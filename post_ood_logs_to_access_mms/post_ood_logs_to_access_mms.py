#!/usr/bin/env python3

# Find Open OnDemand logs, parse them, and send them via POST request to the
# endpoint run by the ACCESS Monitoring and Measurement (ACCESS MMS) team who
# will ingest and aggregate the data to be included in ACCESS XDMoD.

# Import required libraries.
import apachelogs
import argparse
import configparser
import glob
import logging
import os
import re
import requests
import sys

class LogPoster:
    def __init__(self):
        self.__access_mms_server_url = 'http://localhost:1234'
        self.__api_token_pattern = re.compile('^[0-9a-f]{4}$')
        self.__version = self.__read_version()
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
        self.__log_file_paths = self.__find_log_files()
        (self.__prev_line, self.__prev_request_time) = self.__parse_prev_line()
        try:
            self.__parse_and_post()
        finally:
            self.__write_conf()
        self.__logger.info('Script finished.')


    def __read_version(self):
        with open('VERSION', 'r') as version_file:
            version = version_file.read().strip()
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


    def __load_api_token(self):
        self.__logger.debug('Loading the API token.')
        file_stat = os.stat(self.__args.token_path)
        if file_stat.st_mode != 33152:
            self.__logger.warning(
                'File permissions on '
                + self.__args.token_path
                + ' not set to 600!'
            )
        with open(self.__args.token_path, 'r') as token_file:
            api_token = token_file.read().strip()
        if not self.__api_token_pattern.match(api_token):
            raise ValueError('API token is in the wrong format.')
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
        self.__logger.debug('Finding, sorting, and filtering the log files.')
        log_file_paths = glob.glob(
            self.__get_conf_property('logs', 'dir')
            + '/'
            + self.__get_conf_property('logs', 'filename_prefix')
            + '*'
        )
        log_file_paths = self.__sort_log_files(log_file_paths)
        log_file_paths = self.__filter_log_files(log_file_paths)
        self.__logger.debug('Will process these log files:')
        self.__logger.debug(log_file_paths)
        return log_file_paths


    def __sort_log_files(self, log_file_paths):
        log_file_paths = sorted(log_file_paths)
        # Move the first file in the list to the end, since it is assumed to be
        # the file that has no suffix and is thus the newest file that has not
        # been rotated yet.
        log_file_paths.append(log_file_paths.pop(0))
        return log_file_paths


    def __filter_log_files(self, log_file_paths):
        # Of file paths that have suffixes (i.e., not the last file in the
        # list, see __sort_log_files()), only include those that are greater
        # than the configured previous file's path.
        prev_file_path = self.__get_conf_property('prev_run', 'file')
        newest_file = log_file_paths.pop()
        log_file_paths = list(
            filter(
                lambda file_path: file_path > prev_file_path,
                log_file_paths
            )
        )
        log_file_paths.append(newest_file)
        return log_file_paths


    def __parse_prev_line(self):
        prev_line = self.__get_conf_property('prev_run', 'line')
        if prev_line == '':
            prev_line = None
            prev_request_time = None
        else:
            entry = self.__log_parser.parse(prev_line)
            prev_request_time = entry.request_time
        self.__logger.debug('Previous line: ' + str(prev_line))
        self.__logger.debug('Previous request time: ' + str(prev_request_time))
        return (prev_line, prev_request_time)


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
            if log_file_path != self.__log_file_paths[-1]:
                self.__conf_parser.set('prev_run', 'file', log_file_path)
            self.__conf_parser.set('prev_run', 'line', self.__new_prev_line)


    def __parse_log_file(self, log_file_path):
        with open(log_file_path, 'r') as log_file:
            line_num = 0
            seen_prev_line = False
            for line in log_file:
                try:
                    entry = self.__log_parser.parse(line)
                    # Ignore lines that are before the configured previous
                    # line.
                    if self.__prev_request_time is not None:
                        if entry.request_time < self.__prev_request_time:
                            continue
                        elif entry.request_time == self.__prev_request_time:
                            if not seen_prev_line:
                                if line.strip() == self.__prev_line:
                                    seen_prev_line = True
                                continue
                    # Ignore lines that have the same request time and are
                    # before the configured previous line.
                    # Ignore lines for which a user is not logged in.
                    if entry.remote_user is None:
                        continue
                    # TODO: reformat into default LogFormat if needed.
                    self.__new_prev_line = line.strip()
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
# The values in the [prev_run] section will be overwritten in-place in this
# file by the script when it runs. Log files whose names contain a suffix
# (e.g., access.log.1, access.log-20200315) will only be processed whose names
# are lexicographically less than the value of the configured "file". For log
# files that are being processed, lines will be ignored for which the value of
# %t is less than the value of %t in the configured "line". For lines for which
# the value of %t is equal to the value of %t in the configured "line", lines
# will be ignored up to and including the line that matches the provided
# "line".

"""
        with open(self.__args.conf_path, 'w') as conf_file:
            conf_file.write(comment_header)
            self.__conf_parser.write(conf_file)


if __name__ == '__main__':
    LogPoster()
