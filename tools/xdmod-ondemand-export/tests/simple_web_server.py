from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


output_dir = None
request_index = None
mode = None


class Server(BaseHTTPRequestHandler):
    def do_POST(self):
        global request_index
        authorization = self.headers.get('Authorization')
        if (
            authorization != 'Bearer 1.10fe91043025e974f798d8ddc320ac794eacefd'
            + '43c609c7eb42401bccfccc8ae'
        ):
            self.send_response(401)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"message":"Invalid credentials."}')
            return
        query_params = parse_qs(urlparse(self.path).query)
        is_app_list = (
            'type' in query_params and 'app-list' == query_params['type'][0]
        )
        file_path = output_dir + (
            '/app-list.json'
            if is_app_list
            else '/access.log.' + str(request_index)
        )
        print('DEBUG:simple_web_server:Writing to ' + file_path)
        with open(file_path, 'w') as file:
            if is_app_list:
                length = int(self.headers.get('content-length'))
                content = self.rfile.read(length)
                file.write(content.strip().decode('utf-8'))
            else:
                while True:
                    length = self.rfile.readline().strip().decode('utf-8')
                    if length == '0':
                        break
                    bytes_ = self.rfile.readline().strip().decode('utf-8')
                    file.write(bytes_)
                    file.write('\n')
                    self.rfile.readline().strip().decode('utf-8')
        self.send_response(mode)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"message":"success"}')
        if not is_app_list:
            request_index += 1


def run(dir_, num_requests, mode_=200):
    global output_dir, request_index, mode
    output_dir = dir_
    request_index = 0
    mode = mode_
    server = HTTPServer(('localhost', 1234), Server)
    for _ in range(0, num_requests):
        server.handle_request()
