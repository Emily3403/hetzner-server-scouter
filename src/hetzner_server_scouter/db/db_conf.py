from __future__ import annotations

import os
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import declarative_base, DeclarativeMeta, sessionmaker
from typing import Type, TypeVar

from hetzner_server_scouter.settings import error_exit, database_url, db_make_sqlite_url, sqlite_database_name, database_verbose_sql, warning_text
from hetzner_server_scouter.utils import path

if "sqlite" in database_url:
    connect_args = {"check_same_thread": False}
    isolation_level = "SERIALIZABLE"
else:
    connect_args = {}
    isolation_level = "READ COMMITTED"


def make_engine() -> Engine:
    engine = create_engine(database_url, connect_args=connect_args, isolation_level=isolation_level, echo=database_verbose_sql)
    engine.connect()
    return engine


# Make sure the path exists
os.makedirs(path(), exist_ok=True)

try:
    database_engine = make_engine()

except Exception as ex:
    # If the connection failed, try again with SQLite
    new_url = db_make_sqlite_url(sqlite_database_name)
    if new_url == database_url:
        error_exit(1, f"Database connection to the url `{database_url}` failed:\n{ex}")

    print(f"{warning_text} Initial database connection failed: {ex}\nTrying again with SQLite ...\033[0m")
    try:
        database_engine = make_engine()
    except Exception as ex:
        error_exit(1, f"Connecting with SQLite also failed: {ex}\nBailing out!")


class DatabaseObject:
    __tablename__: str
    __allow_unmapped__ = True

    def __str__(self) -> str:
        return f"{type(self).__name__}"

    def __repr__(self) -> str:
        return self.__str__()


# This Callable can be used to create new Session objects for interacting with a database
DatabaseSessionMaker = sessionmaker(autocommit=False, bind=database_engine)
DataBase: Type[DeclarativeMeta] = declarative_base(cls=DatabaseObject)
DB_T = TypeVar("DB_T", bound=DatabaseObject)


def init_database() -> None:
    DataBase.metadata.create_all(bind=database_engine)
