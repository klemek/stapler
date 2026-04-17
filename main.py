import sys

from src.logs import setup_logs
from src.params import parse_parameters
from src.server import StaplerServer


def main() -> None:
    params = parse_parameters(sys.argv[1:])
    setup_logs(params)
    server = StaplerServer(params)
    method = getattr(server, params.command)
    sys.exit(method())


if __name__ == "__main__":
    main()
