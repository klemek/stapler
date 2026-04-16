import logging
import typing

from . import data_dir, page

if typing.TYPE_CHECKING:
    from . import params


class Registry:
    HOST_FILE = ".host"
    TOKEN_FILE = ".token"  # noqa: S105

    def __init__(self, params: params.Parameters) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.pages: dict[str, page.Page] = {}
        self.data_dir = data_dir.DataDir(params.data_dir)

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
            self.data_dir.get_file(path, self.HOST_FILE),
            self.data_dir.get_file(path, self.TOKEN_FILE),
        )
        self.logger.info("Updated %s", self.pages[path])

    def set_host(self, path: str, host: str) -> None:
        if self.pages[path].host != host:
            self.data_dir.set_file(path, self.HOST_FILE, host)
            self.pages[path].host = host
            self.logger.debug("Updated %s", self.pages[path])

    def set_token_hash(self, path: str, token_hash: str) -> None:
        if self.pages[path].token_hash != token_hash:
            self.data_dir.set_file(path, self.TOKEN_FILE, token_hash)
            self.pages[path].token_hash = token_hash
            self.logger.debug("Updated %s", self.pages[path])

    def remove(self, path: str) -> None:
        page = self.pages[path]
        del self.pages[path]
        self.logger.info("Removed %s", page)

    def get_from_path(self, path: str) -> page.Page | None:
        if path in self.pages:
            return self.pages[path]
        return None

    def get_from_host(self, host: str) -> page.Page | None:
        for p in self.pages.values():
            if p.host == host:
                return p
        return None
