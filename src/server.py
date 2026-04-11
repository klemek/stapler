import http.server

from . import params, handler, registry


class StaplerServer:
    def __init__(self, params: params.Parameters):
        self.default_host = params.host
        self.registry = registry.Registry(params)
        self.params = params
        self.server = http.server.ThreadingHTTPServer(
            (params.bind, params.port),
            self.request_handler,
        )

    def request_handler(self, *args) -> http.server.BaseHTTPRequestHandler:
        return handler.StaplerRequestHandler(
            *args, params=self.params, registry=self.registry
        )

    def start(self):
        self.registry.load_pages()
        print(
            f"{handler.StaplerRequestHandler.server_version} serving on http://{self.default_host}:{self.server.server_port}..."
        )
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
