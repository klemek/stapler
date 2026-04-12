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
        self.default_host = params.host.split(":", maxsplit=2)[0]

    def request_handler(self, *args: typing.Any) -> http.server.BaseHTTPRequestHandler:
        return handler.RequestHandler(
            *args,
            params=self.params,
            registry=self.registry,
            cert_manager=self.cert_manager,
        )

    def __get_all_hosts(self) -> list[str]:
        return [self.default_host, *self.registry.get_hosts()]

    def __startup(self) -> None:
        self.logger.info("Starting up...")
        self.registry.load_pages()
        if self.params.with_certificates:
            self.cert_manager.init(self.__get_all_hosts())
        if not len(self.params.token):
            self.logger.warning("No token provided update requests will fail")

    def __create_https_context(self, server: http.server.HTTPServer) -> bool:
        https = False
        if (
            context := self.cert_manager.get_https_context(self.default_host)
        ) is not None:
            https = True
            server.socket = context.wrap_socket(server.socket, server_side=True)
        return https

    def run(self) -> int:
        self.logger.info("Version %s", project.get_version())
        self.__startup()
        server = http.server.ThreadingHTTPServer(
            (self.params.bind, self.params.port),
            self.request_handler,
        )
        https = self.params.https and self.__create_https_context(server)
        self.logger.info(
            "Listening on %s:%d...",
            server.server_address[0],
            server.server_port,
        )
        self.logger.info(
            "Server up and ready on %s://%s",
            "https" if https else "http",
            self.params.host,
        )
        with contextlib.suppress(KeyboardInterrupt):
            server.serve_forever()
        return 0

    def renew(self) -> int:
        self.logger.info("Starting up...")
        if not self.params.with_certificates:
            self.logger.warning("Cannot renew without certificates")
            return 1
        self.registry.load_pages()
        for host in self.__get_all_hosts():
            self.cert_manager.create_or_update(host)
        return 0
