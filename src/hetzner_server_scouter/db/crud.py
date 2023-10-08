from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_utils import add_object_to_database, add_objects_to_database
from hetzner_server_scouter.db.models import Server
from hetzner_server_scouter.notify.change_notifier import ChangeNotifier
from hetzner_server_scouter.notify.models import ServerChange, ServerChangeType
from hetzner_server_scouter.settings import get_hetzner_api


def read_servers(db: DatabaseSession) -> list[Server]:
    return list(db.execute(select(Server)).scalars().all())


def read_servers_to_ids(db: DatabaseSession) -> dict[int, Server]:
    return {it.id: it for it in read_servers(db)}


def create_server_from_data(db: DatabaseSession, data: dict[str, Any]) -> Server | None:
    return add_object_to_database(db, Server.from_data(data))


def process_changes(updated_servers: list[tuple[Server, Server | None]], deleted_servers: list[Server]) -> None:
    updated_changes = [new.process_change(old) for new, old in updated_servers]
    deleted_changes = [ServerChange(ServerChangeType.sold, it.id, it.last_message_id, "", "", "") for it in deleted_servers]

    changes = updated_changes + deleted_changes
    _ = changes
    pass


def download_server_list(db: DatabaseSession, notifier: ChangeNotifier) -> list[Server] | None:
    api_data = get_hetzner_api()
    if api_data is None:
        return None

    existing_servers = read_servers_to_ids(db)
    servers_to_update: list[tuple[Server, Server | None]] = []

    for data in api_data["server"]:
        server = Server.from_data(data)
        maybe_server = existing_servers.pop(data["id"], None)

        if server == maybe_server:
            continue

        servers_to_update.append((server, maybe_server))

    # First delete all old servers
    server_ids = [it.id for (_, it) in servers_to_update if it is not None]
    if server_ids:
        db.execute(delete(Server).where(Server.id.in_(server_ids)))

    # Next, insert all new ones and process the changes
    new_servers = add_objects_to_database(db, [it for (it, _) in servers_to_update])
    process_changes(servers_to_update, list(existing_servers.values()))
    return new_servers
