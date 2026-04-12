from src.params import parse_parameters
from src.server import StaplerServer
from src.logs import setup_logs


def main():
    params = parse_parameters()
    setup_logs(params)
    server = StaplerServer(params)
    server.start()


if __name__ == "__main__":
    main()
