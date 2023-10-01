from __future__ import annotations

import asyncio
import inspect
import itertools
import logging
import os
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter
from asyncio import AbstractEventLoop, get_event_loop
from functools import wraps
from pathlib import Path
from time import perf_counter
from typing import TypeVar, Callable, Iterable, Any

from hetzner_server_scouter.settings import is_linux, is_macos, is_testing, is_windows, working_dir_location, database_url
from hetzner_server_scouter.version import __version__


def print_version() -> None:
    # This is such an ingenious solution constructed by ChatGPT
    os_string = {is_windows: "Windows", is_macos: "MacOS", is_linux: "Linux"}.get(True, "Unknown OS")
    database_string = {"sqlite" in database_url: "SQLite", "mariadb" in database_url: "MariaDB", "postgresql" in database_url: "PostgreSQL"}.get(True, "Unknown Database")

    # This is a bit talkative, but I like giving info
    print(
        f"This is hetzner-server-scouter with version: {__version__}\n"
        f"I am running on {os_string}\n"
        f"I am working in the directory \"{path()}\" to store data\n"
        f"I am using {database_string} as the database engine\n"
    )


def startup() -> None:
    """The startup routine to ensure a valid directory structure"""
    os.makedirs(path(), exist_ok=True)


def path(*args: str | Path) -> Path:
    """Prepend the args with the dedicated eet_backend directory"""
    return Path(working_dir_location, *args)


def parse_args() -> Namespace:
    """Parse the command line arguments"""
    parser = ArgumentParser(prog="hetzner-server-scouter", formatter_class=RawTextHelpFormatter, description="""A tool to watch and get notified about updates on the hetzner server auction""")

    # Arguments that you can always add
    parser.add_argument("-v", "--verbose", help="Make the application more verbose", action="count", default=0)
    parser.add_argument("-d", "--debug", help="Debug the application", action="store_true")

    # Mutually exclusive arguments
    operations = parser.add_mutually_exclusive_group()
    operations.add_argument("-V", "--version", help="Print the version number and exit", action="store_true")

    if is_testing:
        # Pytest adds extra arguments that don't fit into the defined schema.
        return parser.parse_known_args()[0]

    parsed_args = parser.parse_args()

    # Now modify the arguments based on each other
    if parsed_args.debug:
        parsed_args.verbose = 3

    return parsed_args


def create_logger(verbose_level: int) -> logging.Logger:
    """
    Creates the logger
    """
    # disable DEBUG messages from various modules
    logging.getLogger("urllib3").propagate = False
    logging.getLogger("selenium").propagate = False
    logging.getLogger("matplotlib").propagate = False
    logging.getLogger("PIL").propagate = False
    logging.getLogger("oauthlib").propagate = False
    logging.getLogger("requests_oauthlib.oauth1_auth").propagate = False

    debug_level = {1: logging.WARNING, 2: logging.INFO, 3: logging.DEBUG}.get(verbose_level, logging.ERROR)

    logger = logging.getLogger()
    logger.setLevel(debug_level)

    if not is_windows:
        # Add a colored console handler. This only works on UNIX, however I use that. If you don't maybe reconsider using windows :P
        import coloredlogs  # type: ignore
        coloredlogs.install(level=debug_level, fmt='%(asctime)s [%(levelname)s] %(message)s')
    else:
        # Windows users don't have colorful logs :(
        # Legacy solution that should work for windows.
        #
        # Warning:
        #   This is untested.
        #   I think it should work but if not, feel free to submit a bug report!

        ch = logging.StreamHandler(stream=sys.stdout)
        console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
        ch.setLevel(debug_level)
        ch.setFormatter(console_formatter)
        logger.addHandler(ch)

    logging.info("Starting up…")

    return logger


# --- More or less useful functions ---

def get_input(allowed: set[str]) -> str:
    while True:
        choice = input()
        if choice in allowed:
            break

        print(f"Unhandled character: {choice!r} is not in the expected {{" + ", ".join(repr(item) for item in sorted(list(allowed))) + "}\nPlease try again.\n")

    return choice


def flat_map(func: Callable[[T], Iterable[U]], it: Iterable[T]) -> Iterable[U]:
    return itertools.chain.from_iterable(map(func, it))


def get_async_time(event_loop: AbstractEventLoop | None = None) -> float:
    return (event_loop or get_event_loop()).time()


def queue_get_nowait(q: asyncio.Queue[T]) -> T | None:
    try:
        return q.get_nowait()
    except Exception:
        return None


# Adapted from https://stackoverflow.com/a/5929165 and https://stackoverflow.com/a/36944992
def debug_time(str_to_put: str | None = None, func_to_call: Any = None, debug_level: int = logging.DEBUG) -> Callable[[Any], Any]:
    def decorator(function: Any) -> Any:
        @wraps(function)
        def _self_impl(self: Any, *method_args: Any, **method_kwargs: Any) -> Any:
            logger.log(debug_level, f"Starting: {str_to_put if func_to_call is None else func_to_call(self)}")
            s = perf_counter()

            method_output = function(self, *method_args, **method_kwargs)
            logger.log(debug_level, f"Finished: {str_to_put if func_to_call is None else func_to_call(self)} in {perf_counter() - s:.3f}s")

            return method_output

        def _impl(*method_args: Any, **method_kwargs: Any) -> Any:
            logger.log(debug_level, f"Starting: {str_to_put}")
            s = perf_counter()

            method_output = function(*method_args, **method_kwargs)
            logger.log(debug_level, f"Finished: {str_to_put} in {perf_counter() - s:.3f}s")

            return method_output

        if "self" in inspect.getfullargspec(function).args:
            return _self_impl

        return _impl

    return decorator


# Copied and adapted from https://stackoverflow.com/a/63839503
class HumanBytes:
    @staticmethod
    def format(num: float) -> tuple[float, str]:
        """
        Human-readable formatting of bytes, using binary (powers of 1024) representation.

        Note: num > 0
        """

        unit_labels = ["  B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
        last_label = unit_labels[-1]
        unit_step = 1024
        unit_step_thresh = unit_step - 0.5

        for unit in unit_labels:
            if num < unit_step_thresh:
                # Only return when under the rounding threshold
                break
            if unit != last_label:
                num /= unit_step

        return num, unit

    @staticmethod
    def format_str(num: float | None) -> str:
        if num is None:
            return "?"

        n, unit = HumanBytes.format(num)
        return f"{n:.2f} {unit}"

    @staticmethod
    def format_pad(num: float | None) -> str:
        if num is None:
            return "   ?"

        n, unit = HumanBytes.format(num)
        return f"{f'{n:.2f}'.rjust(6)} {unit}"


# -/- More or less useful functions ---

T = TypeVar("T")
U = TypeVar("U")
KT = TypeVar("KT")

startup()
program_args = parse_args()
logger = create_logger(program_args.verbose)

DEBUG_ASSERTS = program_args.debug
