import abc
import http
import http.server
import io
import logging
import os
import pathlib
import re
import tarfile
import typing

from . import STAPLER_ASCII, data_dir, logs, project

if typing.TYPE_CHECKING:
    from . import cert_manager, params, registry, token_manager


class _BaseHandler(abc.ABC, http.server.BaseHTTPRequestHandler):
    @typing.override
    def __init__(
        self,
        *args: typing.Any,
        params: params.Parameters,
        **kwargs: dict[str, typing.Any],
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.default_host = params.host.split(":", maxsplit=2)[0]
        self.out_size = 0
        super().__init__(*args, **kwargs)

    @typing.override
    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        shortmsg, longmsg = self.responses[code]
        if message is None:
            message = shortmsg
        if explain is None:
            explain = longmsg
        if "Accept" not in self.headers["Accept"] or "text/" in self.headers["Accept"]:
            self.send_basic_body(
                f"{code} {message}\n{explain}\n\n{self._server_signature()}",
                code=code,
                message=message,
            )
        else:
            self.send_status_only(code, message)

    @typing.override
    def log_message(self, format: str, *args: typing.Any) -> None:
        fmt = "%s - " + format
        self.logger.info(fmt, self.address_string(), *args)

    @typing.override
    def log_error(self, format: str, *args: typing.Any) -> None:
        fmt = "%s - " + format
        self.logger.error(fmt, self.address_string(), *args)

    @typing.override
    def log_request(self, code: str = "?", size: str = "-") -> None:  # ty:ignore[invalid-method-override]
        if isinstance(code, http.HTTPStatus):
            color = logs.TermColor.RED
            if 100 <= code < 200:
                color = logs.TermColor.CYAN
            if 200 <= code < 300:
                color = logs.TermColor.GREEN
            elif 300 <= code < 400:
                color = logs.TermColor.BLUE
            elif 400 <= code < 500:
                color = logs.TermColor.YELLOW
            code = color + str(code.value) + logs.TermColor.RESET
        if size == "" and self.out_size > 0:
            size = str(self.out_size)
        args = (code, self.address_string(), self._get_host(), self.requestline)
        fmt = "→ %s - %s - %s - %s"
        if size != "":
            args = (*args, size)
            fmt += " - %s"
        self.logger.info(fmt, *args)

    def send_basic_body(
        self,
        body: str,
        content_type: str = "text/plain",
        code: int = http.HTTPStatus.OK,
        message: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        encoded: bytes = body.encode()
        self.out_size = len(encoded)
        self.send_response(code, message)
        self.send_header("Content-type", f"{content_type}; charset=UTF-8")
        self.send_header("Content-Length", str(len(encoded)))
        if headers is not None:
            for header, value in headers.items():
                self.send_header(header, value)
        self.end_headers()
        self.wfile.write(encoded)
        self.close_connection = True

    def send_status_only(
        self,
        code: int,
        message: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(code, message)
        self.send_header("Content-Length", "0")
        if headers is not None:
            for header, value in headers.items():
                self.send_header(header, value)
        self.end_headers()
        self.close_connection = True

    def _get_host(self) -> str:
        if self.headers["Host"] is None:
            return self.default_host
        return self.headers["Host"].split(":", maxsplit=2)[0]

    def _get_length(self) -> int:
        if not self.headers["Content-Length"]:
            return 0
        return int(self.headers["Content-Length"])

    def _pre_log_request(self) -> None:
        args = ("...", self.address_string(), self._get_host(), self.requestline)
        fmt = "← %s - %s - %s - %s"
        if (size := self._get_length()) > 0:
            args = (*args, size)
            fmt += " - %s"
        self.logger.debug(fmt, *args)

    def _server_signature(self) -> str:
        return self.server_version + "\n\n" + STAPLER_ASCII + "\n"


class RequestHandler(http.server.SimpleHTTPRequestHandler, _BaseHandler):
    protocol_version = "HTTP/2.0"
    server_version = "StaplerServer/" + project.get_version()
    CERTBOT_CHALLENGE_PATH = "/.well-known/acme-challenge"
    PATH_REGEX = re.compile(r"^\/([\w-]+)\/")
    HOST_PART_REGEX = re.compile(r"^([a-zA-Z0-9]|[a-zA-Z0-9]*[a-zA-Z0-9][a-zA-Z0-9])$")
    AUTHORIZED_PATHS: typing.ClassVar[list[str]] = ["/favicon.ico"]

    @typing.override
    def __init__(
        self,
        *args: typing.Any,
        params: params.Parameters,
        registry: registry.Registry,
        cert_manager: cert_manager.CertManager,
        token_manager: token_manager.TokenManager,
        **kwargs: dict[str, typing.Any],
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.token_manager = token_manager
        self.data_dir = data_dir.DataDir(params.data_dir)
        self.max_size_bytes = params.max_size_bytes
        self.registry = registry
        self.cert_manager = cert_manager
        self.certbot_www = os.path.realpath(params.certbot_www)
        super().__init__(*args, directory=params.data_dir, **kwargs, params=params)  # ty:ignore[unknown-argument]

    @typing.override
    def do_HEAD(self) -> None:
        self._pre_log_request()
        super().do_HEAD()

    @typing.override
    def do_GET(self) -> None:
        self._pre_log_request()
        if self.path == "/" and self._get_host() == self.default_host:
            return self.send_basic_body(self._server_signature())
        super().do_GET()
        return None

    def do_PUT(self) -> None:
        self._pre_log_request()
        if (sub_path := self.__check_update_request()) is None:
            return None
        host: str | None = self.headers["X-Host"]
        if host is not None and not self.__valid_host(host):
            return self.send_error(
                http.HTTPStatus.BAD_REQUEST, "Invalid requested host"
            )
        if (content_length := self._get_length()) == 0:
            return self.send_error(http.HTTPStatus.LENGTH_REQUIRED, "No body found")
        if content_length > self.max_size_bytes:
            return self.send_error(
                http.HTTPStatus.CONTENT_TOO_LARGE,
                "Archive too large",
            )
        try:
            file_bytes = io.BytesIO(self.rfile.read(content_length))
            self.data_dir.extract_tar_bytes(sub_path, file_bytes)
        except tarfile.TarError:
            return self.send_error(http.HTTPStatus.BAD_REQUEST, "Invalid tar archive")
        except Exception as e:
            return self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
        self.send_status_only(
            http.HTTPStatus.CREATED,
            f"Resource /{sub_path}/ updated",
        )
        self.registry.add(sub_path)
        self.token_manager.set_token(self.headers["X-Token"], sub_path)
        if host is not None and self.cert_manager.create_or_update(host):
            self.registry.set_host(sub_path, host)
        return None

    def do_DELETE(self) -> None:
        self._pre_log_request()
        if (sub_path := self.__check_update_request()) is None:
            return None
        if not self.data_dir.exists(sub_path):
            self.send_error(http.HTTPStatus.NOT_FOUND, "Not found")
            return None
        try:
            self.data_dir.remove(sub_path)
        except Exception as e:
            return self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
        self.send_status_only(
            http.HTTPStatus.NO_CONTENT,
            f"Resource /{sub_path}/ removed",
        )
        self.registry.remove(sub_path)
        return None

    @typing.override
    def list_directory(self, *_: typing.Any, **__: typing.Any) -> None:
        """Disable default directory listing."""
        self.send_error(http.HTTPStatus.NOT_FOUND, "File not found")

    @typing.override
    def translate_path(self, path: str) -> str:
        if path.startswith(self.CERTBOT_CHALLENGE_PATH):
            return self.certbot_www + path
        if (page := self.registry.get_from_host(host := self._get_host())) is not None:
            path = f"/{page.path}" + path
        elif host != self.default_host:
            return ""
        elif (
            path not in self.AUTHORIZED_PATHS and self.__get_subpath(path) is None
        ):  # not a valid path
            return ""
        if pathlib.Path(path).name.startswith("."):  # hidden files
            return ""
        return super().translate_path(path)

    def __check_update_request(self) -> str | None:
        if (token := self.headers["X-Token"]) is None:
            self.send_error(http.HTTPStatus.BAD_REQUEST, "No X-Token header in request")
            return None
        if not self.token_manager.is_valid(token):
            self.send_error(http.HTTPStatus.UNAUTHORIZED, "Invalid token")
            return None
        if (sub_path := self.__get_subpath_full(self.path)) is None:
            self.send_error(http.HTTPStatus.BAD_REQUEST, "Invalid path")
            return None
        if not self.token_manager.is_valid_for_path(token, sub_path):
            self.send_error(http.HTTPStatus.FORBIDDEN, "Path forbidden for this token")
            return None
        return sub_path

    def __get_subpath(self, path: str) -> str | None:
        if (match := self.PATH_REGEX.match(path)) is not None:
            return match.group(1)
        return None

    def __get_subpath_full(self, path: str) -> str | None:
        if (match := self.PATH_REGEX.fullmatch(path)) is not None:
            return match.group(1)
        return None

    def __valid_host(self, host: str) -> bool:
        return all(self.HOST_PART_REGEX.fullmatch(part) for part in host.split("."))


class UpgradeHandler(_BaseHandler):
    server_version = "StaplerUpgradeServer/" + project.get_version()

    def do_HEAD(self) -> None:
        self._pre_log_request()
        self.send_status_only(
            http.HTTPStatus.MOVED_PERMANENTLY,
            headers={"Location": f"https://{self._get_host()}{self.path}"},
        )

    def do_GET(self) -> None:
        self.do_HEAD()
