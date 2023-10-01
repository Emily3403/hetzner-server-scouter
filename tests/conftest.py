from typing import Generator

from pytest import fixture
from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_conf import DatabaseSessionMaker, init_database
from hetzner_server_scouter.utils import startup


def pytest_configure() -> None:
    startup()


@fixture(scope="session")
def db() -> Generator[DatabaseSession, None, None]:
    init_database()

    with DatabaseSessionMaker() as session:
        yield session
