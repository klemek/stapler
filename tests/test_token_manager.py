import logging
import typing
import unittest
import unittest.mock

from src.page import Page
from src.params import Parameters
from src.registry import Registry
from src.token_manager import TokenManager

from . import BaseTestCase


class TestTokenManager(BaseTestCase):
    EMPTY_SALT_HASH = "a04ca803c9fd73c21b721ece14b8b30cd3d9ca1bff752904a46982b881e152d0cdaa463a32e6bce71408de611953bc304ca8000d40d4b06b3f2a70769f69fecc"
    SALT_HASH = "a5f2d8785eb4f064eae60f94e6025f93be32c2c93d2bbd73a982ee5c7ebcc484536487a4f60cfdfcb9ba72da7cebe0ce11afa91f191272e51d8c14be6874824b"
    SECRET_HASH = "9901847ff8c76bd5fb473b7bd2e4f4ddd110332a52a888fd69deb276613885ddf382e5cf1210ed0decdb8010ae3994331a9e0639c3ca7e9e8b110dd50978ce76"  # noqa: S105

    @typing.override
    def setUp(self) -> None:
        self.registry = self.mock(Registry)
        self.token_manager = TokenManager(
            Parameters(data_dir=self.get_tmp_dir(), token_salt="salt"),  # noqa: S106
            self.registry,
        )
        self.token_manager.logger = unittest.mock.Mock(logging.Logger)
        self.tmp_tokens_file = self.tmp_path / TokenManager.FILE
        super().setUp()

    def test_init_no_hashes(self) -> None:
        self.seal_mocks()
        self.token_manager.init()
        self.assert_file_content(self.tmp_tokens_file, self.SALT_HASH)
        self.assertEqual(self.tmp_tokens_file.stat().st_mode, 0o100600)
        self.assertListEqual(self.token_manager.token_hashes, [])

    def test_init_weak_salt(self) -> None:
        self.token_manager.token_salt = ""
        self.seal_mocks()
        self.token_manager.init()
        self.assert_file_content(
            self.tmp_tokens_file,
            self.EMPTY_SALT_HASH,
        )
        self.assertListEqual(self.token_manager.token_hashes, [])

    def test_init_load_hashes(self) -> None:
        with self.tmp_tokens_file.open(mode="w") as file:
            file.write(self.SALT_HASH + "\n" + self.SECRET_HASH)
        self.seal_mocks()
        self.token_manager.init()
        self.assertListEqual(self.token_manager.token_hashes, [self.SECRET_HASH])

    def test_init_invalid_salt(self) -> None:
        with self.tmp_tokens_file.open(mode="w") as file:
            file.write(self.EMPTY_SALT_HASH + "\n" + self.SECRET_HASH)
        self.seal_mocks()
        self.token_manager.init()
        self.assertListEqual(self.token_manager.token_hashes, [])

    def test_is_valid(self) -> None:
        self.seal_mocks()
        self.token_manager.token_hashes = [self.SECRET_HASH]
        assert self.token_manager.is_valid("secret")

    def test_is_valid_fail(self) -> None:
        self.seal_mocks()
        assert not self.token_manager.is_valid("secret")

    def test_is_valid_for_path(self) -> None:
        with (
            self.mock_call(
                self.registry.get_from_path,
                ["test_1"],
                Page("test_1", token_hash=self.SECRET_HASH),
            ),
            self.seal_mocks(),
        ):
            assert self.token_manager.is_valid_for_path("secret", "test_1")

    def test_is_valid_for_path_no_token(self) -> None:
        with (
            self.mock_call(
                self.registry.get_from_path,
                ["test_1"],
                Page("test_1"),
            ),
            self.seal_mocks(),
        ):
            assert self.token_manager.is_valid_for_path("secret", "test_1")

    def test_is_valid_for_path_no_page(self) -> None:
        with (
            self.mock_call(
                self.registry.get_from_path,
                ["test_1"],
            ),
            self.seal_mocks(),
        ):
            assert self.token_manager.is_valid_for_path("secret", "test_1")

    def test_is_valid_for_path_fail(self) -> None:
        with (
            self.mock_call(
                self.registry.get_from_path,
                ["test_1"],
                Page("test_1", token_hash=self.SALT_HASH),
            ),
            self.seal_mocks(),
        ):
            assert not self.token_manager.is_valid_for_path("secret", "test_1")

    def test_set_token(self) -> None:
        with (
            self.mock_call(
                self.registry.set_token_hash,
                ["test_1", self.SECRET_HASH],
            ),
            self.seal_mocks(),
        ):
            self.token_manager.set_token("secret", "test_1")

    @unittest.mock.patch("secrets.token_hex")
    def test_new_token(self, mock_token_hex: unittest.mock.Mock) -> None:
        mock_token_hex.return_value = "secret"
        self.seal_mocks()
        self.token_manager.new_token()
        self.assertListEqual(self.token_manager.token_hashes, [self.SECRET_HASH])
        self.assert_file_content(self.tmp_tokens_file, self.SALT_HASH, self.SECRET_HASH)
