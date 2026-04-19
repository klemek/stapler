import abc
import collections
import contextlib
import http
import http.server
import io
import logging
import tarfile
import typing
import unittest.mock

from src.cert_manager import CertManager
from src.data_dir import DataDir
from src.handlers import BaseHandler, RequestHandler, UpgradeHandler
from src.page import Page
from src.params import Parameters
from src.registry import Registry
from src.token_manager import TokenManager

from . import BaseTestCase


class BaseHandlerTestCase(BaseTestCase, abc.ABC):
    @abc.abstractmethod
    def _get_handler(
        self,
        path: str = "/",
        headers: dict[str, str | None] | None = None,
        rfile: io.BufferedIOBase | None = None,
    ) -> BaseHandler:
        pass

    @contextlib.contextmanager
    def expects_status_only(
        self,
        handler: BaseHandler,
        code: int,
        message: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> typing.Iterator[None]:
        if headers is None:
            headers = {}
        send_response_mock = handler.send_response = unittest.mock.Mock()  # ty:ignore[invalid-assignment]
        send_header_mock = handler.send_header = unittest.mock.Mock()  # ty:ignore[invalid-assignment]
        end_headers_mock = handler.end_headers = unittest.mock.Mock()  # ty:ignore[invalid-assignment]
        yield
        send_response_mock.assert_called_once_with(code, message)
        send_header_mock.assert_has_calls(
            [
                unittest.mock.call("Content-Length", "0"),
            ]
            + [unittest.mock.call(header, value) for header, value in headers.items()],
            any_order=True,
        )
        end_headers_mock.assert_called_once()

    @contextlib.contextmanager
    def expects_basic_body(  # noqa: PLR0913
        self,
        handler: BaseHandler,
        body: str,
        content_type: str = "text/plain",
        code: int = http.HTTPStatus.OK,
        message: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> typing.Iterator[None]:
        if headers is None:
            headers = {}
        send_response_mock = handler.send_response = unittest.mock.Mock()  # ty:ignore[invalid-assignment]
        send_header_mock = handler.send_header = unittest.mock.Mock()  # ty:ignore[invalid-assignment]
        end_headers_mock = handler.end_headers = unittest.mock.Mock()  # ty:ignore[invalid-assignment]
        yield
        send_response_mock.assert_called_once_with(code, message)
        send_header_mock.assert_has_calls(
            [
                unittest.mock.call("Content-Length", str(len(body.encode()))),
                unittest.mock.call("Content-type", f"{content_type}; charset=UTF-8"),
            ]
            + [unittest.mock.call(header, value) for header, value in headers.items()],
            any_order=True,
        )
        end_headers_mock.assert_called_once()
        handler.wfile.seek(0)
        self.assertEqual(handler.wfile.read(), body.encode())

    @contextlib.contextmanager
    def expects_error(
        self,
        handler: BaseHandler,
        code: int,
        message: str | None = None,
    ) -> typing.Iterator[None]:
        shortmsg, _ = RequestHandler.responses[code]
        if message is None:
            message = shortmsg
        with self.expects_status_only(handler, code, message):
            yield

    @contextlib.contextmanager
    def expects_error_full(
        self,
        handler: BaseHandler,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> typing.Iterator[None]:
        shortmsg, longmsg = http.server.BaseHTTPRequestHandler.responses[code]
        if message is None:
            message = shortmsg
        if explain is None:
            explain = longmsg
        with self.expects_basic_body(
            handler,
            body=f"{code} {message}\n{explain}\n\n{handler.server_signature()}",
            code=code,
            message=message,
        ):
            yield


class TestRequestHandler(BaseHandlerTestCase):
    @typing.override
    def setUp(self) -> None:
        self.get_tmp_dir()
        self.registry = self.mock(Registry)
        self.cert_manager = self.mock(CertManager)
        self.token_manager = self.mock(TokenManager)
        self.certbot_www = self.tmp_path / "certbot_www"
        self.data_dir = self.mock(DataDir)
        super().setUp()

    def _get_handler(
        self,
        path: str = "/",
        headers: dict[str, str | None] | None = None,
        rfile: io.BufferedIOBase | None = None,
    ) -> RequestHandler:
        if headers is None:
            headers = {}
        with self.patch("http.server.BaseHTTPRequestHandler.__init__"):
            handler = RequestHandler(
                unittest.mock.MagicMock(),
                "127.0.0.1",
                unittest.mock.MagicMock(),
                params=Parameters(
                    data_dir=self.get_tmp_dir(), certbot_www=str(self.certbot_www)
                ),
                registry=self.registry,
                cert_manager=self.cert_manager,
                token_manager=self.token_manager,
            )
            handler.address_string = lambda: "127.0.0.1"  # ty:ignore[invalid-assignment]
            handler.requestline = "GET /"
            handler.path = path
            handler.request_version = "HTTP/0.9"
            handler.headers = collections.defaultdict(lambda: None, headers)  # ty:ignore[invalid-assignment]
            handler.rfile = rfile if rfile is not None else io.BytesIO()
            handler.wfile = io.BytesIO()
            handler.logger = unittest.mock.Mock(logging.Logger)
            handler.data_dir = self.data_dir
            return handler

    def test_do_head_proxy(self) -> None:
        handler = self._get_handler()
        with (
            self.patch("http.server.SimpleHTTPRequestHandler.do_HEAD"),
            self.seal_mocks(),
        ):
            handler.do_HEAD()

    def test_do_get_index(self) -> None:
        handler = self._get_handler("/")
        with (
            self.expects_basic_body(handler, handler.server_signature()),
            self.seal_mocks(),
        ):
            handler.do_GET()

    def test_do_get_proxy_on_other_path(self) -> None:
        handler = self._get_handler("/file")
        with (
            self.patch("http.server.SimpleHTTPRequestHandler.do_GET"),
            self.seal_mocks(),
        ):
            handler.do_GET()

    def test_do_get_proxy_on_other_host(self) -> None:
        handler = self._get_handler("/", {"Host": "other_host"})
        with (
            self.patch("http.server.SimpleHTTPRequestHandler.do_GET"),
            self.seal_mocks(),
        ):
            handler.do_GET()

    def test_do_put_no_token(self) -> None:
        handler = self._get_handler("/path")
        with (
            self.expects_error(
                handler, http.HTTPStatus.BAD_REQUEST, "No X-Token header in request"
            ),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_put_invalid_token(self) -> None:
        handler = self._get_handler("/path", {"X-Token": "secret"})
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], False),  # noqa: FBT003
            self.expects_error(handler, http.HTTPStatus.UNAUTHORIZED, "Invalid token"),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_put_invalid_path(self) -> None:
        handler = self._get_handler("/pa.th", {"X-Token": "secret"})
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.expects_error(handler, http.HTTPStatus.BAD_REQUEST, "Invalid path"),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_put_invalid_token_for_path(self) -> None:
        handler = self._get_handler("/path", {"X-Token": "secret"})
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                False,  # noqa: FBT003
            ),
            self.expects_error(
                handler, http.HTTPStatus.FORBIDDEN, "Path forbidden for this token"
            ),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_put_invalid_host(self) -> None:
        handler = self._get_handler(
            "/path", {"X-Token": "secret", "X-Host": "invalid_host"}
        )
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.expects_error(
                handler, http.HTTPStatus.BAD_REQUEST, "Invalid requested host"
            ),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_put_invalid_host_for_path(self) -> None:
        handler = self._get_handler(
            "/path", {"X-Token": "secret", "X-Host": "example.com"}
        )
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.mock_call(
                self.registry.get_from_host, ["example.com"], Page("other_path")
            ),
            self.expects_error(
                handler, http.HTTPStatus.FORBIDDEN, "Host already taken"
            ),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_put_no_content(self) -> None:
        handler = self._get_handler("/path", {"X-Token": "secret"})
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.expects_error(
                handler, http.HTTPStatus.LENGTH_REQUIRED, "No body found"
            ),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_put_content_too_large(self) -> None:
        handler = self._get_handler(
            "/path", {"X-Token": "secret", "Content-Length": "999999999"}
        )
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.expects_error(
                handler,
                http.HTTPStatus.CONTENT_TOO_LARGE,
                "Archive too large",
            ),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_put_tar_error(self) -> None:
        handler = self._get_handler(
            "/path", {"X-Token": "secret", "Content-Length": "1"}
        )
        handler.rfile.write(b"\0")
        self.data_dir.extract_tar_bytes.side_effect = tarfile.TarError
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.expects_error(
                handler, http.HTTPStatus.BAD_REQUEST, "Invalid tar archive"
            ),
            self.seal_mocks(),
        ):
            handler.do_PUT()
        self.data_dir.extract_tar_bytes.assert_called_once()

    def test_do_put_extract_error(self) -> None:
        handler = self._get_handler(
            "/path", {"X-Token": "secret", "Content-Length": "1"}
        )
        handler.rfile.write(b"\0")
        self.data_dir.extract_tar_bytes.side_effect = Exception
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.expects_error(handler, http.HTTPStatus.INTERNAL_SERVER_ERROR, ""),
            self.seal_mocks(),
        ):
            handler.do_PUT()
        self.data_dir.extract_tar_bytes.assert_called_once()

    def test_do_put_ok(self) -> None:
        handler = self._get_handler(
            "/path", {"X-Token": "secret", "Content-Length": "1"}
        )
        handler.rfile.write(b"\0")
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.mock_call_unchecked(self.data_dir.extract_tar_bytes),
            self.mock_call(self.registry.add, ["path"]),
            self.mock_call(self.token_manager.set_token, ["secret", "path"]),
            self.expects_status_only(
                handler, http.HTTPStatus.CREATED, "Resource /path/ updated"
            ),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_put_ok_with_host_fail_init(self) -> None:
        handler = self._get_handler(
            "/path",
            {"X-Token": "secret", "Content-Length": "1", "X-Host": "example.com"},
        )
        handler.rfile.write(b"\0")
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.mock_call(self.registry.get_from_host, ["example.com"], Page("path")),
            self.mock_call_unchecked(self.data_dir.extract_tar_bytes),
            self.mock_call(self.registry.add, ["path"]),
            self.mock_call(self.token_manager.set_token, ["secret", "path"]),
            self.mock_call(self.cert_manager.create_or_update, ["example.com"], False),  # noqa: FBT003
            self.expects_status_only(
                handler, http.HTTPStatus.CREATED, "Resource /path/ updated"
            ),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_put_ok_with_host(self) -> None:
        handler = self._get_handler(
            "/path",
            {"X-Token": "secret", "Content-Length": "1", "X-Host": "example.com"},
        )
        handler.rfile.write(b"\0")
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.mock_call(self.registry.get_from_host, ["example.com"], Page("path")),
            self.mock_call_unchecked(self.data_dir.extract_tar_bytes),
            self.mock_call(self.registry.add, ["path"]),
            self.mock_call(self.token_manager.set_token, ["secret", "path"]),
            self.mock_call(self.cert_manager.create_or_update, ["example.com"], True),  # noqa: FBT003
            self.mock_call(self.registry.set_host, ["path", "example.com"]),
            self.expects_status_only(
                handler, http.HTTPStatus.CREATED, "Resource /path/ updated"
            ),
            self.seal_mocks(),
        ):
            handler.do_PUT()

    def test_do_delete_no_token(self) -> None:
        handler = self._get_handler("/path")
        with (
            self.expects_error(
                handler, http.HTTPStatus.BAD_REQUEST, "No X-Token header in request"
            ),
            self.seal_mocks(),
        ):
            handler.do_DELETE()

    def test_do_delete_invalid_token(self) -> None:
        handler = self._get_handler("/path", {"X-Token": "secret"})
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], False),  # noqa: FBT003
            self.expects_error(handler, http.HTTPStatus.UNAUTHORIZED, "Invalid token"),
            self.seal_mocks(),
        ):
            handler.do_DELETE()

    def test_do_delete_invalid_path(self) -> None:
        handler = self._get_handler("/pa.th", {"X-Token": "secret"})
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.expects_error(handler, http.HTTPStatus.BAD_REQUEST, "Invalid path"),
            self.seal_mocks(),
        ):
            handler.do_DELETE()

    def test_do_delete_invalid_token_for_path(self) -> None:
        handler = self._get_handler("/path", {"X-Token": "secret"})
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                False,  # noqa: FBT003
            ),
            self.expects_error(
                handler, http.HTTPStatus.FORBIDDEN, "Path forbidden for this token"
            ),
            self.seal_mocks(),
        ):
            handler.do_DELETE()

    def test_do_delete_not_found(self) -> None:
        handler = self._get_handler("/path", {"X-Token": "secret"})
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.mock_call(self.data_dir.exists, ["path"], False),  # noqa: FBT003
            self.expects_error(handler, http.HTTPStatus.NOT_FOUND, "Not found"),
            self.seal_mocks(),
        ):
            handler.do_DELETE()

    def test_do_delete_remove_error(self) -> None:
        handler = self._get_handler("/path", {"X-Token": "secret"})
        self.data_dir.remove.side_effect = Exception
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.mock_call(self.data_dir.exists, ["path"], True),  # noqa: FBT003
            self.mock_call(self.data_dir.exists, ["path"], True),  # noqa: FBT003
            self.expects_error(handler, http.HTTPStatus.INTERNAL_SERVER_ERROR, ""),
            self.seal_mocks(),
        ):
            handler.do_DELETE()
        self.data_dir.remove.assert_called_once_with("path")

    def test_do_delete_ok(self) -> None:
        handler = self._get_handler("/path", {"X-Token": "secret"})
        with (
            self.mock_call(self.token_manager.is_valid, ["secret"], True),  # noqa: FBT003
            self.mock_call(
                self.token_manager.is_valid_for_path,
                ["secret", "path"],
                True,  # noqa: FBT003
            ),
            self.mock_call(self.data_dir.exists, ["path"], True),  # noqa: FBT003
            self.mock_call(self.data_dir.remove, ["path"]),
            self.mock_call(self.registry.remove, ["path"]),
            self.expects_error(
                handler, http.HTTPStatus.NO_CONTENT, "Resource /path/ removed"
            ),
            self.seal_mocks(),
        ):
            handler.do_DELETE()

    def test_list_directory(self) -> None:
        handler = self._get_handler("/path/", {"Accept": "text/html"})
        with (
            self.expects_error_full(
                handler, http.HTTPStatus.NOT_FOUND, "File not found"
            ),
            self.seal_mocks(),
        ):
            handler.list_directory()

    def test_translate_path_certbot(self) -> None:
        handler = self._get_handler()
        with (
            self.patch("http.server.SimpleHTTPRequestHandler.translate_path", count=0),
            self.seal_mocks(),
        ):
            self.assertEqual(
                handler.translate_path("/.well-known/acme-challenge/abcde"),
                str(self.certbot_www / ".well-known" / "acme-challenge" / "abcde"),
            )

    def test_translate_path_host_not_found(self) -> None:
        handler = self._get_handler(headers={"Host": "example.com"})
        with (
            self.mock_call(self.registry.get_from_host, ["example.com"]),
            self.patch("http.server.SimpleHTTPRequestHandler.translate_path", count=0),
            self.seal_mocks(),
        ):
            self.assertEqual(
                handler.translate_path("/"),
                "",
            )

    def test_translate_path_invalid(self) -> None:
        handler = self._get_handler()
        with (
            self.patch("http.server.SimpleHTTPRequestHandler.translate_path", count=0),
            self.seal_mocks(),
        ):
            self.assertEqual(
                handler.translate_path("/invalid.path"),
                "",
            )

    def test_translate_path_favicon(self) -> None:
        handler = self._get_handler()
        with (
            self.patch_call(
                "http.server.SimpleHTTPRequestHandler.translate_path",
                ["/favicon.ico"],
            ),
            self.seal_mocks(),
        ):
            self.assertEqual(
                handler.translate_path("/favicon.ico"),
                None,
            )

    def test_translate_path_dotfile(self) -> None:
        handler = self._get_handler()
        with (
            self.patch("http.server.SimpleHTTPRequestHandler.translate_path", count=0),
            self.seal_mocks(),
        ):
            self.assertEqual(
                handler.translate_path("/path/.token"),
                "",
            )

    def test_translate_path_with_host(self) -> None:
        handler = self._get_handler(headers={"Host": "example.com"})
        with (
            self.mock_call(self.registry.get_from_host, ["example.com"], Page("path")),
            self.patch_call(
                "http.server.SimpleHTTPRequestHandler.translate_path",
                ["/path/index.html"],
            ),
            self.seal_mocks(),
        ):
            self.assertEqual(
                handler.translate_path("/index.html"),
                None,
            )

    def test_translate_path_default_host(self) -> None:
        handler = self._get_handler()
        with (
            self.patch_call(
                "http.server.SimpleHTTPRequestHandler.translate_path",
                ["/path/index.html"],
            ),
            self.seal_mocks(),
        ):
            self.assertEqual(
                handler.translate_path("/path/index.html"),
                None,
            )


class TestUpgradeHandler(BaseHandlerTestCase):
    def _get_handler(
        self,
        path: str = "/",
        headers: dict[str, str | None] | None = None,
        rfile: io.BufferedIOBase | None = None,
    ) -> UpgradeHandler:
        if headers is None:
            headers = {}
        with self.patch("http.server.BaseHTTPRequestHandler.__init__"):
            handler = UpgradeHandler(
                unittest.mock.MagicMock(),
                "127.0.0.1",
                unittest.mock.MagicMock(),
                params=Parameters(),
            )
            handler.address_string = lambda: "127.0.0.1"  # ty:ignore[invalid-assignment]
            handler.requestline = "GET /"
            handler.path = path
            handler.request_version = "HTTP/0.9"
            handler.headers = collections.defaultdict(lambda: None, headers)  # ty:ignore[invalid-assignment]
            handler.rfile = rfile if rfile is not None else io.BytesIO()
            handler.wfile = io.BytesIO()
            handler.logger = unittest.mock.Mock(logging.Logger)
            return handler

    def test_do_get(self) -> None:
        handler = self._get_handler("/file")
        with self.expects_status_only(
            handler,
            http.HTTPStatus.MOVED_PERMANENTLY,
            headers={"Location": "https://localhost/file"},
        ):
            handler.do_GET()

    def test_do_head(self) -> None:
        handler = self._get_handler("/file")
        with self.expects_status_only(
            handler,
            http.HTTPStatus.MOVED_PERMANENTLY,
            headers={"Location": "https://localhost/file"},
        ):
            handler.do_HEAD()
