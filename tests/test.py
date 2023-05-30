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
        input_file_dir = TESTS_DIR + '/artifacts/common_logformat'
        output_file_path = tmp_dir + '/output.log'
        conf_path = tmp_dir + '/conf.ini'
        with open(BASE_CONF_PATH, 'rt') as base_conf_file:
            with open(conf_path, 'wt') as conf_file:
                for line in base_conf_file:
                    line = re.sub(
                        r'^dir =.*',
                        'dir = ' + input_file_dir,
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
                (output_file_path,),
                1,
            ),
        )
        server_thread.start()
        subprocess.run((SCRIPT_PATH, '-c', conf_path, '-l', 'DEBUG'))
        server_thread.join()
        assert filecmp.cmp(output_file_path, input_file_dir + '/access.log')
