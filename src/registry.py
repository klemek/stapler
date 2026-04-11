import os

from . import params, page

_HOST_FILE = ".host"


class Registry:
    def __init__(self, params: params.Parameters):
        self.pages: dict[str, page.Page] = {}
        self.data_dir = params.data_dir
        self.prefix = f"http://{params.host}:{params.port}"

    def load_pages(self):
        self.pages = {}
        for path in os.listdir(self.data_dir):
            self.add(path)

    def add(self, path: str):
        real_path = os.path.join(self.data_dir, path)
        if os.path.isdir(real_path):
            self.pages[path] = page.Page(
                path, self.__has_index(path), self.__get_host(path)
            )
            print("Updated: " + self.prefix + str(self.pages[path]))

    def set_host(self, path: str, host: str):
        path_host = os.path.join(self.data_dir, path, _HOST_FILE)
        with open(path_host, mode="w") as host_file:
            host_file.write(host)
        self.pages[path].host = host

    def __has_index(self, path: str) -> bool:
        path_index = os.path.join(self.data_dir, path, "index.html")
        return os.path.exists(path_index) and os.path.isfile(path_index)

    def __get_host(self, path: str) -> str | None:
        path_host = os.path.join(self.data_dir, path, _HOST_FILE)
        if os.path.exists(path_host) and os.path.isfile(path_host):
            try:
                with open(path_host) as host_file:
                    return host_file.read().split("\n")[0].strip()
            except Exception:
                pass
        return None

    def remove(self, path: str):
        page = self.pages[path]
        del self.pages[path]
        print("Removed: " + self.prefix + str(page))

    def get_from_host(self, host: str) -> page.Page | None:
        for p in self.pages.values():
            if p.host == host:
                return p
