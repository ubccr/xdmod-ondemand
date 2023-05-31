import filecmp
import pytest
import re
import simple_web_server
import subprocess
import tempfile
import threading


ROOT_DIR = '/root/post_ood_logs_to_access_mms'
TESTS_DIR = ROOT_DIR + '/tests'
PACKAGES_DIR = ROOT_DIR + '/env/lib/python3.6/site-packages'
PACKAGE_DIR = PACKAGES_DIR + '/post_ood_logs_to_access_mms'
SCRIPT_PATH = PACKAGE_DIR + '/post_ood_logs_to_access_mms.sh'
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


def run(script_args, web_server_args):
    server_thread = threading.Thread(
        target=simple_web_server.run,
        args=web_server_args,
    )
    server_thread.start()
    subprocess_args = [SCRIPT_PATH]
    for script_arg in script_args:
        subprocess_args.append(script_arg)
        subprocess_args.append(script_args[script_arg])
    subprocess.run(subprocess_args)
    server_thread.join()


def validate_output(path_to_actual, path_to_expected):
    with open(path_to_actual) as actual_file:
        actual_file_contents = actual_file.read()
        with open(path_to_expected) as expected_file:
            expected_file_contents = expected_file.read()
            assert filecmp.cmp(path_to_actual, path_to_expected), (
                'files differ:\nactual:\n' + actual_file_contents
                + 'expected:\n' + expected_file_contents
            )


def run_test(tmp_dir, name, conf_args, additional_script_args={'-l': 'DEBUG'}):
    artifacts_dir = TESTS_DIR + '/artifacts/' + name
    inputs_dir = artifacts_dir + '/inputs'
    expected_output_file_path = artifacts_dir + '/outputs/access.log'
    actual_output_file_path = tmp_dir + '/access.log'
    conf_path = tmp_dir + '/conf.ini'
    update_conf_file(
        conf_path,
        {**conf_args, **{'dir': inputs_dir}},
    )
    script_args = {'-c': conf_path}
    for arg in additional_script_args:
        script_args[arg] = additional_script_args[arg]
    web_server_args = ((actual_output_file_path,), 1)
    run(script_args, web_server_args)
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
    run_test(tmp_dir, 'default', {}, {'-l': log_level})
