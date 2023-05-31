from http.server import BaseHTTPRequestHandler, HTTPServer


class Server(BaseHTTPRequestHandler):
    def do_POST(self):
        authorization = self.headers.get('Authorization')
        if authorization != 'Bearer abcd':
            self.send_response(401)
            self.send_header('Content-type', 'text/html')
            self.wfile.write(b'Authentication failed.')
            return
        global file_paths, request_index
        file_path = file_paths[request_index]
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
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'OK')
        request_index += 1


def run(paths, num_requests):
    global file_paths, request_index
    file_paths = paths
    request_index = 0
    server = HTTPServer(('localhost', 1234), Server)
    for _ in range(0, num_requests):
        server.handle_request()
