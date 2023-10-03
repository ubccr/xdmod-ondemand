import apachelogs.errors
import glob
import http.client
import multiprocessing
import os
import pytest
import re
import requests.exceptions
import shutil
import simple_web_server
import tempfile
import urllib3.exceptions
from xdmod_ondemand_export import LogPoster


DESTINATION_URL = 'http://localhost:1234'
API_TOKEN_FOR_TEST_SERVER_ONLY = (
    '1.10fe91043025e974f798d8ddc320ac794eacefd43c609c7eb42401bccfccc8ae'
)
ARTIFACTS_DIR = os.path.dirname(os.path.realpath(__file__)) + '/artifacts'
ROOT_DIR = os.path.expanduser('~/xdmod-ondemand-export')
PACKAGES_DIR = glob.glob(ROOT_DIR + '/env/lib/python3.*/site-packages')[0]
PACKAGE_DIR = PACKAGES_DIR + '/xdmod_ondemand_export'
BASE_CONF_PATH = PACKAGE_DIR + '/conf.ini'
SAMPLE_JSON_PATH = ARTIFACTS_DIR + '/sample.json'
DEFAULT_FILE_PERMISSIONS = {
    '-c': 0o0400,
    '-j': 0o0600,
    '-t': 0o0400,
}


@pytest.fixture()
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def set_token(path, token, file_permissions):
    with open(path, 'w') as f:
        f.write(token)
    os.chmod(path, file_permissions)


def update_conf_file(
    source_path,
    destination_path,
    args,
    destination_permissions,
):
    with open(source_path, 'rt') as base_file:
        old_umask = os.umask(0o077)
        with open(destination_path, 'wt') as file_:
            for line in base_file:
                line = update_conf_file_line(line, args)
                file_.write(line)
        os.umask(old_umask)
    os.chmod(destination_path, destination_permissions)


def update_conf_file_line(line, args):
    for arg in args:
        line = re.sub(
            r'^' + arg + r'\s*=.*',
            arg + ' = ' + args[arg],
            line,
        )
    return line


def run(tmp_dir, script_args, web_server_args, api_token):
    web_server_process = multiprocessing.Process(
        target=simple_web_server.run,
        args=web_server_args,
    )
    web_server_process.daemon = True
    web_server_process.start()
    try:
        script_args_list = []
        for script_arg in script_args:
            script_args_list.append(script_arg)
            if script_args[script_arg] is not None:
                script_args_list.append(script_args[script_arg])
        LogPoster(script_args_list)
    except Exception as e:
        web_server_process.terminate()
        raise e
    finally:
        web_server_process.join()


def validate_output(path_to_actual, path_to_expected):
    with open(path_to_actual) as actual_file:
        actual_file_contents = read_and_substitute_vars(actual_file)
        with open(path_to_expected) as expected_file:
            expected_file_contents = read_and_substitute_vars(expected_file)
            assert expected_file_contents == actual_file_contents


def read_and_substitute_vars(file):
    contents = file.read()
    contents_with_vars_substituted = contents.replace(
        '${ARTIFACTS_DIR}',
        ARTIFACTS_DIR,
    )
    return contents_with_vars_substituted


def run_test(
    tmp_dir,
    artifact_dir='default',
    conf_args={},
    input_json_path=None,
    output_json_path=None,
    additional_script_args={},
    api_token=API_TOKEN_FOR_TEST_SERVER_ONLY,
    num_files=1,
    mode=200,
    file_permissions=DEFAULT_FILE_PERMISSIONS,
):
    artifact_dir_path = ARTIFACTS_DIR + '/' + artifact_dir
    inputs_dir = artifact_dir_path + '/inputs'
    expected_output_path_prefix = artifact_dir_path + '/outputs/access.log.'
    destination_conf_path = tmp_dir + '/conf.ini'
    if input_json_path is None:
        input_json_path = tmp_dir + '/input.json'
        with open(input_json_path, 'w') as json_file:
            json_file.write('')
    elif input_json_path != tmp_dir + '/input.json':
        shutil.copy(
            input_json_path,
            tmp_dir + '/input.json',
        )
    os.chmod(tmp_dir + '/input.json', file_permissions['-j'])
    update_conf_file(
        BASE_CONF_PATH,
        destination_conf_path,
        {
            **conf_args,
            **{
                'url': (
                    conf_args['url']
                    if 'url' in conf_args
                    else DESTINATION_URL
                ),
                'dir': conf_args['dir'] if 'dir' in conf_args else inputs_dir,
            },
        },
        file_permissions['-c'],
    )
    script_args = {
        '-c': destination_conf_path,
        '-j': tmp_dir + '/input.json',
        '-t': tmp_dir + '/.token',
        '-l': 'DEBUG',
    }
    for arg in additional_script_args:
        script_args[arg] = additional_script_args[arg]
    web_server_args = (tmp_dir, num_files, mode)
    try:
        set_token(tmp_dir + '/.token', api_token, file_permissions['-t'])
        run(tmp_dir, script_args, web_server_args, api_token)
    except RuntimeError as e:
        if mode != 200:
            assert str(e) == 'Server returned ' + str(mode)
        else:  # pragma: no cover
            raise e
    for i in range(0, num_files):
        validate_output(
            tmp_dir + '/access.log.' + str(i),
            expected_output_path_prefix + str(i),
        )
    if output_json_path is not None:
        validate_output(tmp_dir + '/input.json', output_json_path)


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
    run_test(
        tmp_dir,
        artifact_dir=nickname + '_logformat',
        conf_args={'format': logformat},
    )


def test_compressed(tmp_dir):
    run_test(
        tmp_dir,
        artifact_dir='compressed',
    )


@pytest.mark.parametrize(
    'log_level, in_caplog, not_in_caplog',
    [
        ('DEBUG', ('DEBUG', 'INFO'), ()),
        ('INFO', ('INFO',), ('DEBUG',)),
        ('WARNING', (), ('DEBUG', 'INFO')),
        ('ERROR', (), ('DEBUG', 'INFO', 'WARNING')),
    ],
    ids=('DEBUG', 'INFO', 'WARNING', 'ERROR'),
)
def test_log_level(tmp_dir, caplog, log_level, in_caplog, not_in_caplog):
    run_test(tmp_dir, additional_script_args={'-l': log_level})
    for entry in in_caplog:
        assert entry in caplog.text
    for entry in not_in_caplog:
        assert entry not in caplog.text


@pytest.mark.parametrize(
    'api_token',
    [
        '',
        'asdf',
        '1.12345678901234567890123456789',
        '1.12345678901234567890123456789012345678901234567890123456789012345',
    ],
    ids=('empty', 'malformed', 'short', 'long'),
)
def test_malformed_api_token(tmp_dir, api_token):
    with pytest.raises(
        ValueError,
        match='API token is malformed.',
    ):
        run_test(tmp_dir, api_token=api_token)


def test_invalid_api_token(tmp_dir):
    with pytest.raises(
        (
            http.client.BadStatusLine,
            requests.exceptions.ConnectionError,
        ),
        match='Invalid credentials.',
    ):
        run_test(
            tmp_dir,
            api_token=(
                '1.12345678901234567890123456789012345678901234567890'
                + '12345678901234'
            ),
        )


@pytest.mark.parametrize(
    'conf_args, artifact_dir, exception_class, match',
    [
        (
            {'url': 'asdf'},
            'default',
            requests.exceptions.MissingSchema,
            "Invalid URL 'asdf': No scheme supplied."
        ),
        (
            {'url': 'http://asdf'},
            'default',
            (
                requests.exceptions.ConnectionError,
                urllib3.exceptions.NewConnectionError,
            ),
            '\\[Errno -2\\] Name or service not known',
        ),
        (
            {'dir': 'asdf'},
            'default',
            FileNotFoundError,
            "No such directory: 'asdf'",
        ),
        (
            {'filename_pattern': ''},
            'default',
            IsADirectoryError,
            'Is a directory',
        ),
        (
            {'format': '%1'},
            'default',
            apachelogs.errors.InvalidDirectiveError,
            "Invalid log format directive at index 0 of '%1'",
        ),
    ],
    ids=(
        'url_no_scheme',
        'url_unknown_service',
        'dir',
        'filename_pattern',
        'format',
    )
)
def test_invalid_conf_property(
    tmp_dir,
    conf_args,
    artifact_dir,
    exception_class,
    match,
):
    with pytest.raises(exception_class, match=match):
        run_test(
            tmp_dir,
            artifact_dir=artifact_dir,
            conf_args=conf_args,
            # Make sure the JSON is unchanged.
            input_json_path=SAMPLE_JSON_PATH,
            output_json_path=SAMPLE_JSON_PATH,
        )


def test_no_files_to_process(tmp_dir, caplog):
    run_test(tmp_dir, conf_args={'filename_pattern': 'asdf'}, num_files=0)
    assert 'No log files to process.' in caplog.text


@pytest.mark.parametrize(
    'artifact_dir',
    [
        'some_old_some_new',
        'some_old_some_new_compressed',
    ],
    ids=(
        'uncompressed',
        'compressed',
    )
)
def test_some_old_some_new(tmp_dir, artifact_dir):
    artifact_dir_path = ARTIFACTS_DIR + '/' + artifact_dir
    run_test(
        tmp_dir,
        artifact_dir=artifact_dir,
        input_json_path=artifact_dir_path + '/inputs/input.json',
        output_json_path=artifact_dir_path + '/outputs/output.json',
        num_files=2,
    )


def test_check_config(tmp_dir, caplog):
    run_test(
        tmp_dir,
        additional_script_args={'--check-config': None},
        num_files=0,
    )
    assert (
        'Finished checking config, not parsing or POSTing any files.'
    ) in caplog.text


@pytest.mark.parametrize(
    'artifact_dir, second_run_num_files',
    [
        ('two_runs', 2),
        ('two_runs_compressed', 2),
        ('two_runs_first_all_unauthenticated', 2),
        ('two_runs_file_size_changes', 3),
    ],
    ids=(
        'uncompressed',
        'compressed',
        'first_all_unauthenticated',
        'file_size_changes',
    )
)
def test_two_runs(tmp_dir, artifact_dir, second_run_num_files):
    artifact_dir_path = ARTIFACTS_DIR + '/' + artifact_dir + '/first_run'
    run_test(
        tmp_dir,
        artifact_dir=artifact_dir + '/first_run',
        output_json_path=artifact_dir_path + '/outputs/output.json',
        num_files=2,
    )
    artifact_dir_path = ARTIFACTS_DIR + '/' + artifact_dir + '/second_run'
    run_test(
        tmp_dir,
        artifact_dir=artifact_dir + '/second_run',
        # Make sure to use the same JSON file for both runs:
        input_json_path=tmp_dir + '/input.json',
        output_json_path=artifact_dir_path + '/outputs/output.json',
        num_files=second_run_num_files,
    )


def test_error_response(tmp_dir):
    run_test(tmp_dir, mode=500)


def test_empty_file(tmp_dir):
    run_test(tmp_dir, artifact_dir='empty_file')


def test_empty_lines(tmp_dir, caplog):
    run_test(tmp_dir, artifact_dir='empty_lines')
    assert 'Skipped 3 invalid entries' in caplog.text


def test_invalid_compressed_lines(tmp_dir, caplog):
    run_test(
        tmp_dir,
        artifact_dir='invalid_compressed_lines',
    )
    assert 'Skipped 3 invalid entries' in caplog.text


def test_invalid_compressed_file(tmp_dir, caplog):
    run_test(
        tmp_dir,
        artifact_dir='invalid_compressed_file',
        num_files=2,
    )
    assert 'Skipped 1 invalid entry' in caplog.text
    assert 'Skipped 2 invalid entries' in caplog.text


def test_delete_old_json(tmp_dir):
    artifact_dir = 'delete_old_json'
    artifact_dir_path = ARTIFACTS_DIR + '/' + artifact_dir
    run_test(
        tmp_dir,
        artifact_dir=artifact_dir,
        input_json_path=artifact_dir_path + '/inputs/input.json',
        output_json_path=artifact_dir_path + '/outputs/output.json',
        num_files=1,
    )


@pytest.mark.parametrize('script_arg', ['-c', '-j', '-t'])
def test_file_not_found(tmp_dir, script_arg):
    with pytest.raises(
        FileNotFoundError,
        match='\\[Errno 2\\] No such file or directory:'
        + " 'asdf'",
    ):
        run_test(tmp_dir, additional_script_args={script_arg: 'asdf'})


def test_invalid_script_args(tmp_dir):
    with pytest.raises(SystemExit):
        run_test(tmp_dir, additional_script_args={'asdf': None}, num_files=0)


@pytest.mark.parametrize(
    'script_arg, file_name, expected_file_permissions',
    [
        ('-c', 'conf.ini', '400'),
        ('-t', '.token', '400'),
        ('-j', 'input.json', '600'),
    ],
    ids=('conf', 'token', 'json'),
)
def test_file_permissions_warning(
    tmp_dir,
    caplog,
    script_arg,
    file_name,
    expected_file_permissions,
):
    file_permissions = DEFAULT_FILE_PERMISSIONS.copy()
    file_permissions[script_arg] = 0o777
    run_test(tmp_dir, file_permissions=file_permissions)
    assert (
        'File permissions on ' + tmp_dir + '/' + file_name + ' not set to '
        + expected_file_permissions + '.'
    ) in caplog.text
