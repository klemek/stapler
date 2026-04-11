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

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "Parameters":
        return Parameters(**vars(args))


def parse_parameters() -> Parameters:
    parser = argparse.ArgumentParser(
        project.get_name(), description=project.get_description()
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8080, help="server port (default: 8080)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="server default host (default: localhost)",
    )
    parser.add_argument(
        "-d",
        "--data-dir",
        help="directory where files are/will be stored",
        default=os.path.join(os.getcwd(), "data"),
    )
    parser.add_argument(
        "-b",
        "--bind",
        default="0.0.0.0",
        help="server bind address (default: 0.0.0.0)",
    )
    args = parser.parse_args()
    return Parameters.from_namespace(args)
