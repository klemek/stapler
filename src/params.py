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


def parse_parameters() -> Parameters:
    parser = argparse.ArgumentParser(
        project.get_name(), description=project.get_description()
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=__get_env_int("PORT", 8080),
        help="server port (default: 8080) (env var: PORT)",
    )
    parser.add_argument(
        "--host",
        default=__get_env_str("HOST", "localhost"),
        help="server default host (default: localhost) (env var: HOST)",
    )
    parser.add_argument(
        "-d",
        "--data-dir",
        default=__get_env_str("DATA_DIR", os.path.join(os.getcwd(), "data")),
        help="directory where files are/will be stored (default: ./data) (env var: DATA_DIR)",
    )
    parser.add_argument(
        "-b",
        "--bind",
        default=__get_env_str("BIND", "0.0.0.0"),
        help="server bind address (default: 0.0.0.0) (env var: BIND)",
    )
    parser.add_argument(
        "-t",
        "--token",
        required=os.getenv("TOKEN") is None,
        default=os.getenv("TOKEN"),
        help="secret token for update requests (env var: TOKEN)",
    )
    args = parser.parse_args()
    return Parameters.from_namespace(args)
