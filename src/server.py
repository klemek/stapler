import http.server
import http

from . import project, params


class _StaplerRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/2.0"
    server_version = "StaplerServer/" + project.get_version()

    def __init__(self, *args, params: params.Parameters, **kwargs):
        self.default_host = params.host
        super().__init__(*args, directory=params.data_dir, **kwargs)

    def list_directory(self, *_, **__):
        """Disable default directory listing"""
        self.send_error(http.HTTPStatus.NOT_FOUND, "File not found")

    def do_GET(self):
        if self.path == "/" and self.get_host() == self.default_host:
            self.server_index()
            return
        super().do_GET()

    def get_host(self) -> str:
        return self.headers["Host"].split(":")[0]

    def server_index(self):
        self.send_basic_body(self.server_version)

    def send_basic_body(self, body: str, content_type: str = "text/plain"):
        encoded: bytes = body.encode()
        self.send_response(http.HTTPStatus.OK)
        self.send_header("Content-type", f"{content_type}; charset=UTF-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class StaplerServer:
    def __init__(self, params: params.Parameters):
        self.default_host = params.host
        self.server = http.server.ThreadingHTTPServer(
            (params.bind, params.port),
            lambda req, client, server: _StaplerRequestHandler(
                req, client, server, params=params
            ),
        )

    def start(self):
        print(
            f"{_StaplerRequestHandler.server_version} serving on http://{self.default_host}:{self.server.server_port}..."
        )
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
