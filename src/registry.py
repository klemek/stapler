import logging
import typing

from . import data_dir, page

if typing.TYPE_CHECKING:
    from . import params


class Registry:
    def __init__(self, params: params.Parameters) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pages: dict[str, page.Page] = {}
        self.data_dir = data_dir.DataDir(params.data_dir)
        self.prefix = f"http://{params.host}"

    def load_pages(self) -> None:
        self.pages = {}
        for path in self.data_dir.list_paths():
            self.add(path)

    def get_hosts(self) -> list[str]:
        return [p.host for p in self.pages.values() if p.host is not None]

    def add(self, path: str) -> None:
        self.pages[path] = page.Page(
            path,
            self.data_dir.has_index(path),
            self.data_dir.get_host(path),
        )
        self.logger.info("Updated %s%s", self.prefix, str(self.pages[path]))

    def set_host(self, path: str, host: str) -> None:
        self.data_dir.set_host(path, host)
        self.pages[path].host = host

    def remove(self, path: str) -> None:
        page = self.pages[path]
        del self.pages[path]
        self.logger.info("Removed %s%s", self.prefix, str(page))

    def get_from_host(self, host: str) -> page.Page | None:
        for p in self.pages.values():
            if p.host == host:
                return p
        return None
