import http.server
import os
import logging

from . import params, handler, registry, project


class StaplerServer:
    def __init__(self, params: params.Parameters):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.params = params
        self.registry = registry.Registry(params)
        self.server = http.server.ThreadingHTTPServer(
            (params.bind, params.port),
            self.request_handler,
        )

    def request_handler(self, *args) -> http.server.BaseHTTPRequestHandler:
        return handler.RequestHandler(*args, params=self.params, registry=self.registry)

    def __init_certbot_www(self):
        os.makedirs(self.params.certbot_www, exist_ok=True)

    def __startup(self):
        self.logger.info("Starting up...")
        self.registry.load_pages()
        self.__init_certbot_www()

    def start(self):
        self.logger.info("Version %s", project.get_version())
        self.__startup()
        self.logger.info(
            "Listening on %s:%d...",
            self.server.server_address[0],
            self.server.server_port,
        )
        self.logger.info(
            "Server up and ready on http://%s",
            self.params.host,
        )
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
