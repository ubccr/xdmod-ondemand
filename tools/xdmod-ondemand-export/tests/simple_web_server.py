from http.server import BaseHTTPRequestHandler, HTTPServer


class Server(BaseHTTPRequestHandler):
    def do_POST(self):
        authorization = self.headers.get('Authorization')
        if (
            authorization != 'Bearer 1.10fe91043025e974f798d8ddc320ac794eacefd'
            + '43c609c7eb42401bccfccc8ae'
        ):
            self.send_response(401)
            self.send_header('Content-type', 'application/json')
            self.wfile.write(b'{"message":"Invalid credentials."}')
            return
        global output_dir, request_index, mode
        file_path = output_dir + '/access.log.' + str(request_index)
        print('DEBUG:simple_web_server:Writing to ' + file_path)
        with open(file_path, 'w') as file:
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
        request_index += 1


def run(dir_, num_requests, mode_=200):
    global output_dir, request_index, mode
    output_dir = dir_
    mode = mode_
    request_index = 0
    server = HTTPServer(('localhost', 1234), Server)
    for _ in range(0, num_requests):
        server.handle_request()
