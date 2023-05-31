import filecmp
import os
import re
import simple_web_server
import shutil
import subprocess
import tempfile
import threading

TESTS_DIR = '/root/post_ood_logs_to_access_mms/tests'
PACKAGE_DIR = '/root/post_ood_logs_to_access_mms/env/lib/python3.6/site-packages/post_ood_logs_to_access_mms'
SCRIPT_PATH = PACKAGE_DIR + '/post_ood_logs_to_access_mms.sh'
BASE_CONF_PATH = PACKAGE_DIR + '/conf.ini'

def test_common_logformat():
    with tempfile.TemporaryDirectory() as tmp_dir:
        artifacts_dir = TESTS_DIR + '/artifacts/common_logformat'
        inputs_dir = artifacts_dir + '/inputs'
        expected_output_file_path = artifacts_dir + '/outputs/access.log'
        actual_output_file_path = tmp_dir + '/access.log'
        conf_path = tmp_dir + '/conf.ini'
        with open(BASE_CONF_PATH, 'rt') as base_conf_file:
            with open(conf_path, 'wt') as conf_file:
                for line in base_conf_file:
                    line = re.sub(
                        r'^dir =.*',
                        'dir = ' + inputs_dir,
                        line,
                    )
                    line = re.sub(
                        r'^format =.*',
                        'format = %h %l %u %t "%r" %>s %b',
                        line,
                    )
                    conf_file.write(line)
        server_thread = threading.Thread(
            target=simple_web_server.run,
            args=(
                (actual_output_file_path,),
                1,
            ),
        )
        server_thread.start()
        subprocess.run((SCRIPT_PATH, '-c', conf_path, '-l', 'DEBUG'))
        server_thread.join()
        with open(actual_output_file_path) as actual_output_file:
            actual_output_file_contents = actual_output_file.read()
            with open(expected_output_file_path) as expected_output_file:
                expected_output_file_contents = expected_output_file.read()
                assert filecmp.cmp(
                    actual_output_file_path,
                    expected_output_file_path,
                ), (
                    'files differ:\nactual:\n' + actual_output_file_contents
                    + 'expected:\n' + expected_output_file_contents
                )
