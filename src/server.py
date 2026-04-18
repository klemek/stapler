import contextlib
import http.server
import logging
import threading
import typing

from . import (
    STAPLER_ASCII,
    cert_manager,
    data_dir,
    handlers,
    project,
    registry,
    token_manager,
)

if typing.TYPE_CHECKING:
    from . import params


class StaplerServer:
    def __init__(self, params: params.Parameters) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.params = params
        self.registry = registry.Registry(params)
        self.cert_manager = cert_manager.CertManager(params)
        self.token_manager = token_manager.TokenManager(params, self.registry)
        self.data_dir = data_dir.DataDir(params.data_dir)
        self.default_host = params.host.split(":", maxsplit=2)[0]

    def __get_all_hosts(self) -> list[str]:
        return [self.default_host, *self.registry.get_hosts()]

    def __startup(self) -> None:
        self.logger.info("Starting up...")
        self.registry.load_pages()
        if self.params.with_certificates:
            self.cert_manager.init(self.__get_all_hosts())
        self.data_dir.init()
        self.token_manager.init()

    def __request_handler(  # pragma: no cover
        self, *args: typing.Any
    ) -> http.server.BaseHTTPRequestHandler:
        return handlers.RequestHandler(
            *args,
            params=self.params,
            registry=self.registry,
            cert_manager=self.cert_manager,
            token_manager=self.token_manager,
        )

    def __create_base_server(self) -> tuple[http.server.ThreadingHTTPServer, bool]:
        context = (
            self.cert_manager.get_https_context(self.default_host)
            if self.params.https
            else None
        )
        if context is not None:
            server = http.server.ThreadingHTTPServer(
                (
                    self.params.bind,
                    self.params.https_port,
                ),
                self.__request_handler,
            )
            server.socket = context.wrap_socket(server.socket, server_side=True)
        else:
            server = http.server.ThreadingHTTPServer(
                (
                    self.params.bind,
                    self.params.http_port,
                ),
                self.__request_handler,
            )
        self.logger.info(
            "Server listening on %s:%d...",
            server.server_address[0],
            server.server_port,
        )
        return server, context is not None

    def __upgrade_handler(  # pragma: no cover
        self, *args: typing.Any
    ) -> http.server.BaseHTTPRequestHandler:
        return handlers.UpgradeHandler(
            *args,
            params=self.params,
        )

    def __start_upgrade_server(self) -> http.server.ThreadingHTTPServer:
        server = http.server.ThreadingHTTPServer(
            (
                self.params.bind,
                self.params.http_port,
            ),
            self.__upgrade_handler,
        )
        self.logger.info(
            "Upgrade server listening on %s:%d...",
            server.server_address[0],
            server.server_port,
        )
        threading.Thread(target=server.serve_forever).start()
        return server

    def run(self) -> int:
        self.logger.info("Version %s", project.get_version())
        for line in STAPLER_ASCII.split("\n"):
            self.logger.debug(line.ljust(36))
        self.__startup()
        base_server, https = self.__create_base_server()
        upgrade_server = self.__start_upgrade_server() if https else None
        self.logger.info(
            "Server up and ready on %s://%s",
            "https" if https else "http",
            self.params.host,
        )
        with contextlib.suppress(KeyboardInterrupt):
            base_server.serve_forever()
        self.logger.info("Shutting down...")
        if upgrade_server is not None:
            upgrade_server.shutdown()
        return 0

    def renew(self) -> int:
        self.logger.info("Starting up...")
        if not self.params.with_certificates:
            self.logger.warning("Cannot renew without certificates")
            return 1
        self.registry.load_pages()
        self.cert_manager.init(self.__get_all_hosts())
        for host in self.__get_all_hosts():
            self.cert_manager.create_or_update(host)
        return 0

    def token(self) -> int:
        self.logger.info("Starting up...")
        self.registry.load_pages()
        self.token_manager.init()
        self.token_manager.new_token()
        return 0
