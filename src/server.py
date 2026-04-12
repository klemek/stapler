import contextlib
import http.server
import logging
import typing

from . import cert, handler, project, registry

if typing.TYPE_CHECKING:
    from . import params


class StaplerServer:
    def __init__(self, params: params.Parameters) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.params = params
        self.registry = registry.Registry(params)
        self.cert_manager = cert.CertManager(params)
        self.server = http.server.ThreadingHTTPServer(
            (params.bind, params.port),
            self.request_handler,
        )

    def request_handler(self, *args: typing.Any) -> http.server.BaseHTTPRequestHandler:
        return handler.RequestHandler(*args, params=self.params, registry=self.registry)

    def __startup(self) -> None:
        self.logger.info("Starting up...")
        self.registry.load_pages()
        if self.params.with_certificates:
            self.cert_manager.init([self.params.host, *self.registry.get_hosts()])

    def start(self) -> None:
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
        with contextlib.suppress(KeyboardInterrupt):
            self.server.serve_forever()
