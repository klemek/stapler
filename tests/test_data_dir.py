import io
import logging
import tarfile
import typing
import unittest
import unittest.mock

from src.data_dir import DataDir

from . import BaseTestCase


class TestDataDir(BaseTestCase):
    @typing.override
    def setUp(self) -> None:
        self.data_dir = DataDir(self.get_tmp_dir())
        self.data_dir.logger = unittest.mock.Mock(logging.Logger)
        super().setUp()

    def test_init_empty(self) -> None:
        self.data_dir.init()
        for file in self.data_dir.NEEDED_FILES:
            assert (self.tmp_path / file).exists()

    def test_init_existing(self) -> None:
        for file in self.data_dir.NEEDED_FILES:
            (self.tmp_path / file).touch()
        self.data_dir.init()

    def test_list_paths(self) -> None:
        self.__create_path("test_1")
        (self.tmp_path / "test_2").touch()
        paths = self.data_dir.list_paths()
        self.assertEqual(paths, ["test_1"])

    def test_exists(self) -> None:
        self.__create_path("test_1")
        assert self.data_dir.exists("test_1")

    def test_exists_invalid_path(self) -> None:
        assert not self.data_dir.exists("test_1")

    def test_has_index_with_index(self) -> None:
        self.__create_path("test_1", {"index.html": ""})
        assert self.data_dir.has_index("test_1")

    def test_has_index_without_index(self) -> None:
        self.__create_path("test_1", {"index.txt": ""})
        assert not self.data_dir.has_index("test_1")

    def test_has_index_invalid_path(self) -> None:
        assert not self.data_dir.has_index("test_1")

    def test_get_file(self) -> None:
        self.__create_path("test_1", {".value": "test_value\nother_line"})
        self.assertEqual(self.data_dir.get_file("test_1", ".value"), "test_value")

    def test_get_file_not_found(self) -> None:
        self.__create_path("test_1")
        self.assertIsNone(self.data_dir.get_file("test_1", ".value"))

    def test_get_file_cannot_read(self) -> None:
        self.__create_path("test_1", {".value": "value"})
        (self.tmp_path / "test_1" / ".value").chmod(0o333)
        self.assertIsNone(self.data_dir.get_file("test_1", ".value"))

    def test_get_file_invalid_path(self) -> None:
        self.assertIsNone(self.data_dir.get_file("test_1", ".value"))

    def test_set_file_create(self) -> None:
        self.__create_path("test_1")
        self.data_dir.set_file("test_1", ".value", "other_value")
        self.assert_file_content(self.tmp_path / "test_1" / ".value", "other_value")

    def test_set_file_update(self) -> None:
        self.__create_path("test_1", {".value": "test_value\nother_line"})
        self.data_dir.set_file("test_1", ".value", "other_value")
        self.assert_file_content(self.tmp_path / "test_1" / ".value", "other_value")

    def test_set_file_invalid_path(self) -> None:
        self.data_dir.set_file("test_1", ".value", "test")
        assert not (self.tmp_path / "test_1").exists()
        assert not (self.tmp_path / "test_1" / ".value").exists()

    def test_remove(self) -> None:
        self.__create_path("test_1")
        self.data_dir.remove("test_1")
        assert not (self.tmp_path / "test_1").exists()

    def test_remove_invalid_path(self) -> None:
        self.data_dir.remove("test_1")

    def test_extract_tar_bytes_create(self) -> None:
        tar_bytes = self.__get_tar_bytes({"value": "value"})
        self.data_dir.extract_tar_bytes("test_1", tar_bytes)
        self.assert_file_content(self.tmp_path / "test_1" / "value", "value")

    def test_extract_tar_bytes_create_without_dotfiles(self) -> None:
        tar_bytes = self.__get_tar_bytes(
            {"value": "value", ".value": "value", ".git/test": "test"}
        )
        self.data_dir.extract_tar_bytes("test_1", tar_bytes)
        self.assert_file_content(self.tmp_path / "test_1" / "value", "value")

    def test_extract_tar_bytes_update(self) -> None:
        self.__create_path(
            "test_1",
            {"value": "test_value\nother_line", ".host": "aaah"},
        )
        tar_bytes = self.__get_tar_bytes({"value": "value"})
        self.data_dir.extract_tar_bytes("test_1", tar_bytes)
        self.assert_file_content(self.tmp_path / "test_1" / "value", "value")
        assert not (self.tmp_path / "test_1" / ".host").exists()

    def test_extract_tar_bytes_invalid_path(self) -> None:
        tar_bytes = self.__get_tar_bytes({"value": "value"})
        self.data_dir.extract_tar_bytes("~test", tar_bytes)
        assert not (self.tmp_path / "~test").exists()

    def __create_path(self, path: str, files: dict[str, str] | None = None) -> None:
        (self.tmp_path / path).mkdir()
        if files is not None:
            for name, content in files.items():
                file_path = self.tmp_path / path / name
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with file_path.open(mode="w") as file:
                    file.write(content)

    def __get_tar_bytes(self, files: dict[str, str] | None = None) -> io.BytesIO:
        self.__create_path("tmp", files)
        with tarfile.open(self.tmp_path / "tmp.tar.gz", mode="w") as tar_file:
            if files is not None:
                for file in files:
                    tar_file.add(self.tmp_path / "tmp" / file, file)
            tar_file.close()
        with (self.tmp_path / "tmp.tar.gz").open(mode="rb") as file:
            return io.BytesIO(file.read())
