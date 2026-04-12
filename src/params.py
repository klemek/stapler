import argparse
import dataclasses
import os

from . import project


@dataclasses.dataclass(frozen=True)
class Parameters:
    port: int
    host: str
    data_dir: str
    bind: str
    token: str
    max_size_bytes: int
    certbot_conf: str
    certbot_www: str
    self_signed_path: str
    with_certbot: bool
    with_certificates: bool
    https: bool
    debug: bool

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
        help=f"{help_txt} (default: {default})",
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


def __add_arg_str_required(
    parser: argparse.ArgumentParser,
    *flags: str,
    env_var: str,
    help_txt: str,
) -> None:
    parser.add_argument(
        *flags,
        metavar=env_var,
        required=os.getenv(env_var) is None,
        default=os.getenv(env_var),
        help=help_txt,
    )


def parse_parameters() -> Parameters:
    parser = argparse.ArgumentParser(
        project.get_name(),
        description=project.get_description(),
        epilog="(Each option can be supplied with equivalent environment variable.)",
    )
    __add_arg_int(
        parser,
        "-p",
        "--port",
        env_var="PORT",
        default=8080,
        help_txt="server port",
    )
    __add_arg_str(
        parser,
        "--host",
        env_var="HOST",
        default="localhost:8080",
        help_txt="server default host",
    )
    __add_arg_str(
        parser,
        "-d",
        "--data-dir",
        env_var="DATA_DIR",
        default="./data",
        help_txt="directory where pages are/will be stored",
    )
    __add_arg_str_required(
        parser,
        "-t",
        "--token",
        env_var="TOKEN",
        help_txt="secret token for update requests",
    )
    __add_arg_int(
        parser,
        "--max-size-bytes",
        env_var="MAX_SIZE",
        default=2_000_000,
        help_txt="max size of accepted archives (in bytes)",
    )
    __add_arg_str(
        parser,
        "-b",
        "--bind",
        env_var="BIND",
        default="0.0.0.0",
        help_txt="server bind address",
    )
    __add_arg_str(
        parser,
        "--certbot-conf",
        env_var="CERTBOT_CONF",
        default="/etc/letsencrypt",
        help_txt="Certbot config dir",
    )
    __add_arg_str(
        parser,
        "--certbot-www",
        env_var="CERTBOT_WWW",
        default="./data/.certbot",
        help_txt="Certbot www dir",
    )
    __add_arg_str(
        parser,
        "--self-signed-path",
        env_var="SELF_SIGNED_PATH",
        default="./data/.certificates",
        help_txt="Self-signed certificates dir",
    )
    parser.add_argument("--debug", action=argparse.BooleanOptionalAction)
    parser.add_argument(
        "--certbot",
        action=argparse.BooleanOptionalAction,
        help="Use Certbot (default: false)",
        default=False,
        dest="with_certbot",
    )
    parser.add_argument(
        "--certificates",
        action=argparse.BooleanOptionalAction,
        help="Handle certificates (default: true)",
        default=True,
        dest="with_certificates",
    )
    parser.add_argument(
        "--https",
        action=argparse.BooleanOptionalAction,
        help="Use https (implies --certificates) (default: true)",
        default=True,
    )
    args = parser.parse_args()
    if args.https:
        args.with_certificates = True
    return Parameters.from_namespace(args)
