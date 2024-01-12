__title__ = "xdmod-ondemand-export"
__version__ = "1.1.0"
__description__ = (
    "POST Open OnDemand logs to a web server for inclusion in XDMoD."
)

import apachelogs
import argparse
import base64
import configparser
from contextlib import ExitStack
from datetime import datetime
import glob
import gzip
import hmac
import json
import logging
import os
import re
import requests
import secrets
import sys


class LogPoster:
    def __init__(self, args=None):
        self.__api_token_name = 'XDMOD_ONDEMAND_EXPORT_TOKEN'
        self.__api_token_pattern = r'^[0-9]+\.[0-9a-f]{64}$'
        self.__time_format = '[%d/%b/%Y:%H:%M:%S %z]'
        self.__args = self.__parse_args(args)
        self.__logger = self.__init_logger()
        self.__logger.info('Script starting.')
        # Override how exceptions are handled.
        sys.excepthook = self.__excepthook
        self.__logger.debug('Using arguments: ' + str(self.__args))
        self.__validate_file_permissions(self.__args.conf_path, '400')
        self.__validate_file_permissions(self.__args.token_path, '600')
        self.__validate_file_permissions(self.__args.json_path, '600')
        (
            self.__api_token,
            self.__secret_key,
        ) = self.__load_api_token_and_secret_key()
        self.__conf_parser = self.__init_conf_parser()
        self.__parse_conf()
        self.__dir = self.__parse_dir()
        self.__log_parser = self.__init_log_parser()
        self.__json = self.__parse_json_file()
        self.__log_file_paths = self.__find_log_files()
        self.__url = self.__get_conf_property('destination', 'url')
        if self.__args.check_config:
            self.__logger.info(
                'Finished checking config, not parsing or POSTing any files.'
            )
        else:
            self.__new_json = {}
            try:
                app_lists = self.__get_app_lists()
                self.__send_app_lists(app_lists)
            # If sending the lists of applications fails, still try to send the
            # logs.
            finally:
                try:
                    self.__process_log_files()
                    self.__mark_deleted_log_files()
                finally:
                    self.__write_json()
                    self.__write_api_token_and_secret_key()
        self.__logger.info('Script finished.')

    def __parse_args(self, args=None):
        arg_parser = argparse.ArgumentParser(
            description=__description__,
            # Add information about default arguments to the help message.
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        arg_parser.add_argument(
            '-c',
            '--conf-path',
            default=os.path.expanduser('~/conf.ini'),
            help='path to the configuration file that declares where to'
            + ' find log files, how to parse them, and where to POST them',
        )
        arg_parser.add_argument(
            '-j',
            '--json-path',
            default=os.path.expanduser('~/last-run.json'),
            help='path to the JSON file that stores metadata about files that'
            + ' have already been processed. This file is both read from and'
            + ' written to by the script'
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
            default=os.path.expanduser('~/.token'),
            help='path to the token file'
        )
        arg_parser.add_argument(
            '--version',
            action='version',
            version=__version__,
        )
        arg_parser.add_argument(
            '--check-config',
            action='store_true',
            help='if provided, will simply check file permissions,'
            + ' make sure the API token exists, validate the configuration'
            + ' file, and exit',
        )
        parsed_args = arg_parser.parse_args(args)
        return parsed_args

    def __init_logger(self):
        logging.basicConfig()
        logger = logging.getLogger(__title__)
        logger.setLevel(self.__args.log_level)
        return logger

    def __excepthook(self, exctype, value, traceback):  # pragma: no cover
        if self.__args.log_level == 'DEBUG':
            sys.__excepthook__(exctype, value, traceback)
        else:
            self.__logger.error(value)

    def __validate_file_permissions(self, path, expected_permissions):
        mode = os.stat(path).st_mode
        actual_permissions = oct(mode)[-3:]
        if actual_permissions != expected_permissions:
            self.__logger.warning(
                'File permissions on ' + path + ' not set to '
                + expected_permissions + '.'
            )

    def __load_api_token_and_secret_key(self):
        self.__logger.debug('Loading the API token and secret key.')
        try:
            with open(self.__args.token_path, 'r') as token_file:
                contents = token_file.read()
        except FileNotFoundError:  # pragma: no cover
            raise FileNotFoundError(
                "Token file '" + self.__args.token_path + "' not found."
            ) from None
        secret_key = None
        try:
            json_contents = json.loads(contents)
            api_token = json_contents['api_token']
            secret_key = base64.a85decode(json_contents['secret_key'])
        except (json.decoder.JSONDecodeError, TypeError):
            self.__logger.debug(
                'File is not valid JSON, checking for token only.'
            )
            api_token = contents.replace('\n', '').strip()
        except KeyError as e:
            raise KeyError(
                'Token file is malformed. Missing key `' + e.args[0] + '`.'
            ) from None
        if re.match(self.__api_token_pattern, api_token) is None:
            raise ValueError('API token is malformed.')
        if secret_key is None:
            secret_key = secrets.token_bytes(16)
        return (api_token, secret_key)

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
        if not parsed_filenames:  # pragma: no cover
            raise FileNotFoundError(
                "Configuration file '" + self.__args.conf_path + "' not found."
            )

    def __parse_dir(self):
        dir_ = self.__get_conf_property('logs', 'dir')
        if not os.path.isdir(dir_):
            raise FileNotFoundError("No such directory: '" + dir_ + "'")
        return dir_

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

    def __parse_json_file(self):
        self.__logger.debug('Parsing the JSON file.')
        json_content = None
        with open(self.__args.json_path, 'r') as json_file:
            content = json_file.read()
            if content == '' or content.isspace():
                json_content = {}
            else:
                json_content = json.loads(content)
        return json_content

    def __find_log_files(self):
        self.__logger.debug('Finding the log files.')
        log_file_paths = sorted(glob.glob(
            self.__dir
            + '/'
            + self.__get_conf_property('logs', 'filename_pattern')
        ))
        self.__logger.debug('Found list of log files:')
        self.__logger.debug(log_file_paths)
        if not log_file_paths:
            self.__logger.info('No log files to process.')
        return log_file_paths

    def __get_app_lists(self):
        self.__logger.debug('Getting the application lists:')
        date = datetime.today().strftime('%Y-%m-%d')
        with open('/opt/ood/VERSION') as f:
            version = f.read().strip()
        system_apps = os.listdir('/var/www/ood/apps/sys')
        system_apps.sort()
        all_shared_apps = []
        usr_dirs_path = '/var/www/ood/apps/usr'
        usr_dirs = os.listdir(usr_dirs_path)
        for usr_dir in usr_dirs:
            try:
                shared_apps = os.listdir(
                    usr_dirs_path
                    + '/'
                    + usr_dir
                    + '/gateway'
                )
                all_shared_apps += shared_apps
            except FileNotFoundError:
                pass
        all_shared_apps.sort()
        app_lists = {
            'date': date,
            'version': version,
            'system_apps': system_apps,
            'shared_apps': all_shared_apps,
        }
        self.__logger.debug(app_lists)
        return app_lists

    def __send_app_lists(self, app_lists):
        self.__logger.debug('POSTing the application lists.')
        response = requests.post(
            self.__url,
            params={'type': 'app-list'},
            json=app_lists,
            headers={
                'content-type': 'application/json',
                'authorization': 'Bearer ' + self.__api_token,
            },
        )
        self.__process_response(response)

    def __process_response(self, response):
        self.__logger.debug('Got response:')
        self.__logger.debug(response.text)
        if response.status_code != 200:
            raise RuntimeError(
                'Server returned ' + str(response.status_code) + '.'
            )

    def __process_log_files(self):
        self.__logger.debug('Starting processing of log files.')
        for log_file_path in self.__log_file_paths:
            self.__logger.debug('Processing ' + log_file_path)
            with ExitStack() as stack:
                log_file = stack.enter_context(
                    self.__open_log_file(log_file_path)
                )
                first_line = log_file.readline().strip()
            st_size = os.stat(log_file_path).st_size
            # Look to see if the file's metadata is already stored in the JSON
            # file (meaning it has been POSTed before).
            found_in_json = False
            for stored_path in self.__json:
                if self.__json[stored_path]['first_line'] == first_line:
                    found_in_json = True
                    if self.__json[stored_path]['st_size'] == st_size:
                        self.__logger.debug(
                            'File already exists in JSON,'
                            + ' will not parse it.'
                        )
                        last_line = self.__json[stored_path]['last_line']
                    else:
                        self.__logger.debug(
                            'File already exists in JSON but with different'
                            + ' size, will parse and POST lines starting after'
                            + ' last line of last run.'
                        )
                        self.__parse_and_post(
                            log_file_path,
                            self.__json[stored_path]['last_line'],
                        )
                        last_line = self.__new_last_line
                    # Mark that the file still exists.
                    self.__json[stored_path]['still_exists'] = True
                    # Found the file's metadata, so stop searching.
                    break
            if not found_in_json:
                self.__logger.debug(
                    'File is new, will parse and POST.'
                )
                self.__parse_and_post(log_file_path, None)
                last_line = self.__new_last_line
            # Prepare to overwrite the file's metadata in the JSON file.
            self.__new_json[log_file_path] = {
                'first_line': first_line,
                'st_size': st_size,
                'last_line': last_line,
            }

    def __open_log_file(self, path):
        open_function = gzip.open if path.endswith('.gz') else open
        return open_function(path, 'rt', encoding='utf-8')

    def __parse_and_post(self, log_file_path, previous_line):
        self.__logger.info('Parsing and POSTing ' + log_file_path)
        response = requests.post(
            self.__url,
            data=self.__parse_log_file(log_file_path, previous_line),
            headers={
                'Content-Type': 'text/plain',
                'Authorization': 'Bearer ' + self.__api_token,
                'User-Agent': __title__ + ' v' + __version__,
            },
        )
        self.__process_response(response)

    def __parse_log_file(self, log_file_path, previous_line):
        line_num = 0
        num_invalid_entries = 0
        # If there is no previous line, we don't need to find it.
        found_previous_line = previous_line is None
        self.__new_last_line = previous_line
        with ExitStack() as stack:
            log_file = stack.enter_context(
                self.__open_log_file(log_file_path)
            )
            for line in log_file:
                if not found_previous_line:
                    if line.strip() == previous_line:
                        found_previous_line = True
                    # Note that for code coverage, the following continue
                    # statement is not properly marked as covered by
                    # coverage.py for Python <3.10, thus we add the pragma.
                    continue  # pragma: no cover
                try:
                    parsed_line = self.__parse_line(line, line_num)
                    if parsed_line is not None:
                        yield parsed_line
                except apachelogs.errors.InvalidEntryError:
                    self.__logger.debug(
                        'Skipping invalid entry: ' + log_file_path
                        + ' line ' + str(line_num)
                    )
                    num_invalid_entries += 1
                self.__new_last_line = line.strip()
                line_num += 1
            if num_invalid_entries > 0:
                self.__logger.warning(
                    'Skipped ' + str(num_invalid_entries)
                    + ' invalid entr' + (
                        'y' if num_invalid_entries == 1 else 'ies'
                    ) + ' in ' + log_file_path
                )

    def __parse_line(self, line, line_num):
        entry = self.__log_parser.parse(line)
        # Don't send lines for which a user is not logged in or is
        # unauthenticated.
        if (
            entry.remote_user is None
            or entry.remote_user == ''
            or entry.final_status == 401
        ):
            return
        else:
            # Replace the IP address with a hashed value.
            entry.remote_host = self.__get_ip_hash(entry.remote_host)
            # Convert the line to combined log format.
            combined_line = self.__convert_to_combined_logformat(entry)
            # Encode the line.
            return combined_line.encode()

    def __entry_time_field_to_str(self, time_fields, key):
        return (
            time_fields[key].strftime(self.__time_format)
            if key in time_fields
            and time_fields[key] is not None
            else '-'
        )

    def __get_ip_hash(self, ip):
        ip_bytes = bytes(ip, 'utf-8')
        digest = hmac.new(self.__secret_key, ip_bytes, 'md5').digest()
        ip_hash = base64.b64encode(
            digest,
            altchars=b'-_',
        ).decode('utf-8').replace('=', '')
        return ip_hash

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

    def __mark_deleted_log_files(self):
        for stored_path in self.__json:
            # If a file was not processed in this run of the script, it no
            # longer exists; mark it as such so it can be removed from the JSON
            # file.
            if 'still_exists' not in self.__json[stored_path]:
                self.__json[stored_path]['still_exists'] = False

    def __write_json(self):
        self.__logger.debug('Writing file data to JSON file.')
        # If any files were not marked as either still existing or not, assume
        # they still exist, because this means the script had an error before
        # it could finish processing all the files, and we don't want this to
        # clobber the JSON history.
        for stored_path in self.__json:
            if 'still_exists' not in self.__json[stored_path]:
                self.__new_json[stored_path] = {
                    'first_line': self.__json[stored_path]['first_line'],
                    'st_size': self.__json[stored_path]['st_size'],
                    'last_line': self.__json[stored_path]['last_line'],
                }
        self.__write_json_file(self.__args.json_path, self.__new_json)

    def __write_json_file(self, path, json_content):
        # Write to a temporary file first so that, if the write fails, it
        # doesn't accidentally clobber the file.
        tmp_path = path + '.tmp'
        descriptor = os.open(
            tmp_path,
            flags=os.O_CREAT | os.O_WRONLY,
            mode=0o600,
        )
        with open(descriptor, 'w') as json_file:
            json.dump(json_content, json_file, indent=4)
            json_file.write('\n')
        os.rename(tmp_path, path)

    def __write_api_token_and_secret_key(self):
        self.__logger.debug('Writing API token and secret key to token file.')
        json_content = {
            'api_token': self.__api_token,
            'secret_key': base64.a85encode(self.__secret_key).decode('utf-8'),
        }
        self.__write_json_file(self.__args.token_path, json_content)


def main():  # pragma: no cover
    LogPoster()


if __name__ == '__main__':  # pragma: no cover
    main()
