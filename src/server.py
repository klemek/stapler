import http.server
import os

from . import params, handler, registry, project


class StaplerServer:
    def __init__(self, params: params.Parameters):
        self.params = params
        self.registry = registry.Registry(params)
        self.server = http.server.ThreadingHTTPServer(
            (params.bind, params.port),
            self.request_handler,
        )

    def request_handler(self, *args) -> http.server.BaseHTTPRequestHandler:
        return handler.StaplerRequestHandler(
            *args, params=self.params, registry=self.registry
        )

    def __repr__(self):
        return f"StaplerServer ({project.get_version()})"

    def __init_certbot_www(self):
        os.makedirs(self.params.certbot_www, exist_ok=True)

    def __startup(self):
        print(f"{self}: starting up...")
        self.registry.load_pages()
        self.__init_certbot_www()

    def start(self):
        self.__startup()
        print(
            f"{self}: serving on http://{self.params.host}:{self.server.server_port}..."
        )
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
