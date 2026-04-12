import enum
import logging
import typing

if typing.TYPE_CHECKING:
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

    @typing.override
    def __add__(self, value: typing.Any, /) -> str:  # ty:ignore[invalid-method-override]
        return str(self) + str(value)

    def __radd__(self, value: typing.Any, /) -> str:
        return str(value) + str(self)


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

    FORMAT_COLORS: typing.ClassVar[dict[int, TermColor | str]] = {
        logging.DEBUG: TermColor.FEINT + TermColor.GREY,
        logging.INFO: TermColor.GREEN,
        logging.WARNING: TermColor.YELLOW,
        logging.ERROR: TermColor.RED,
        logging.CRITICAL: TermColor.RED,
    }

    @typing.override
    def __init__(self, trace: bool) -> None:
        self.trace = trace
        super().__init__()

    @typing.override
    def format(self, record: logging.LogRecord) -> str:
        log_color: TermColor | str = self.FORMAT_COLORS.get(
            record.levelno,
            TermColor.MAGENTA,
        )
        formatter = logging.Formatter(
            self.pre_format
            + log_color
            + TermColor.BOLD
            + self.level_format
            + TermColor.RESET
            + self.post_format
            + (self.trace_format if self.trace else ""),
        )
        return formatter.format(record)


def setup_logs(params: params.Parameters) -> None:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(ColoredLoggingFormatter(trace=params.debug))
    log_level = logging.INFO
    if params.debug:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, handlers=[stream_handler])
