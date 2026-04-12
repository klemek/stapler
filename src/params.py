import argparse
import dataclasses
import os
import os.path

from . import project


@dataclasses.dataclass
class Parameters:
    port: int
    host: str
    data_dir: str
    bind: str
    token: str
    max_size_bytes: int
    certbot_conf: str
    certbot_www: str

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "Parameters":
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
    parser: argparse.ArgumentParser, *flags: str, env_var: str, default: str, help: str
):
    parser.add_argument(
        *flags,
        metavar=env_var,
        default=__get_env_str(env_var, default),
        help=f"{help} (default: {default})",
    )


def __add_arg_int(
    parser: argparse.ArgumentParser, *flags: str, env_var: str, default: int, help: str
):
    parser.add_argument(
        *flags,
        type=int,
        metavar=env_var,
        default=__get_env_int(env_var, default),
        help=f"{help} (default: {default})",
    )


def __add_arg_str_required(
    parser: argparse.ArgumentParser, *flags: str, env_var: str, help: str
):
    parser.add_argument(
        *flags,
        metavar=env_var,
        required=os.getenv(env_var) is None,
        default=os.getenv(env_var),
        help=f"{help}",
    )


def parse_parameters() -> Parameters:
    parser = argparse.ArgumentParser(
        project.get_name(),
        description=project.get_description(),
        epilog="(Each option can be supplied with equivalent environment variable.)",
    )
    __add_arg_int(
        parser, "-p", "--port", env_var="PORT", default=8080, help="server port"
    )
    __add_arg_str(
        parser,
        "--host",
        env_var="HOST",
        default="localhost",
        help="server default host",
    )
    __add_arg_str(
        parser,
        "-d",
        "--data-dir",
        env_var="DATA_DIR",
        default=os.path.join(".", "data"),
        help="directory where pages are/will be stored",
    )
    __add_arg_str_required(
        parser,
        "-t",
        "--token",
        env_var="TOKEN",
        help="secret token for update requests",
    )
    __add_arg_int(
        parser,
        "--max-size-bytes",
        env_var="MAX_SIZE",
        default=2_000_000,
        help="max size of accepted archives (in bytes)",
    )
    __add_arg_str(
        parser,
        "-b",
        "--bind",
        env_var="BIND",
        default="0.0.0.0",
        help="server bind address",
    )
    __add_arg_str(
        parser,
        "--certbot-conf",
        env_var="CERTBOT_CONF",
        default="/etc/letsencrypt",
        help="Certbot config dir",
    )
    __add_arg_str(
        parser,
        "--certbot-www",
        env_var="CERTBOT_WWW",
        default=os.path.join(".", "data", ".certbot"),
        help="Certbot www dir",
    )
    args = parser.parse_args()
    return Parameters.from_namespace(args)
