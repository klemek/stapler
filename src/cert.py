import logging
import pathlib
import shutil
import ssl
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

    def get_cert(self, host: str) -> pathlib.Path:
        if self.__exists_certbot(host):
            return self.__certbot_file(host, self.CRT_FILE)
        if self.__exists_self_signed(host):
            return self.__self_signed_file(host, self.CRT_FILE)
        msg = "Cannot get cert file for %s"
        raise CertManagerError(msg, host)

    def get_key(self, host: str) -> pathlib.Path:
        if self.__exists_certbot(host):
            return self.__certbot_file(host, self.KEY_FILE)
        if self.__exists_self_signed(host):
            return self.__self_signed_file(host, self.KEY_FILE)
        msg = "Cannot get key file for %s"
        raise CertManagerError(msg, host)

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
            self.logger.debug("Created %s", cert_path)
        try:
            self.logger.debug("Creating self-signed certificate for %s...", host)
            subprocess.check_output(
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
                    f"/CN={host}",
                ],
                stderr=subprocess.STDOUT,
            )
            self.logger.info("Created self-signed certificate for %s", host)
        except subprocess.CalledProcessError as e:
            self.logger.exception(
                "Could not create self-signed certificate for %s\n%s",
                host,
                e.stdout.decode(),
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
        try:
            self.logger.debug("Creating certbot certificate for %s...", host)
            subprocess.check_output(
                [
                    self.__get_certbot_bin(),
                    "certonly",
                    "--non-interactive",
                    "--agree-tos",
                    "--webroot",
                    "--webroot-path",
                    self.certbot_www,
                    "--no-eff-email",
                    "--cert-name",
                    host,
                    "--domain",
                    host,
                ],
                stderr=subprocess.STDOUT,
            )
            self.logger.info("Created certbot certificate for %s", host)
            cert_path = self.certbot_conf / "live" / host
            dest_cert_path = self.self_signed_path / host
            if dest_cert_path.exists:
                shutil.rmtree(dest_cert_path)
            cert_path.copy_into(self.self_signed_path, follow_symlinks=False)
            self.logger.debug("Copied certbot certificate to self certificates")
        except subprocess.CalledProcessError as e:
            self.logger.exception(
                "Could not create certbot certificate for %s\n%s",
                host,
                e.stdout.decode(),
            )
            return False
        return self.__exists_certbot(host)

    def get_https_context(self, default_host: str) -> ssl.SSLContext | None:
        if not self.exists(default_host):
            self.logger.warning("Cannot create HTTPS context for %s", default_host)
            return None
        cert_file = self.get_cert(default_host)
        key_file = self.get_key(default_host)
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(
            cert_file,
            key_file,
        )
        context.sni_callback = self.__sni_callback
        return context

    def __sni_callback(
        self, socket: ssl.SSLObject, host: str, _: ssl.SSLContext, /
    ) -> None | int:
        if host is None:
            return
        if not self.exists(host) and not self.create_or_update(host):
            msg = "Could not get certificate for %s"
            raise CertManagerError(msg, host)
        new_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        cert_file = self.get_cert(host)
        key_file = self.get_key(host)
        new_context.load_cert_chain(
            cert_file,
            key_file,
        )
        socket.context = new_context
        return None
