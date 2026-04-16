import hashlib
import logging
import pathlib
import secrets
import typing

if typing.TYPE_CHECKING:
    from . import params, registry


class TokenManager:
    FILE = ".tokens"

    def __init__(self, params: params.Parameters, registry: registry.Registry) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.token_salt = params.token_salt
        self.tokens_file = pathlib.Path(params.data_dir) / self.FILE
        self.registry = registry
        self.token_hashes: list[str] = []

    def init(self) -> None:
        self.logger.debug("Initializing...")
        if not len(self.token_salt):
            self.logger.warning(
                "No salt provided, tokens will be cryptographically weak"
            )
        if not self.tokens_file.exists():
            self.tokens_file.touch()
        self.tokens_file.chmod(0o600)
        self.token_hashes = self.__load_hashes()

    def is_valid(self, token: str) -> bool:
        return self.__hash_token(token) in self.token_hashes

    def is_valid_for_path(self, token: str, path: str) -> bool:
        return (page := self.registry.get_from_path(path)) is None or (
            page.token_hash is None or page.token_hash == self.__hash_token(token)
        )

    def set_token(self, token: str, path: str) -> None:
        self.registry.set_token_hash(path, self.__hash_token(token))

    def new_token(self) -> None:
        new_token = secrets.token_hex(16)
        self.token_hashes += [self.__hash_token(new_token)]
        self.__save_hashes()
        self.logger.warning("NEW TOKEN: %s", new_token)
        self.logger.warning("Please copy this secret value before it disappears")

    def __hash_token(self, token: str) -> str:
        return hashlib.sha512(
            (self.token_salt + token).encode(), usedforsecurity=True
        ).hexdigest()

    def __load_hashes(self) -> list[str]:
        if self.tokens_file.is_file():
            with self.tokens_file.open() as file:
                return [line.strip() for line in file]
        return []

    def __save_hashes(self) -> None:
        with self.tokens_file.open(mode="w") as file:
            file.write("\n".join(self.token_hashes))
        self.tokens_file.chmod(0o600)
        self.logger.debug("Updated %s", self.tokens_file)
