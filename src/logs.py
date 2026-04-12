import enum
import logging

from . import params


class TermColor(enum.StrEnum):
    RESET = "0"
    BOLD = "1"
    FEINT = "2"
    UNDERLINE = "4"

    BLACK = "30"
    RED = "31"
    GREEN = "32"
    YELLOW = "33"
    BLUE = "34"
    MAGENTA = "35"
    CYAN = "36"
    WHITE = "37"
    GREY = "38"

    def __str__(self) -> str:
        return f"\033[{self.value}m"

    def __add__(self, second):
        return str(self) + str(second)

    def __radd__(self, second):
        return str(second) + str(self)


class ColoredLoggingFormatter(logging.Formatter):
    pre_format = "%(asctime)s | "
    level_format = "%(levelname)-8s"
    post_format = " | [%(name)s] %(message)s"
    trace_format = (
        TermColor.FEINT
        + TermColor.GREY
        + " (%(filename)s:%(lineno)d)"
        + TermColor.RESET
    )

    FORMAT_COLORS = {
        logging.DEBUG: TermColor.FEINT + TermColor.GREY,
        logging.INFO: TermColor.GREEN,
        logging.WARNING: TermColor.YELLOW,
        logging.ERROR: TermColor.RED,
        logging.CRITICAL: TermColor.RED,
    }

    def __init__(self, trace: bool):
        self.trace = trace

    def format(self, record):
        log_color: TermColor = (
            self.FORMAT_COLORS[record.levelno]
            if record.levelno in self.FORMAT_COLORS
            else TermColor.MAGENTA
        )
        formatter = logging.Formatter(
            self.pre_format
            + log_color
            + TermColor.BOLD
            + self.level_format
            + TermColor.RESET
            + self.post_format
            + (self.trace_format if self.trace else "")
        )
        return formatter.format(record)


def setup_logs(params: params.Parameters):
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(ColoredLoggingFormatter(trace=params.debug))
    log_level = logging.INFO
    if params.debug:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, handlers=[stream_handler])
