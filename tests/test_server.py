import logging
import ssl
import typing
import unittest
import unittest.mock

from src.cert_manager import CertManager
from src.data_dir import DataDir
from src.params import Parameters
from src.registry import Registry
from src.server import StaplerServer
from src.token_manager import TokenManager

from . import BaseTestCase


class TestStaplerServer(BaseTestCase):
    @typing.override
    def setUp(self) -> None:
        self.server = StaplerServer(Parameters())
        self.server.logger = unittest.mock.Mock(logging.Logger)
        self.registry = self.server.registry = self.mock(Registry)
        self.cert_manager = self.server.cert_manager = self.mock(CertManager)
        self.token_manager = self.server.token_manager = self.mock(TokenManager)
        self.data_dir = self.server.data_dir = self.mock(DataDir)
        self.server_mock = unittest.mock.MagicMock()
        self.context_mock = unittest.mock.Mock(ssl.SSLContext)
        super().setUp()

    def test_renew(self) -> None:
        with (
            self.mock_call(self.registry.load_pages),
            self.mock_calls(
                self.registry.get_hosts, [[], []], [["host_1"], ["host_1"]]
            ),
            self.mock_call(self.cert_manager.init, [["localhost", "host_1"]]),
            self.mock_calls(
                self.cert_manager.create_or_update, [["localhost"], ["host_1"]]
            ),
            self.seal_mocks(),
        ):
            self.assertEqual(self.server.renew(), 0)

    def test_renew_without_certificates(self) -> None:
        self.server.params = Parameters(with_certificates=False)
        self.seal_mocks()
        self.assertEqual(self.server.renew(), 1)

    def test_token(self) -> None:
        with (
            self.mock_call(self.registry.load_pages),
            self.mock_call(self.token_manager.init),
            self.mock_call(self.token_manager.new_token),
            self.seal_mocks(),
        ):
            self.assertEqual(self.server.token(), 0)

    def test_run_http(self) -> None:
        self.server.params = Parameters(https=False, with_certificates=False)
        with (
            self.mock_call(self.registry.load_pages),
            self.mock_call(self.data_dir.init),
            self.mock_call(self.token_manager.init),
            self.patch("http.server.ThreadingHTTPServer", self.server_mock),
            self.mock_call(self.server_mock.serve_forever),
            self.seal_mocks(),
        ):
            self.assertEqual(self.server.run(), 0)

    def test_run_https_fail(self) -> None:
        with (
            self.mock_call(self.registry.load_pages),
            self.mock_call(self.registry.get_hosts, [], []),
            self.mock_call(self.cert_manager.init, [["localhost"]]),
            self.mock_call(self.data_dir.init),
            self.mock_call(self.token_manager.init),
            self.mock_call(self.cert_manager.get_https_context, ["localhost"]),
            self.patch("http.server.ThreadingHTTPServer", self.server_mock),
            self.mock_call(self.server_mock.serve_forever),
            self.seal_mocks(),
        ):
            self.assertEqual(self.server.run(), 0)

    def test_run_https(self) -> None:
        with (
            self.mock_call(self.registry.load_pages),
            self.mock_call(self.registry.get_hosts, [], []),
            self.mock_call(self.cert_manager.init, [["localhost"]]),
            self.mock_call(self.data_dir.init),
            self.mock_call(self.token_manager.init),
            self.mock_call(
                self.cert_manager.get_https_context,
                ["localhost"],
                self.context_mock,
            ),
            self.patch("http.server.ThreadingHTTPServer", self.server_mock, 2),
            self.mock_call_unchecked(self.context_mock.wrap_socket),
            self.mock_calls_unchecked(self.server_mock.serve_forever, 2),
            self.mock_call(self.server_mock.shutdown),
            self.seal_mocks(self.context_mock),
        ):
            self.assertEqual(self.server.run(), 0)
