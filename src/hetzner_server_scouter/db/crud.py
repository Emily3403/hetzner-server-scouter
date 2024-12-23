from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_utils import database_transaction
from hetzner_server_scouter.db.models import Server, DiskType
from hetzner_server_scouter.notifications.models import ServerChange
from hetzner_server_scouter.settings import get_hetzner_api, is_testing
from hetzner_server_scouter.utils import filter_none


def read_servers(db: DatabaseSession) -> list[Server]:
    return list(db.execute(select(Server)).scalars().all())


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


def create_disk_type_from_string(string: str) -> tuple[DiskType, int]:
    _size, unit, *rest = string.split(" ")
    is_enterprise = "Enterprise" in rest or "Datacenter" in rest

    if unit == "GB":
        size = int(_size)
    elif unit == "TB":
        size = int(round(float(_size) * 1000, 0))
    elif unit == "PB":
        size = int(round(float(_size) * 1000 ** 2, 0))
    else:
        # If disk sizes ever exceed Petabytes, I'll eat a broom
        assert False, f"Wrong unit detected: {unit!r}"

    if "HDD" in rest:
        if is_enterprise:
            return "enterprise_hdd", size
        else:
            return "hdd", size
    if "SSD" in rest:
        if is_enterprise:
            return "enterprise_ssd", size
        else:
            return "ssd", size

    assert False, f"Wrong Disk Type detected: {' '.join(rest)}"


def create_disk_dict_from_hdd_arr(hdd_arr: list[str], server_disk_data: dict[str, list[int]]) -> dict[DiskType, list[int]]:
    disks = defaultdict(list)

    for disk in hdd_arr:
        disk_type, disk_size = create_disk_type_from_string(disk)
        disks[disk_type].append(disk_size)

    if is_testing or True:
        assert sorted(server_disk_data["hdd"]) == sorted(disks["hdd"] + disks["enterprise_hdd"])
        assert sorted(server_disk_data["sata"] + server_disk_data["nvme"]) == sorted(disks["ssd"] + disks["enterprise_ssd"])

    return disks
