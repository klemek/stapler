import argparse
import dataclasses
import os
import typing

from . import project

__EPILOG = "(Each option can be supplied with equivalent environment variable.)"


@dataclasses.dataclass(frozen=True)
class Parameters:
    debug: bool = False
    data_dir: str = "./data"
    with_certificates: bool = True
    self_signed_path: str = "./data/.certificates"
    with_certbot: bool = True
    certbot_conf: str = "/etc/letsencrypt"
    certbot_www: str = "./data/.certbot"
    host: str = "localhost"
    http_port: int = 80
    https_port: int = 443
    https: bool = True
    token_salt: str = ""
    max_size_bytes: int = 2_000_000
    bind: str = "0.0.0.0"
    command: typing.Literal["run", "renew", "token"] = "run"

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> Parameters:
        return Parameters(**vars(args))


def __get_env_str(var: str, default: str) -> str:
    if (result := os.getenv(var)) is None:
        return default
    return result


def __get_env_int(var: str, default: int) -> int:
    value = __get_env_str(var, str(default))
    if value.isnumeric():
        return int(value)
    return default


def __add_arg_str(
    parser: argparse.ArgumentParser,
    *flags: str,
    env_var: str,
    default: str,
    help_txt: str,
) -> None:
    parser.add_argument(
        *flags,
        metavar=env_var,
        default=__get_env_str(env_var, default),
        help=f"{help_txt} (default: {default})" if len(default) else help_txt,
    )


def __add_arg_int(
    parser: argparse.ArgumentParser,
    *flags: str,
    env_var: str,
    default: int,
    help_txt: str,
) -> None:
    parser.add_argument(
        *flags,
        type=int,
        metavar=env_var,
        default=__get_env_int(env_var, default),
        help=f"{help_txt} (default: {default})",
    )


def parse_parameters(args: typing.Sequence[str]) -> Parameters:
    default_values = Parameters()
    parser = argparse.ArgumentParser(
        project.get_name(),
        description=project.get_description(),
        epilog=__EPILOG,
        suggest_on_error=True,
    )
    parser.add_argument(
        "--debug", action=argparse.BooleanOptionalAction, default=default_values.debug
    )
    __add_arg_str(
        parser,
        "-d",
        "--data-dir",
        env_var="DATA_DIR",
        default=default_values.data_dir,
        help_txt="directory where pages are/will be stored",
    )
    parser.add_argument(
        "--certificates",
        action=argparse.BooleanOptionalAction,
        help="Handle certificates (default: true)",
        default=default_values.with_certificates,
        dest="with_certificates",
    )
    __add_arg_str(
        parser,
        "--self-signed-path",
        env_var="SELF_SIGNED_PATH",
        default=default_values.self_signed_path,
        help_txt="Self-signed certificates dir",
    )
    parser.add_argument(
        "--certbot",
        action=argparse.BooleanOptionalAction,
        help="Use Certbot (default: true)",
        default=default_values.with_certbot,
        dest="with_certbot",
    )
    __add_arg_str(
        parser,
        "--certbot-conf",
        env_var="CERTBOT_CONF",
        default=default_values.certbot_conf,
        help_txt="Certbot config dir",
    )
    __add_arg_str(
        parser,
        "--certbot-www",
        env_var="CERTBOT_WWW",
        default=default_values.certbot_www,
        help_txt="Certbot www dir",
    )
    __add_arg_str(
        parser,
        "--host",
        env_var="HOST",
        default=default_values.host,
        help_txt="server default host",
    )
    __add_arg_int(
        parser,
        "--http-port",
        env_var="HTTP_PORT",
        default=default_values.http_port,
        help_txt="server http port",
    )
    __add_arg_int(
        parser,
        "--https-port",
        env_var="HTTPS_PORT",
        default=default_values.https_port,
        help_txt="server https port",
    )
    parser.add_argument(
        "--https",
        action=argparse.BooleanOptionalAction,
        help="Use https (implies --certificates) (default: true)",
        default=default_values.https,
    )
    __add_arg_str(
        parser,
        "-t",
        "--token-salt",
        env_var="TOKEN_SALT",
        default=default_values.token_salt,
        help_txt="salt for tokens generation",
    )
    __add_arg_int(
        parser,
        "--max-size-bytes",
        env_var="MAX_SIZE",
        default=default_values.max_size_bytes,
        help_txt="max size of accepted archives (in bytes)",
    )
    __add_arg_str(
        parser,
        "-b",
        "--bind",
        env_var="BIND",
        default=default_values.bind,
        help_txt="server bind address",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")
    subparsers.add_parser("run", help="Run Stapler server")
    subparsers.add_parser("renew", help="Renew certificates")
    subparsers.add_parser("token", help="Generate a new token")
    parsed_args = parser.parse_args(args)
    if parsed_args.https:
        parsed_args.with_certificates = True
    return Parameters.from_namespace(parsed_args)
