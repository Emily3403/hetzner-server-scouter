from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession
from typing import Any

from hetzner_server_scouter.db.db_utils import add_object_to_database, database_transaction
from hetzner_server_scouter.db.models import Server
from hetzner_server_scouter.notifications.models import ServerChange
from hetzner_server_scouter.settings import get_hetzner_api
from hetzner_server_scouter.utils import filter_none


def read_servers(db: DatabaseSession) -> list[Server]:
    return list(db.execute(select(Server)).scalars().all())


def create_server_from_data(db: DatabaseSession, data: dict[str, Any], last_message_id: int | None = None) -> Server | None:
    return add_object_to_database(db, Server.from_data(data, last_message_id=last_message_id))


async def download_server_list(_api_data: dict[str, Any] | None = None) -> list[Server] | None:
    api_data = _api_data or get_hetzner_api()
    if api_data is None:
        return None

    return filter_none([Server.from_data(data) for data in api_data["server"]])


def update_server_list(db: DatabaseSession, _new_servers: list[Server]) -> list[ServerChange]:
    existing_servers = read_servers(db)
    new_servers = {it.id: it for it in _new_servers}

    updates = [server.update(db, new_servers.pop(server.id, None)) for server in existing_servers]
    new = [server.new(db) for server in new_servers.values()]

    database_transaction(db, lambda: None)
    return filter_none(updates) + new
