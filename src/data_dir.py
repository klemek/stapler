import logging
import pathlib
import re
import shutil
import tarfile
import typing

if typing.TYPE_CHECKING:
    import io


class DataDir:
    PATH_REGEX = re.compile(r"^[\w-]+$")
    NEEDED_FILES: typing.ClassVar[list[str]] = ["favicon.ico"]

    def __init__(self, root_path: str) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.root_path = pathlib.Path(root_path)

    def init(self) -> None:
        self.logger.debug("Initializing...")
        for file in self.NEEDED_FILES:
            if not (self.root_path / file).is_file():
                (pathlib.Path.cwd() / file).copy_into(self.root_path)
                self.logger.debug("Copied %s into data dir", file)

    def list_paths(self) -> list[str]:
        paths: list[str] = []
        for path in self.root_path.iterdir():
            if self.exists(path.name):
                paths += [path.name]
        return paths

    def __valid_path(self, path: str) -> bool:
        return self.PATH_REGEX.match(path) is not None

    def has_index(self, path: str) -> bool:
        if self.exists(path):
            path_index = self.root_path / path / "index.html"
            return path_index.is_file()
        return False

    def set_file(
        self, path: str, file_name: str, value: str, chmod: int = 0o644
    ) -> None:
        if self.exists(path):
            file_path = self.root_path / path / file_name
            with file_path.open(mode="w") as file:
                file.write(value)
            file_path.chmod(chmod)
            self.logger.debug("Wrote %s", file_path)

    def get_file(self, path: str, file_name: str) -> str | None:
        if self.exists(path):
            file_path = self.root_path / path / file_name
            if file_path.is_file():
                try:
                    with file_path.open() as file:
                        return file.read().split("\n")[0].strip()
                except Exception:
                    self.logger.exception("Cannot read %s", file_path)
            return None
        return None

    def extract_tar_bytes(self, path: str, tar_bytes: io.BytesIO) -> None:
        if self.__valid_path(path):
            target_path = self.root_path / path
            with tarfile.open(fileobj=tar_bytes) as tar_file:
                if target_path.exists():
                    shutil.rmtree(target_path)
                    self.logger.debug("Deleted %s", target_path)
                tar_file.extractall(target_path, filter="data")
                for target_file in target_path.iterdir():
                    if re.match(r"^\..*", target_file.name):  # remove dot files
                        if target_file.is_dir():
                            shutil.rmtree(target_file)
                        else:
                            target_file.unlink()
                self.logger.debug("Extracted tar to %s", target_path)

    def remove(self, path: str) -> None:
        if self.exists(path):
            target_path = self.root_path / path
            shutil.rmtree(target_path)
            self.logger.debug("Deleted %s", target_path)

    def exists(self, path: str) -> bool:
        return (
            self.PATH_REGEX.match(path) is not None and (self.root_path / path).is_dir()
        )
