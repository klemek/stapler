from src.logs import setup_logs
from src.params import parse_parameters
from src.server import StaplerServer


def main() -> None:
    params = parse_parameters()
    setup_logs(params)
    server = StaplerServer(params)
    server.start()


if __name__ == "__main__":
    main()
