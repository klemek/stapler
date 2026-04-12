import http
import http.server
import io
import logging
import os
import pathlib
import re
import tarfile
import typing

from . import data_dir, logs, project

if typing.TYPE_CHECKING:
    from . import params, registry


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/2.0"
    server_version = "StaplerServer/" + project.get_version()
    CERTBOT_CHALLENGE_PATH = "/.well-known/acme-challenge"
    PATH_REGEX = re.compile(r"^\/([\w-]+)\/")

    @typing.override
    def __init__(
        self,
        *args: typing.Any,
        params: params.Parameters,
        registry: registry.Registry,
        **kwargs: dict[str, typing.Any],
    ) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.default_host = params.host
        self.token = params.token
        self.data_dir = data_dir.DataDir(params.data_dir)
        self.max_size_bytes = params.max_size_bytes
        self.registry = registry
        self.certbot_www = os.path.realpath(params.certbot_www)
        self.out_size = 0
        super().__init__(*args, directory=params.data_dir, **kwargs)

    @typing.override
    def do_HEAD(self) -> None:
        self.__pre_log_request()
        super().do_HEAD()

    @typing.override
    def do_GET(self) -> None:
        self.__pre_log_request()
        if self.path == "/" and self.__get_host() == self.default_host:
            return self.__server_index()
        super().do_GET()
        return None

    def do_PUT(self) -> None:
        self.__pre_log_request()
        if (sub_path := self.__check_update_request()) is None:
            return None
        if (content_length := self.__get_length()) == 0:
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
        self.__send_status_only(
            http.HTTPStatus.CREATED,
            f"Resource /{sub_path}/ updated",
        )
        if self.headers["X-Host"] is not None:
            self.registry.set_host(sub_path, self.headers["X-Host"])
        self.registry.add(sub_path)
        return None

    def do_DELETE(self) -> None:
        self.__pre_log_request()
        if (sub_path := self.__check_update_request()) is None:
            return None
        if not self.data_dir.exists(sub_path):
            self.send_error(http.HTTPStatus.NOT_FOUND, "Not found")
            return None
        try:
            self.data_dir.remove(sub_path)
        except Exception as e:
            return self.send_error(http.HTTPStatus.INTERNAL_SERVER_ERROR, str(e))
        self.__send_status_only(
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
            return self.certbot_www + path.removeprefix(self.CERTBOT_CHALLENGE_PATH)
        if (page := self.registry.get_from_host(self.__get_host())) is not None:
            path = f"/{page.path}" + path
        path = super().translate_path(path)
        if self.__get_subpath() is None:  # not a valid path
            return ""
        if pathlib.Path(path).name.startswith("."):  # hidden files
            return ""
        return path

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
            self.__send_basic_body(
                f"{code} {message}\n{explain}\n{self.server_version}\n",
                code=code,
                message=message,
            )
        else:
            self.__send_status_only(code, message)

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
        args = (code, self.address_string(), self.__get_host(), self.requestline)
        fmt = "→ %s - %s - %s - %s"
        if size != "":
            args = (*args, size)
            fmt += " - %s"
        self.logger.info(fmt, *args)

    def __pre_log_request(self) -> None:
        args = ("...", self.address_string(), self.__get_host(), self.requestline)
        fmt = "← %s - %s - %s - %s"
        if (size := self.__get_length()) > 0:
            args = (*args, size)
            fmt += " - %s"
        self.logger.debug(fmt, *args)

    def __check_update_request(self) -> str | None:
        if self.headers["X-Token"] != self.token:
            self.send_error(http.HTTPStatus.UNAUTHORIZED, "Invalid token")
            return None
        if (sub_path := self.__get_subpath_full()) is None:
            self.send_error(http.HTTPStatus.BAD_REQUEST, "Invalid path")
            return None
        return sub_path

    def __get_subpath(self) -> str | None:
        if (match := self.PATH_REGEX.match(self.path)) is not None:
            return match.group(1)
        return None

    def __get_subpath_full(self) -> str | None:
        if (match := self.PATH_REGEX.fullmatch(self.path)) is not None:
            return match.group(1)
        return None

    def __get_host(self) -> str:
        if self.headers["Host"] is None:
            return self.default_host
        return self.headers["Host"]

    def __get_length(self) -> int:
        if not self.headers["Content-Length"]:
            return 0
        return int(self.headers["Content-Length"])

    def __server_index(self) -> None:
        self.__send_basic_body(self.server_version + "\n")

    def __send_basic_body(
        self,
        body: str,
        content_type: str = "text/plain",
        code: int = http.HTTPStatus.OK,
        message: str | None = None,
    ) -> None:
        encoded: bytes = body.encode()
        self.out_size = len(encoded)
        self.send_response(code, message)
        self.send_header("Content-type", f"{content_type}; charset=UTF-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def __send_status_only(self, code: int, message: str | None = None) -> None:
        self.send_response(code, message)
        self.send_header("Content-Length", "0")
        self.end_headers()
