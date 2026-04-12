import logging

from . import params, page, data_dir


class Registry:
    def __init__(self, params: params.Parameters):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pages: dict[str, page.Page] = {}
        self.data_dir = data_dir.DataDir(params.data_dir)
        self.prefix = f"http://{params.host}"

    def load_pages(self):
        self.pages = {}
        for path in self.data_dir.list_paths():
            self.add(path)

    def add(self, path: str):
        self.pages[path] = page.Page(
            path, self.data_dir.has_index(path), self.data_dir.get_host(path)
        )
        self.logger.info("Updated %s%s", self.prefix, str(self.pages[path]))

    def set_host(self, path: str, host: str):
        self.data_dir.set_host(path, host)
        self.pages[path].host = host

    def remove(self, path: str):
        page = self.pages[path]
        del self.pages[path]
        self.logger.info("Removed %s%s", self.prefix, str(page))

    def get_from_host(self, host: str) -> page.Page | None:
        for p in self.pages.values():
            if p.host == host:
                return p
