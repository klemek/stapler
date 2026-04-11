import http.server

from . import params, handler


class StaplerServer:
    def __init__(self, params: params.Parameters):
        self.default_host = params.host
        self.server = http.server.ThreadingHTTPServer(
            (params.bind, params.port),
            lambda req, client, server: handler.StaplerRequestHandler(
                req, client, server, params=params
            ),
        )

    def start(self):
        print(
            f"{handler.StaplerRequestHandler.server_version} serving on http://{self.default_host}:{self.server.server_port}..."
        )
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
