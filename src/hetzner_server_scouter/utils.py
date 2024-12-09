from __future__ import annotations

import asyncio
import inspect
import logging
import os
import re
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, Action
from asyncio import AbstractEventLoop, get_event_loop
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from pathlib import Path
from traceback import format_exception
from typing import TypeVar, Callable, Iterable, Any, TYPE_CHECKING

import itertools
import requests
import sys
from time import perf_counter

from hetzner_server_scouter.settings import is_linux, is_macos, is_testing, is_windows, working_dir_location, database_url, Datacenters, error_text
from hetzner_server_scouter.version import __version__

if TYPE_CHECKING:
    from hetzner_server_scouter.db.models import Server


def print_version() -> None:
    # This is such an ingenious solution constructed by ChatGPT
    os_string = {is_windows: "Windows", is_macos: "MacOS", is_linux: "Linux"}.get(True, "Unknown OS")
    database_string = {"sqlite" in database_url: "SQLite", "mariadb" in database_url: "MariaDB", "postgresql" in database_url: "PostgreSQL"}.get(True, "Unknown Database")

    # This is a bit talkative, but I like giving info
    print(f"""This is hscout version {__version__}, running on {os_string}

I am working in the directory \"{path()}\" to store data
I am using {database_string} as the database engine
""")


def startup() -> None:
    """The startup routine to ensure a valid directory structure"""
    os.makedirs(path(), exist_ok=True)


def path(*args: str | Path) -> Path:
    """Prepend the args with the dedicated eet_backend directory"""
    return Path(working_dir_location, *args)


def print_exception(ex: Exception) -> None:
    print(f"{error_text} An unexpected error has occured:\n{chr(10).join(format_exception(ex))}", flush=True)


def parse_args() -> Namespace:
    """Parse the command line arguments"""
    parser = ArgumentParser(prog="hscout", formatter_class=lambda prog: RawTextHelpFormatter(prog, max_help_position=31), description="""A tool to watch and get notified about updates on the hetzner server auction""")

    parser.add_argument("-v", "--verbose", help="Make the application more verbose", action="count", default=0)
    parser.add_argument("-d", "--debug", help="Debug the application (triggers debug asserts and highest log level)", action="store_true")
    parser.add_argument("-V", "--version", help="Print the version", action="store_true")

    parser.add_argument("--tax", metavar="<tax>", type=int, action=Percentage, default=19, help="Set the tax rate  [default: 19]")

    filter_group = parser.add_argument_group("Available Filters")
    filter_group.add_argument("--price", metavar="<price>", type=int, help="Filter by price (in €)")
    filter_group.add_argument("--cpu", type=str, help="Filter by CPU model")
    filter_group.add_argument("--datacenter", choices=[it.value for it in Datacenters], nargs="+", help="Filter by datacenter")
    filter_group.add_argument("--ram", metavar="<GB>", type=int, help="Filter by RAM size")

    disk_group = parser.add_argument_group("Disks")
    disk_group.add_argument("--disk-num", metavar="<num>", type=int, help="The number of disks the server should have")
    disk_group.add_argument("--disk-num-quick", metavar="<num>", type=int, help="The number of SATA / NVME disks the server should have")
    disk_group.add_argument("--disk-size", metavar="<size>", type=int, help="The minimum size (in GB) of *each* disk")
    disk_group.add_argument("--disk-size-any", metavar="<size>", type=int, help="The minimum size (in GB) of any disk")
    disk_group.add_argument("--disk-size-raid0", metavar="<size>", type=int, help="Set the minimum size (in GB) of the resulting RAID when using all the drives")
    disk_group.add_argument("--disk-size-redundant", metavar="<size>", type=int, help="Set the minimum size of a redundant disk configuration if you don't care about if it is 1 / 5 / 6")
    disk_group.add_argument("--disk-size-raid1", metavar="<size>", type=int)
    disk_group.add_argument("--disk-size-raid5", metavar="<size>", type=int)
    disk_group.add_argument("--disk-size-raid6", metavar="<size>", type=int)

    specials_group = parser.add_argument_group("Require specials")
    specials_group.add_argument("--ipv4", action="store_true")
    specials_group.add_argument("--gpu", action="store_true")
    specials_group.add_argument("--inic", action="store_true")
    specials_group.add_argument("--ecc", action="store_true")
    specials_group.add_argument("--hwr", action="store_true")

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


def datetime_nullable_fromtimestamp(it: int | None) -> datetime | None:
    if it is None:
        return None

    return datetime.fromtimestamp(it)


def datetime_nullable_fromisoformat(it: str | None) -> datetime | None:
    if it is None:
        return None

    return datetime.fromisoformat(it)


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


class Percentage(Action):
    def __call__(self, parser: ArgumentParser, namespace: Namespace, values: Any, option_string: str | None = None) -> None:
        if 0 <= values <= 100:
            setattr(namespace, self.dest, values)
        else:
            parser.error(f"{option_string or self.dest} must be between 0 and 100.")


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


@dataclass
class RateLimiter:
    rate_s: int
    rate_m: int

    tokens_s: list[float] = field(default_factory=list)
    tokens_m: list[float] = field(default_factory=list)

    async def wait(self) -> None:
        while len(self.tokens_s) >= self.rate_s or len(self.tokens_m) >= self.rate_m:
            # Remove expired tokens
            now = perf_counter()
            self.tokens_s = [t for t in self.tokens_s if t > now - 1]
            self.tokens_m = [t for t in self.tokens_m if t > now - 60]

            await asyncio.sleep(0.1)

        now = perf_counter()
        self.tokens_s.append(now)
        self.tokens_m.append(now)


def filter_none(it: list[T | None]) -> list[T]:
    return [item for item in it if item is not None]


# -/- More or less useful functions ---

# --- Hetzner API ---

def get_hetzner_ipv4_price() -> float | None:
    req = requests.get("https://docs.hetzner.com/de/general/others/ipv4-pricing/", headers={"User-Agent": "Mozilla/5.0"})
    if not req.ok:
        return None

    it = re.search(r"Primäre IPv4[\w</>\s]*(\d,\d\d)\s*€ pro Monat", req.text)
    if it is None:
        return None

    try:
        return float(it.group(1).replace(",", "."))
    except Exception:
        return None


def filter_server_with_program_args(server: Server) -> Server | None:
    if program_args.price and server.calculate_price() > program_args.price:
        return None

    if program_args.cpu and program_args.cpu.lower() not in server.cpu_name.lower():
        return None

    if program_args.datacenter and server.datacenter not in {Datacenters.from_data(it) for it in program_args.datacenter}:
        return None

    if program_args.ram and server.ram_size < program_args.ram:
        return None

    # Now, check for the disks
    num_quick_disks = len(server.nvme_disks) + len(server.sata_disks)
    if program_args.disk_num and num_quick_disks + len(server.hdd_disks) < program_args.disk_num:
        return None

    if program_args.disk_num_quick and num_quick_disks < program_args.disk_num_quick:
        return None

    if program_args.disk_size or program_args.disk_size_any:
        max_size_seen = 0
        for disk in server.hdd_disks + server.sata_disks + server.nvme_disks:
            max_size_seen = max(max_size_seen, disk)

            if program_args.disk_size and disk < program_args.disk_size:
                return None

        if program_args.disk_size_any and max_size_seen < program_args.disk_size_any:
            return None

    # Now check if the server satisfies the required raid size
    all_disks = [it for it in server.hdd_disks + server.sata_disks + server.nvme_disks]
    if not all_disks:
        return None

    min_disk_size = min(all_disks)

    raid0_size = sum(all_disks)
    raid1_size = min_disk_size * len(all_disks) // 2
    raid5_size = min_disk_size * (len(all_disks) - 1)
    raid6_size = min_disk_size * (len(all_disks) - 2)

    cant_raid1 = lambda size: size and raid1_size < size
    cant_raid5 = lambda size: size and (len(all_disks) < 3 or raid5_size < size)
    cant_raid6 = lambda size: size and (len(all_disks) < 4 or raid6_size < size)

    if (it := program_args.disk_size_redundant) and cant_raid1(it) and cant_raid5(it) and cant_raid6(it):
        return None
    else:
        if cant_raid1(program_args.disk_size_raid1):
            return None
        if cant_raid5(program_args.disk_size_raid5):
            return None
        if cant_raid6(program_args.disk_size_raid6):
            return None

    # Finally, check for specials
    if program_args.ipv4 and not server.specials.has_IPv4:
        return None
    if program_args.gpu and not server.specials.has_GPU:
        return None
    if program_args.inic and not server.specials.has_iNIC:
        return None
    if program_args.ecc and not server.specials.has_ECC:
        return None
    if program_args.hwr and not server.specials.has_HWR:
        return None

    return server


def hetzner_notify_format_disks(disks: list[int], kind: str) -> list[str]:
    return [
        f"{disks.count(disk)}× {f'{round(disk / 1000, 1)}TB' if disk >= 1000 else f'{disk}GB'} ({kind})"
        for disk in sorted(set(disks))
    ]


def hetzner_notify_calculate_price_time_decrease(time_of_next_price_reduce: datetime | None) -> str:
    if time_of_next_price_reduce is None:
        return ""

    time_left_in_s = int((time_of_next_price_reduce - datetime.now()).total_seconds())
    hours_left = time_left_in_s // 3600
    minutes_left = (time_left_in_s // 60) % 60

    return f"decreasing in {f'{hours_left}h ' if hours_left else ''}{minutes_left}min"


# -/- Hetzner API ---

T = TypeVar("T")
U = TypeVar("U")
KT = TypeVar("KT")

startup()
program_args = parse_args()
logger = create_logger(program_args.verbose)

hetzner_ipv4_price = get_hetzner_ipv4_price()
DEBUG_ASSERTS = program_args.debug
