import logging
import pathlib
import shutil
import subprocess
import typing

if typing.TYPE_CHECKING:
    from . import params


class CertManagerError(Exception):
    pass


class CertManager:
    SELF_SIGNED_DAYS = 30
    CRT_FILE = "fullchain.pem"
    KEY_FILE = "privkey.pem"

    def __init__(self, params: params.Parameters) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.certbot_conf = pathlib.Path(params.certbot_conf)
        self.certbot_www = pathlib.Path(params.certbot_www)
        self.self_signed_path = pathlib.Path(params.self_signed_path)
        self.with_certbot = params.with_certbot

    def init(self, hosts: list[str]) -> None:
        if not self.certbot_www.exists():
            self.certbot_www.mkdir(parents=True)
            self.logger.debug("Created %s", self.certbot_www)
        if not self.self_signed_path.exists():
            self.self_signed_path.mkdir(parents=True)
            self.logger.debug("Created %s", self.self_signed_path)
        for host in hosts:
            self.init_cert(host)

    def exists(self, host: str) -> bool:
        return self.__exists_certbot(host) or self.__exists_self_signed(host)

    def init_cert(self, host: str) -> bool:
        if not self.exists(host):
            return self.__create_self_signed(host)
        self.logger.debug("Certificate exists for %s", host)
        return False

    def create_or_update(self, host: str) -> bool:
        created = self.init_cert(host)
        if self.with_certbot and self.__create_certbot(host):
            return True
        return created or self.__create_self_signed(host)

    def get_pem(self, host: str) -> pathlib.Path | None:
        if self.__exists_certbot(host):
            return self.__certbot_file(host, self.CRT_FILE)
        if self.__exists_self_signed(host):
            return self.__self_signed_file(host, self.CRT_FILE)
        return None

    def get_key(self, host: str) -> pathlib.Path | None:
        if self.__exists_certbot(host):
            return self.__certbot_file(host, self.KEY_FILE)
        if self.__exists_self_signed(host):
            return self.__self_signed_file(host, self.KEY_FILE)
        return None

    def __self_signed_file(self, host: str, file: str) -> pathlib.Path:
        return self.self_signed_path / host / file

    def __exists_self_signed(self, host: str) -> bool:
        return (
            self.__self_signed_file(host, self.CRT_FILE).is_file()
            and self.__self_signed_file(host, self.KEY_FILE).is_file()
        )

    def __get_openssl_bin(self) -> str:
        binary_path = shutil.which("openssl")
        if binary_path is None:
            msg = "Cannot find 'openssl' binary in PATH"
            raise CertManagerError(msg)
        return binary_path

    def __create_self_signed(self, host: str) -> bool:
        cert_path = self.self_signed_path / host
        if not cert_path.exists():
            cert_path.mkdir(parents=True)
        cert_host: str = host
        if ":" in host:
            cert_host = host.split(":", maxsplit=2)[0]
        try:
            # openssl req -new -newkey rsa:2048 -days 30 -nodes -x509 -keyout server.key -out server.crt
            subprocess.run(
                [
                    self.__get_openssl_bin(),
                    "req",
                    "-new",
                    "-newkey",
                    "rsa:4096",
                    "-days",
                    str(self.SELF_SIGNED_DAYS),
                    "-nodes",
                    "-x509",
                    "-keyout",
                    cert_path / "privkey.pem",
                    "-out",
                    cert_path / "fullchain.pem",
                    "-subj",
                    f"/C=/ST=/L=/O=/OU=/CN={cert_host}",
                ],
                check=True,
            )
            self.logger.info("Created self-signed certificate for %s", host)
        except subprocess.CalledProcessError:
            self.logger.exception(
                "Could not create self-signed certificate for %s", host
            )
            return False
        return self.__exists_self_signed(host)

    def __certbot_file(self, host: str, file: str) -> pathlib.Path:
        return self.certbot_conf / "live" / host / file

    def __exists_certbot(self, host: str) -> bool:
        return (
            self.with_certbot
            and self.__certbot_file(host, self.CRT_FILE).is_file()
            and self.__certbot_file(host, self.KEY_FILE).is_file()
        )

    def __get_certbot_bin(self) -> str:
        binary_path = shutil.which("certbot")
        if binary_path is None:
            msg = "Cannot find 'certbot' binary in PATH"
            raise CertManagerError(msg)
        return binary_path

    def __create_certbot(self, host: str) -> bool:
        cert_host: str = host
        if ":" in host:
            cert_host = host.split(":", maxsplit=2)[0]
        try:
            #  certonly -v --webroot --webroot-path=/var/www/certbot --agree-tos --no-eff-email -n --force-renewal --expand
            subprocess.run(
                [
                    self.__get_certbot_bin(),
                    "--non-interactive",
                    "--agree-tos",
                    "--webroot",
                    "--webroot-path",
                    self.certbot_www,
                    "--no-eff-email",
                    "--cert-name",
                    host,
                    "--domain",
                    cert_host,
                ],
                check=True,
            )
            self.logger.info("Created certbot certificate for %s", host)
        except subprocess.CalledProcessError:
            self.logger.exception("Could not create certbot certificate for %s", host)
            return False
        return self.__exists_certbot(host)
