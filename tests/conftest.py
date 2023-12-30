import copy
from typing import Generator, Any

from pytest import fixture
from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_conf import DatabaseSessionMaker, init_database
from hetzner_server_scouter.settings import get_hetzner_api
from hetzner_server_scouter.utils import startup, program_args


class MockProgramsArgs:

    def __init__(self, **kwargs: Any):
        self.kwargs = kwargs
        self.prev_args = copy.deepcopy(program_args)

    def __enter__(self) -> None:
        for k, v in self.kwargs.items():
            setattr(program_args, k, v)

    def __exit__(self, *args: Any) -> None:
        for k in self.kwargs:
            setattr(program_args, k, getattr(self.prev_args, k))


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
