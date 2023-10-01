from typing import Generator, Any

from pytest import fixture
from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_conf import DatabaseSessionMaker, init_database
from hetzner_server_scouter.settings import get_hetzner_api
from hetzner_server_scouter.utils import startup


def pytest_configure() -> None:
    startup()


@fixture(scope="session")
def db() -> Generator[DatabaseSession, None, None]:
    init_database()

    with DatabaseSessionMaker() as session:
        yield session


@fixture(scope="session")
def data() -> Generator[dict[str, Any], None, None]:
    data = get_hetzner_api()
    assert data is not None

    yield data
