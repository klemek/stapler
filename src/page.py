import dataclasses


@dataclasses.dataclass
class Page:
    path: str
    with_index: bool = False
    host: str | None = None
    token_hash: str | None = None

    def __repr__(self) -> str:
        out = f"/{self.path}/"
        if self.host is not None:
            out += f" [{self.host}]"
        if not self.with_index:
            out += " (no index)"
        return out
