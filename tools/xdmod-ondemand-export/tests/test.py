import filecmp
import glob
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
PACKAGES_DIR = glob.glob(ROOT_DIR + '/env/lib/python3.*/site-packages')[0]
PACKAGE_DIR = PACKAGES_DIR + '/xdmod_ondemand_export'
BASH_SCRIPT_PATH = PACKAGE_DIR + '/xdmod-ondemand-export.sh'
BASE_CONF_PATH = PACKAGE_DIR + '/conf.ini'


@pytest.fixture()
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def update_bash_script(path, token):
    with open(BASH_SCRIPT_PATH, 'rt') as base_file:
        old_umask = os.umask(0o077)
        with open(path, 'wt') as file_:
            for line in base_file:
                line = re.sub(
                    r'^' + TOKEN_NAME + r'=.*',
                    '' if token == '' else (TOKEN_NAME + '=' + token),
                    line,
                )
                file_.write(line)
        os.umask(old_umask)
    os.chmod(path, 0o0700)


def update_conf_file(path, args):
    with open(BASE_CONF_PATH, 'rt') as base_file:
        old_umask = os.umask(0o077)
        with open(path, 'wt') as file_:
            for line in base_file:
                for arg in args:
                    line = re.sub(
                        r'^' + arg + r'\s*=.*',
                        arg + ' = ' + args[arg],
                        line,
                    )
                file_.write(line)
        os.umask(old_umask)


def run(tmp_dir, script_args, web_server_args, api_token):
    web_server_process = multiprocessing.Process(
        target=simple_web_server.run,
        args=web_server_args,
    )
    web_server_process.daemon = True
    web_server_process.start()
    bash_script_path = tmp_dir + '/xdmod-ondemand-export.sh'
    update_bash_script(bash_script_path, api_token)
    script_cmd = [bash_script_path]
    for script_arg in script_args:
        script_cmd.append(script_arg)
        if script_args[script_arg] is not None:
            script_cmd.append(script_args[script_arg])
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
    artifact_dir='default',
    conf_args={},
    additional_script_args={},
    api_token=(
        '1.10fe91043025e974f798d8ddc320ac794eacefd43c609c7eb42401bccfccc8ae'
    ),
    num_files=1,
    mode=200,
):
    artifacts_dir = TESTS_DIR + '/artifacts/' + artifact_dir
    inputs_dir = artifacts_dir + '/inputs'
    expected_output_path_prefix = artifacts_dir + '/outputs/access.log.'
    conf_path = tmp_dir + '/conf.ini'
    update_conf_file(
        conf_path,
        {
            **conf_args,
            **{
                'url': (
                    conf_args['url']
                    if 'url' in conf_args
                    else DESTINATION_URL
                ),
                'dir': conf_args['dir'] if 'dir' in conf_args else inputs_dir,
            }},
    )
    script_args = {
        '-c': conf_path,
        '-l': 'DEBUG',
    }
    for arg in additional_script_args:
        script_args[arg] = additional_script_args[arg]
    web_server_args = (tmp_dir, num_files, mode)
    try:
        run(tmp_dir, script_args, web_server_args, api_token)
    except RuntimeError as e:
        if mode != 200:
            assert str(e) == 'RuntimeError: Server returned ' + str(mode)
        else:
            raise e
    for i in range(0, num_files):
        validate_output(
            tmp_dir + '/access.log.' + str(i),
            expected_output_path_prefix + str(i),
        )


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
        match=TOKEN_NAME + ' environment variable is undefined.',
    ):
        run_test(tmp_dir, api_token='')


def test_malformed_api_token(tmp_dir):
    with pytest.raises(
        RuntimeError,
        match=TOKEN_NAME + ' environment variable is in the wrong format.',
    ):
        run_test(tmp_dir, api_token='x')


def test_conf_file_not_found(tmp_dir):
    with pytest.raises(
        RuntimeError,
        match="\\[Errno 2\\] No such file or directory: 'asdf'",
    ):
        run_test(tmp_dir, additional_script_args={'-c': 'asdf'})


@pytest.mark.parametrize(
    'conf_args, artifact_dir, match',
    [
        (
            {'url': 'asdf'},
            'default',
            "Invalid URL 'asdf': No scheme supplied."
        ),
        (
            {'url': 'http://asdf'},
            'default',
            '\\[Errno -2\\] Name or service not known',
        ),
        (
            {'dir': 'asdf'},
            'default',
            "No such directory: 'asdf'",
        ),
        (
            {'filename_pattern': ''},
            'default',
            'Is a directory',
        ),
        (
            {'format': '%1'},
            'default',
            "Invalid log format directive at index 0 of '%1'",
        ),
        (
            {'compressed': 'asdf'},
            'default',
            "KeyError: 'asdf'",
        ),
        (
            {'compressed': 'true'},
            'default',
            'Not a gzipped file',
        ),
        (
            {'compressed': 'false'},
            'compressed',
            "'utf-8' codec can't decode byte",
        ),
        (
            {'last_request_time': 'asdf'},
            'default',
            "time data 'asdf' does not match format "
            + "'\\[%d/%b/%Y:%H:%M:%S %z\\]'"
        ),
    ],
    ids=(
        'url_no_scheme',
        'url_unknown_service',
        'dir',
        'filename_pattern',
        'format',
        'compressed_invalid_value',
        'compressed_wrong_value_true',
        'compressed_wrong_value_false',
        'last_request_time',
    )
)
def test_invalid_conf_property(tmp_dir, conf_args, artifact_dir, match):
    with pytest.raises(RuntimeError, match=match):
        run_test(tmp_dir, artifact_dir=artifact_dir, conf_args=conf_args)


def test_no_files_to_process(tmp_dir):
    run_test(tmp_dir, conf_args={'filename_pattern': 'asdf'}, num_files=0)


@pytest.mark.parametrize(
    'artifact_dir, conf_args, num_files',
    [
        ('some_old_some_new', {}, 2),
        ('some_old_some_new_compressed', {'compressed': 'true'}, 4)
    ],
    ids=(
        'uncompressed',
        'compressed',
    )
)
def test_some_old_some_new(tmp_dir, artifact_dir, conf_args, num_files):
    run_test(
        tmp_dir,
        artifact_dir=artifact_dir,
        conf_args={**{
            'last_line': '127.0.0.0 - testuser1 [01/Jul/2021:03:17:06 -0500] '
            + '"GET /pun/sys/dashboard/apps/icon/jupyter_quantum_chem/sys/'
            + 'sys HTTP/1.1" 401 381 "https://ondemand.ccr.buffalo.edu/'
            + 'pun/sys/dashboard/batch_connect/sessions" "Mozilla/5.0 '
            + '(Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
            + 'like Gecko) Chrome/91.0.4472.77 Safari/537.36"',
            'last_request_time': '[01/Jul/2021:03:17:06 -0500]'
        }, **conf_args},
        num_files=num_files,
    )


def test_check_config(tmp_dir):
    run_test(
        tmp_dir,
        additional_script_args={'--check-config': None},
        num_files=0,
    )


def test_skip_file_matching_last_line(tmp_dir):
    run_test(
        tmp_dir,
        artifact_dir='file_matching_last_line',
        conf_args={
            'last_line': '127.0.0.0 - testuser2 [30/Jun/2021:03:17:08 -0500] '
            + '"GET /pun/sys/dashboard/apps/icon/jupyter_quantum_chem/sys/sys '
            + 'HTTP/1.1" 401 381 "https://ondemand.ccr.buffalo.edu/pun/sys/'
            + 'dashboard/batch_connect/sessions" "Mozilla/5.0 (Windows NT '
            + '10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
            + 'Chrome/91.0.4472.77 Safari/537.36"',
            'last_request_time': '[30/Jun/2021:03:17:08 -0500]',
        },
        num_files=2
    )


@pytest.mark.parametrize(
    'artifact_dir, compressed',
    [
        ('two_runs', 'false'),
        ('two_runs_compressed', 'true'),
    ],
    ids=(
        'uncompressed',
        'compressed',
    )
)
def test_two_runs(tmp_dir, artifact_dir, compressed):
    run_test(
        tmp_dir,
        artifact_dir=artifact_dir + '/first_run',
        conf_args={'compressed': compressed},
        num_files=2,
    )
    with open(tmp_dir + '/conf.ini') as conf_file:
        for line in conf_file:
            match = re.match(r'last_line = (.*)', line)
            if match is not None:
                last_line = match.group(1)
            match = re.match(r'last_request_time = (.*)', line)
            if match is not None:
                last_request_time = match.group(1)
    run_test(
        tmp_dir,
        artifact_dir=artifact_dir + '/second_run',
        conf_args={
            'last_line': last_line,
            'last_request_time': last_request_time,
            'compressed': compressed,
        },
        num_files=(3 if compressed == 'true' else 2),
    )


def test_error_response(tmp_dir):
    run_test(tmp_dir, mode=500)
