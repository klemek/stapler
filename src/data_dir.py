import os
import io
import tarfile
import shutil
import re
import logging


class DataDir:
    HOST_FILE = ".host"
    PATH_REGEX = re.compile(r"^[\w-]+$")

    def __init__(self, root_path: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.root_path = root_path

    def list_paths(self) -> list[str]:
        paths: list[str] = []
        for path in os.listdir(self.root_path):
            if self.__valid_path(path):
                paths += [path]
        return paths

    def __valid_path(self, path: str, exists: bool = True) -> bool:
        return (
            not exists or os.path.isdir(os.path.join(self.root_path, path))
        ) and self.PATH_REGEX.match(path) is not None

    def set_host(self, path: str, host: str):
        if self.__valid_path(path):
            path_host = os.path.join(self.root_path, path, self.HOST_FILE)
            with open(path_host, mode="w") as host_file:
                host_file.write(host)
            self.logger.debug("Wrote %s", path_host)

    def has_index(self, path: str):
        if self.__valid_path(path):
            path_index = os.path.join(self.root_path, path, "index.html")
            return os.path.exists(path_index) and os.path.isfile(path_index)

    def get_host(self, path: str):
        if self.__valid_path(path):
            path_host = os.path.join(self.root_path, path, self.HOST_FILE)
            if os.path.exists(path_host) and os.path.isfile(path_host):
                try:
                    with open(path_host) as host_file:
                        return host_file.read().split("\n")[0].strip()
                except Exception:
                    pass
            return None

    def extract_tar_bytes(self, path: str, tar_bytes: io.BytesIO):
        if self.__valid_path(path, exists=False):
            target_path = os.path.join(self.root_path, path)
            with tarfile.open(fileobj=tar_bytes) as tar_file:
                if os.path.exists(target_path):
                    shutil.rmtree(target_path)
                    self.logger.debug("Deleted %s", target_path)
                tar_file.extractall(target_path)
                self.logger.debug("Extracted tar to %s", target_path)

    def remove(self, path: str):
        if self.__valid_path(path):
            target_path = os.path.join(self.root_path, path)
            shutil.rmtree(target_path)
            self.logger.debug("Deleted %s", target_path)

    def exists(self, path: str):
        return self.__valid_path(path)
