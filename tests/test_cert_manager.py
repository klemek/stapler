import logging
import ssl
import subprocess
import typing
import unittest.mock

from src.cert_manager import CertManager, CertManagerError
from src.params import Parameters

from . import BaseTestCase


class TestRegistry(BaseTestCase):
    @typing.override
    def setUp(self) -> None:
        self.get_tmp_dir()
        self.self_signed_path = self.tmp_path / "self_signed"
        self.certbot_www = self.tmp_path / "certbot_www"
        self.certbot_conf = self.tmp_path / "certbot_conf"
        self.cert_manager = CertManager(
            Parameters(
                self_signed_path=str(self.self_signed_path),
                certbot_www=str(self.certbot_www),
                certbot_conf=str(self.certbot_conf),
            )
        )
        self.cert_manager.logger = unittest.mock.Mock(logging.Logger)
        self.context_mock = unittest.mock.Mock(ssl.SSLContext)
        self.socket_mock = unittest.mock.Mock(ssl.SSLObject)
        unittest.mock.patch("subprocess.check_output")
        super().setUp()

    def test_init_empty(self) -> None:
        with (
            self.patch("shutil.which", count=0),
            self.patch("subprocess.check_output", count=0),
        ):
            self.cert_manager.init([])
            assert self.self_signed_path.is_dir()
            assert self.certbot_www.is_dir()

    def test_init_with_hosts(self) -> None:
        with (
            self.patch("shutil.which", count=0),
            self.patch("subprocess.check_output", count=0),
        ):
            self._make_self_signed("localhost")
            self.cert_manager.init(["localhost"])

    def test_exists_self_signed(self) -> None:
        self._make_self_signed("localhost")
        assert self.cert_manager.exists("localhost")

    def test_exists_certbot(self) -> None:
        self._make_certbot("localhost")
        assert self.cert_manager.exists("localhost")

    def test_exists_fail(self) -> None:
        assert not self.cert_manager.exists("localhost")

    def test_exists_fail_without_certbot(self) -> None:
        self.cert_manager.with_certbot = False
        self._make_certbot("localhost")
        assert not self.cert_manager.exists("localhost")

    def test_init_cert_existing(self) -> None:
        with (
            self.patch("shutil.which", count=0),
            self.patch("subprocess.check_output", count=0),
        ):
            self._make_self_signed("localhost")
            assert not self.cert_manager.init_cert("localhost")

    def test_init_cert_fail(self) -> None:
        with (
            self.patch("shutil.which", return_value=""),
            self.patch("subprocess.check_output") as process_mock,
        ):
            process_mock.side_effect = subprocess.CalledProcessError(1, "", output=b"")
            assert not self.cert_manager.init_cert("localhost")

    def test_init_cert_new(self) -> None:
        with (
            self.patch("shutil.which", return_value=""),
            self.patch("subprocess.check_output") as process_mock,
        ):
            process_mock.side_effect = lambda *_, **__: self._make_self_signed(
                "localhost"
            )
            assert self.cert_manager.init_cert("localhost")

    def test_create_or_update_existing_no_certbot(self) -> None:
        self._make_self_signed("localhost")
        self.cert_manager.with_certbot = False
        with (
            self.patch("shutil.which", return_value=""),
            self.patch("subprocess.check_output") as process_mock,
        ):
            process_mock.side_effect = lambda *_, **__: self._make_self_signed(
                "localhost"
            )
            assert self.cert_manager.create_or_update("localhost")

    def test_create_or_update_existing_certbot(self) -> None:
        self._make_certbot("localhost")
        with (
            self.patch("shutil.which", return_value=""),
            self.patch("subprocess.check_output") as process_mock,
        ):
            process_mock.side_effect = lambda *_, **__: self._make_certbot("localhost")
            assert self.cert_manager.create_or_update("localhost")

    def test_create_or_update_existing_fail_both(self) -> None:
        self._make_certbot("localhost")
        with (
            self.patch("shutil.which", return_value="", count=2),
            self.patch("subprocess.check_output", count=2) as process_mock,
        ):
            process_mock.side_effect = subprocess.CalledProcessError(1, "", output=b"")
            assert not self.cert_manager.create_or_update("localhost")

    def test_create_or_update_existing_fail_both_binary(self) -> None:
        self._make_certbot("localhost")
        with (
            self.patch("shutil.which", count=2),
            self.patch("subprocess.check_output", count=0),
        ):
            assert not self.cert_manager.create_or_update("localhost")

    def test_get_cert_certbot(self) -> None:
        self._make_certbot("localhost")
        self.assertEqual(
            self.cert_manager.get_cert("localhost"),
            self.certbot_conf / "live" / "localhost" / CertManager.CRT_FILE,
        )

    def test_get_cert_self_signed(self) -> None:
        self._make_self_signed("localhost")
        self.assertEqual(
            self.cert_manager.get_cert("localhost"),
            self.self_signed_path / "localhost" / CertManager.CRT_FILE,
        )

    def test_get_cert_fail(self) -> None:
        self.assertRaises(
            CertManagerError,
            lambda: self.cert_manager.get_cert("localhost"),
        )

    def test_get_key_certbot(self) -> None:
        self._make_certbot("localhost")
        self.assertEqual(
            self.cert_manager.get_key("localhost"),
            self.certbot_conf / "live" / "localhost" / CertManager.KEY_FILE,
        )

    def test_get_key_self_signed(self) -> None:
        self._make_self_signed("localhost")
        self.assertEqual(
            self.cert_manager.get_key("localhost"),
            self.self_signed_path / "localhost" / CertManager.KEY_FILE,
        )

    def test_get_key_fail(self) -> None:
        self.assertRaises(
            CertManagerError,
            lambda: self.cert_manager.get_key("localhost"),
        )

    def test_get_https_context_fail(self) -> None:
        self.assertIsNone(self.cert_manager.get_https_context("localhost"))

    def test_get_https_context(self) -> None:
        self._make_self_signed("localhost")
        with (
            self.patch("ssl.create_default_context", return_value=self.context_mock),
            self.mock_call(
                self.context_mock.load_cert_chain,
                [
                    self.self_signed_path / "localhost" / CertManager.CRT_FILE,
                    self.self_signed_path / "localhost" / CertManager.KEY_FILE,
                ],
            ),
        ):
            self.assertEqual(
                self.cert_manager.get_https_context("localhost"), self.context_mock
            )

    def test_sni_callback_no_host(self) -> None:
        self._make_self_signed("localhost")
        with (
            self.patch("ssl.create_default_context", return_value=self.context_mock),
            self.mock_call(
                self.context_mock.load_cert_chain,
                [
                    self.self_signed_path / "localhost" / CertManager.CRT_FILE,
                    self.self_signed_path / "localhost" / CertManager.KEY_FILE,
                ],
            ),
        ):
            self.cert_manager.get_https_context("localhost")
            self.context_mock.sni_callback(self.socket_mock, None, self.context_mock)

    def test_sni_callback_fail(self) -> None:
        self._make_self_signed("localhost")
        with (
            self.patch("ssl.create_default_context", return_value=self.context_mock),
            self.mock_call(
                self.context_mock.load_cert_chain,
                [
                    self.self_signed_path / "localhost" / CertManager.CRT_FILE,
                    self.self_signed_path / "localhost" / CertManager.KEY_FILE,
                ],
            ),
            self.patch("shutil.which", count=3),
        ):
            self.cert_manager.get_https_context("localhost")
            self.assertRaises(
                CertManagerError,
                lambda: self.context_mock.sni_callback(
                    self.socket_mock, "new_host", self.context_mock
                ),
            )

    def test_sni_callback_change_context(self) -> None:
        self._make_self_signed("localhost")
        self._make_self_signed("new_host")
        with (
            self.patch(
                "ssl.create_default_context", return_value=self.context_mock, count=2
            ),
            self.mock_calls(
                self.context_mock.load_cert_chain,
                [
                    [
                        self.self_signed_path / "localhost" / CertManager.CRT_FILE,
                        self.self_signed_path / "localhost" / CertManager.KEY_FILE,
                    ],
                    [
                        self.self_signed_path / "new_host" / CertManager.CRT_FILE,
                        self.self_signed_path / "new_host" / CertManager.KEY_FILE,
                    ],
                ],
            ),
            self.patch("shutil.which", count=0),
        ):
            self.cert_manager.get_https_context("localhost")
            self.context_mock.sni_callback(
                self.socket_mock, "new_host", self.context_mock
            )

    def _make_self_signed(self, host: str) -> None:
        (self.self_signed_path / host).mkdir(parents=True, exist_ok=True)
        (self.self_signed_path / host / CertManager.CRT_FILE).touch()
        (self.self_signed_path / host / CertManager.KEY_FILE).touch()

    def _make_certbot(self, host: str) -> None:
        (self.certbot_conf / "live" / host).mkdir(parents=True, exist_ok=True)
        (self.certbot_conf / "live" / host / CertManager.CRT_FILE).touch()
        (self.certbot_conf / "live" / host / CertManager.KEY_FILE).touch()
