from __future__ import annotations

import os
import platform
import requests
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NoReturn, Any, cast

error_text = "\033[1;91mError:\033[0m"
warning_text = "\033[1;33mWarning:\033[0m"


def error_exit(code: int, reason: str) -> NoReturn:
    print(f"{error_text} {reason}", flush=True)
    os._exit(code)


# --- General settings ---

# The directory where everything lives in.
working_dir_location = Path(os.path.dirname(__file__), "resources")

# A constant to detect if you are on Linux.
is_linux = platform.system() == "Linux"

# A constant to detect if you are on macOS.
is_macos = platform.system() == "Darwin"

# A constant to detect if you are on Windows.
is_windows = platform.system() == "Windows"

# The Separator
separator = ""

# -/- General settings ---


# --- Test Settings ---


# Yes, changing behaviour when testing is evil.
is_testing = "pytest" in sys.modules
if is_testing:
    pass


# -/- Test Settings ---


# --- Database Configuration ---

def _make_db_name(db_name: str) -> str:
    return "test_" + db_name if is_testing else db_name


def db_make_sqlite_url(db_name: str) -> str:
    return f"sqlite:///{os.path.join(working_dir_location, _make_db_name(db_name))}"


def db_make_mariadb_url(user: str, pw: str, db_name: str) -> str:
    return f"mariadb+mariadbconnector://{user}:{pw}@localhost:3306/{_make_db_name(db_name)}"


def db_make_postgres_url(user: str, pw: str, db_name: str) -> str:
    return f"postgresql+psycopg2://{user}:{pw}@localhost:5432/{_make_db_name(db_name)}"


# First, the database url is tried. If it doesn't work, the `sqlite_database_name` together with the working dir is tried. If both error, the program is halted.
sqlite_database_name = "state.db"
database_url = db_make_sqlite_url(sqlite_database_name)

# If set to True all the emitted SQL is echo'd back
database_verbose_sql = False

# -/- Database Configuration ---

# --- Hetzner API specifics ---

hetzner_api_url = "https://www.hetzner.com/_resources/app/jsondata/live_data_sb.json"
hetzner_api_get_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}


def get_hetzner_api() -> dict[str, Any] | None:
    """Fetches the live hetzner data, pretending to be a Chrome instance from Windows 10."""

    response = requests.get(
        "https://www.hetzner.com/_resources/app/data/app/live_data_sb_EUR.json",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"}
    )

    if not response.ok:
        return None

    return cast(dict[str, Any], response.json())


# Unfortunately, this class has to be here due to the shared dependency with utils.py
class Datacenters(Enum):
    frankfurt = "FSN"
    helsinki = "HEL"
    nurnberg = "NBG"

    @classmethod
    def from_data(cls, data: str | None) -> Datacenters | None:
        if data is None:
            return None
        elif "FSN" in data:
            return cls.frankfurt
        elif "HEL" in data:
            return cls.helsinki
        elif "NBG" in data:
            return cls.nurnberg

        return None

    def __str__(self) -> str:
        match self:
            case Datacenters.frankfurt:
                return "Frankfurt"

            case Datacenters.helsinki:
                return "Helsinki"

            case Datacenters.nurnberg:
                return "Nürnberg"

            case _:
                return "Unknown location"  # type:ignore[unreachable]


@dataclass
class ServerSpecials:
    has_IPv4: bool
    has_GPU: bool
    has_iNIC: bool
    has_ECC: bool
    has_HWR: bool  # Hardware RAID

# -/- Hetzner API specifics ---
