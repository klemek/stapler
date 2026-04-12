import logging
import pathlib
import re
import shutil
import tarfile
import typing

if typing.TYPE_CHECKING:
    import io


class DataDir:
    HOST_FILE = ".host"
    PATH_REGEX = re.compile(r"^[\w-]+$")

    def __init__(self, root_path: str) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.root_path = pathlib.Path(root_path)

    def list_paths(self) -> list[str]:
        paths: list[str] = []
        for path in self.root_path.iterdir():
            if self.exists(path.name):
                paths += [path.name]
        return paths

    def __valid_path(self, path: str) -> bool:
        return self.PATH_REGEX.match(path) is not None

    def set_host(self, path: str, host: str) -> None:
        if self.exists(path):
            path_host = self.root_path / path / self.HOST_FILE
            with path_host.open(mode="w") as host_file:
                host_file.write(host)
            self.logger.debug("Wrote %s", path_host)

    def has_index(self, path: str) -> bool:
        if self.exists(path):
            path_index = self.root_path / path / "index.html"
            return path_index.is_file()
        return False

    def get_host(self, path: str) -> str | None:
        if self.exists(path):
            path_host = self.root_path / path / self.HOST_FILE
            if path_host.is_file():
                try:
                    with path_host.open() as host_file:
                        return host_file.read().split("\n")[0].strip()
                except Exception:
                    self.logger.exception("Cannot read %s", path_host)
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
