import dataclasses


@dataclasses.dataclass
class Page:
    path: str
    with_index: bool
    host: str | None = None
    token_hash: str | None = None

    def get_url_path(self) -> str:
        return f"/{self.path}/"

    def __repr__(self) -> str:
        out = self.get_url_path()
        if self.host is not None:
            out += f" [{self.host}]"
        if not self.with_index:
            out += " (no index)"
        return out
