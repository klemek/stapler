import logging
import typing
import unittest
import unittest.mock

from src.data_dir import DataDir
from src.page import Page
from src.params import Parameters
from src.registry import Registry

from . import BaseTestCase


class TestRegistry(BaseTestCase):
    @typing.override
    def setUp(self) -> None:
        self.registry = Registry(Parameters())
        self.registry.logger = unittest.mock.Mock(logging.Logger)
        self.data_dir = self.registry.data_dir = self.mock(DataDir)
        super().setUp()

    def test_load_pages(self) -> None:
        with (
            self.mock_call(self.data_dir.list_paths, [], ["test_1", "test_2"]),
            self.mock_calls(
                self.data_dir.has_index, [["test_1"], ["test_2"]], [True, False]
            ),
            self.mock_calls(
                self.data_dir.get_file,
                [
                    ["test_1", Registry.HOST_FILE],
                    ["test_1", Registry.TOKEN_FILE],
                    ["test_2", Registry.HOST_FILE],
                    ["test_2", Registry.TOKEN_FILE],
                ],
                [
                    "test_1_host",
                    "test_1_token",
                    None,
                    "test_2_token",
                ],
            ),
            self.seal_mocks(),
        ):
            self.registry.load_pages()
        self.assertEqual(len(self.registry.pages), 2)
        self.assertEqual(list(self.registry.pages.keys()), ["test_1", "test_2"])
        self.assertEqual(
            self.registry.pages["test_1"],
            Page(
                "test_1",
                True,  # noqa: FBT003
                "test_1_host",
                "test_1_token",
            ),
        )
        self.assertEqual(
            self.registry.pages["test_2"],
            Page(
                "test_2",
                False,  # noqa: FBT003
                None,
                "test_2_token",
            ),
        )

    def test_get_hosts(self) -> None:
        self.registry.pages["test_1"] = Page(
            "test_1",
            host="test_1_host",
        )
        self.registry.pages["test_2"] = Page(
            "test_2",
            host="test_2_host",
        )
        self.registry.pages["test_3"] = Page(
            "test_3",
            host=None,
        )
        self.seal_mocks()
        self.assertEqual(self.registry.get_hosts(), ["test_1_host", "test_2_host"])

    def test_set_host(self) -> None:
        self.registry.pages["test_1"] = Page(
            "test_1",
            host="test_1_host",
        )
        with (
            self.mock_call(
                self.data_dir.set_file, ["test_1", Registry.HOST_FILE, "new_value"]
            ),
            self.seal_mocks(),
        ):
            self.registry.set_host("test_1", "new_value")
        self.assertEqual(self.registry.pages["test_1"].host, "new_value")

    def test_set_token_hash(self) -> None:
        self.registry.pages["test_1"] = Page(
            "test_1",
            token_hash=None,
        )
        with (
            self.mock_call(
                self.data_dir.set_file,
                ["test_1", Registry.TOKEN_FILE, "new_value", 0o600],
            ),
            self.seal_mocks(),
        ):
            self.registry.set_token_hash("test_1", "new_value")
        self.assertEqual(self.registry.pages["test_1"].token_hash, "new_value")

    def test_remove(self) -> None:
        self.registry.pages["test_1"] = Page(
            "test_1",
        )
        self.seal_mocks()
        self.registry.remove("test_1")
        self.assertNotIn("test_1", self.registry.pages)

    def test_get_from_path(self) -> None:
        self.registry.pages["test_1"] = (
            target := Page(
                "test_1",
            )
        )
        self.registry.pages["test_2"] = Page(
            "test_2",
        )
        self.seal_mocks()
        self.assertEqual(self.registry.get_from_path("test_1"), target)

    def test_get_from_path_not_found(self) -> None:
        self.registry.pages["test_1"] = Page(
            "test_1",
        )
        self.registry.pages["test_2"] = Page(
            "test_2",
        )
        self.seal_mocks()
        self.assertIsNone(self.registry.get_from_path("test_3"))

    def test_get_from_host(self) -> None:
        self.registry.pages["test_1"] = (target := Page("test_1", host="host_1"))
        self.registry.pages["test_2"] = Page("test_2", host="host_2")
        self.seal_mocks()
        self.assertEqual(self.registry.get_from_host("host_1"), target)

    def test_get_from_host_not_found(self) -> None:
        self.registry.pages["test_1"] = Page("test_1", host="host_1")
        self.registry.pages["test_2"] = Page("test_2", host="host_2")
        self.seal_mocks()
        self.assertIsNone(self.registry.get_from_host("host_3"))
