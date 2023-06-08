import filecmp
import os
import pytest
import re
import simple_web_server
import subprocess
import tempfile
import multiprocessing


TOKEN_NAME = 'XDMOD_ONDEMAND_EXPORT_TOKEN'
DESTINATION_URL = 'http://localhost:1234'
TESTS_DIR = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = '/root/xdmod-ondemand-export'
PACKAGES_DIR = ROOT_DIR + '/env/lib/python3.6/site-packages'
PACKAGE_DIR = PACKAGES_DIR + '/xdmod_ondemand_export'
SCRIPT_PATH = PACKAGE_DIR + '/xdmod_ondemand_export.py'
BASE_CONF_PATH = PACKAGE_DIR + '/conf.ini'


@pytest.fixture()
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def update_conf_file(path, args):
    with open(BASE_CONF_PATH, 'rt') as base_file:
        with open(path, 'wt') as file:
            for line in base_file:
                for arg in args:
                    line = re.sub(
                        r'^' + arg + r'\s*=.*',
                        arg + ' = ' + args[arg],
                        line,
                    )
                file.write(line)


def run(script_args, web_server_args, api_token):
    web_server_process = multiprocessing.Process(
        target=simple_web_server.run,
        args=web_server_args,
    )
    web_server_process.daemon = True
    web_server_process.start()
    script_cmd = ['python3', SCRIPT_PATH]
    for script_arg in script_args:
        script_cmd.append(script_arg)
        script_cmd.append(script_args[script_arg])
    if api_token is None:
        del os.environ[TOKEN_NAME]
    else:
        os.environ[TOKEN_NAME] = api_token
    script_process = subprocess.Popen(
        script_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    last_line = ''
    for output_line in iter(script_process.stdout.readline, ''):
        last_line = output_line.replace('\n', '')
        print(last_line)
    script_process.stdout.close()
    return_code = script_process.wait()
    if return_code != 0:
        web_server_process.terminate()
        raise RuntimeError(last_line)
    web_server_process.join()


def validate_output(path_to_actual, path_to_expected):
    with open(path_to_actual) as actual_file:
        actual_file_contents = actual_file.read()
        with open(path_to_expected) as expected_file:
            expected_file_contents = expected_file.read()
            assert filecmp.cmp(path_to_actual, path_to_expected), (
                'files differ:\nactual:\n' + actual_file_contents
                + 'expected:\n' + expected_file_contents
            )


def run_test(
    tmp_dir,
    name='default',
    conf_args={},
    additional_script_args={'-l': 'DEBUG'},
    api_token=(
        '1.10fe91043025e974f798d8ddc320ac794eacefd43c609c7eb42401bccfccc8ae'
    ),
    num_files=1,
):
    artifacts_dir = TESTS_DIR + '/artifacts/' + name
    inputs_dir = artifacts_dir + '/inputs'
    expected_output_file_path = artifacts_dir + '/outputs/access.log'
    actual_output_file_path = tmp_dir + '/access.log'
    conf_path = tmp_dir + '/conf.ini'
    update_conf_file(
        conf_path,
        {
            **conf_args,
            **{
                'url': DESTINATION_URL,
                'dir': conf_args['dir'] if 'dir' in conf_args else inputs_dir,
            }},
    )
    script_args = {'-c': conf_path}
    for arg in additional_script_args:
        script_args[arg] = additional_script_args[arg]
    web_server_args = ((actual_output_file_path,), num_files)
    run(script_args, web_server_args, api_token)
    if num_files > 0:
        validate_output(actual_output_file_path, expected_output_file_path)


@pytest.mark.parametrize(
    'nickname, logformat',
    [
        (
            'combined',
            '%h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-agent}i"',
        ),
        (
            'combined',
            '%h %l %u %t \\"%r\\" %>s %b'
            + ' \\"%{Referer}i\\" \\"%{User-agent}i\\"',
        ),
        (
            'common',
            '%h %l %u %t "%r" %>s %b',
        ),
        (
            'common',
            '%h %l %u %t \\"%r\\" %>s %b',
        ),
        (
            'weird',
            '%>s "%{User-agent}i" %u %b %t "%{Referer}i" %h "%r" %l',
        )
    ],
    ids=(
        'combined_no_backslashes',
        'combined_with_backslashes',
        'common_no_backslashes',
        'common_with_backslashes',
        'weird',
    ),
)
def test_logformat(tmp_dir, nickname, logformat):
    run_test(tmp_dir, nickname + '_logformat', {'format': logformat})


def test_compressed(tmp_dir):
    run_test(tmp_dir, 'compressed', {'compressed': 'true'})


@pytest.mark.parametrize(
    'log_level',
    ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
)
def test_log_level(tmp_dir, log_level):
    run_test(tmp_dir, additional_script_args={'-l': log_level})


def test_no_api_token(tmp_dir):
    with pytest.raises(
        RuntimeError,
        match=TOKEN_NAME + ' environment variable is undefined.'
    ):
        run_test(tmp_dir, api_token=None)


def test_malformed_api_token(tmp_dir):
    with pytest.raises(
        RuntimeError,
        match=TOKEN_NAME + ' environment variable is in the wrong format.'
    ):
        run_test(tmp_dir, api_token='x')


def test_conf_file_not_found(tmp_dir):
    with pytest.raises(
        RuntimeError,
        match='Configuration file asdf not found.'
    ):
        run_test(tmp_dir, additional_script_args={'-c': 'asdf'})


@pytest.mark.parametrize(
    'conf_args, match',
    [
        (
            {'dir': 'asdf'},
            "No such directory: 'asdf'",
        ),
        (
            {'filename_pattern': ''},
            'Is a directory',
        ),
        (
            {'format': '%1'},
            "Invalid log format directive at index 0 of '%1'",
        ),
        (
            {'last_line': 'asdf'},
            "Could not match log entry 'asdf' against log format"
        ),
    ],
    ids=('dir', 'filename_pattern', 'format', 'last_line')
)
def test_invalid_conf_property(tmp_dir, conf_args, match):
    with pytest.raises(RuntimeError, match=match):
        run_test(tmp_dir, conf_args=conf_args)


def test_no_files_to_process(tmp_dir):
    run_test(tmp_dir, conf_args={'filename_pattern': 'asdf'}, num_files=0)
