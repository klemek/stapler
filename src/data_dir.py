import os
import io
import tarfile
import shutil


class DataDir:
    HOST_FILE = ".host"

    def __init__(self, root_path: str):
        self.root_path = root_path

    def list_paths(self) -> list[str]:
        paths: list[str] = []
        for path in os.listdir(self.root_path):
            if os.path.isdir(os.path.join(self.root_path, path)):
                paths += [path]
        return paths

    def set_host(self, path: str, host: str):
        path_host = os.path.join(self.root_path, path, self.HOST_FILE)
        with open(path_host, mode="w") as host_file:
            host_file.write(host)

    def has_index(self, path: str):
        path_index = os.path.join(self.root_path, path, "index.html")
        return os.path.exists(path_index) and os.path.isfile(path_index)

    def get_host(self, path: str):
        path_host = os.path.join(self.root_path, path, self.HOST_FILE)
        if os.path.exists(path_host) and os.path.isfile(path_host):
            try:
                with open(path_host) as host_file:
                    return host_file.read().split("\n")[0].strip()
            except Exception:
                pass
        return None

    def extract_tar_bytes(self, path: str, tar_bytes: io.BytesIO):
        target_path = os.path.join(self.root_path, path)
        with tarfile.open(fileobj=tar_bytes) as tar_file:
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            tar_file.extractall(target_path)

    def remove(self, path: str):
        target_path = os.path.join(self.root_path, path)
        shutil.rmtree(target_path)

    def exists(self, path: str):
        target_path = os.path.join(self.root_path, path)
        return os.path.exists(target_path) and os.path.isdir(target_path)
