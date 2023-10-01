from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import NoReturn

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
