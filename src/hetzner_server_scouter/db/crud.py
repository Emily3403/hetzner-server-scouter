from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_utils import add_object_to_database, add_objects_to_database
from hetzner_server_scouter.db.models import Server
from hetzner_server_scouter.settings import get_hetzner_api, Datacenters, ServerSpecials
from hetzner_server_scouter.utils import datetime_nullable_fromtimestamp


def read_servers(db: DatabaseSession) -> list[Server]:
    return list(db.execute(select(Server)).scalars().all())


def read_servers_to_ids(db: DatabaseSession) -> dict[int, Server]:
    return {it.id: it for it in read_servers(db)}


def create_server(
    db: DatabaseSession, id: int, price: float, next_price_reduce: int | None, datacenter: str,
    cpu_name: str, ram_size: int, ram_description: str, disk_mapping: dict[str, list[int]],
    has_IPv4: bool, has_GPU: bool, has_iNIC: bool, has_ECC: bool, has_HWR: bool,
) -> Server | None:
    #
    return add_object_to_database(db, Server(
        id=id, price=price, time_of_next_price_reduce=datetime_nullable_fromtimestamp(next_price_reduce), datacenter=Datacenters.from_data(datacenter),
        cpu_name=cpu_name, ram_size=ram_size, ram_num=int(ram_description[0][0]), disks=disk_mapping, specials=ServerSpecials(has_IPv4, has_GPU, has_iNIC, has_ECC, has_HWR)
    ))


def bulk_create_server_from_data(db: DatabaseSession, data: list[dict[str, Any]]) -> list[Server] | None:
    servers = [
        Server(
            id=dat["id"], price=dat["price"], time_of_next_price_reduce=datetime_nullable_fromtimestamp(None if dat["fixed_price"] else dat["next_reduce_timestamp"]), datacenter=Datacenters.from_data(dat["datacenter"]),
            cpu_name=dat["cpu"], ram_size=dat["ram_size"], ram_num=int(dat["ram"][0][0]), disks=dat["serverDiskData"],
            specials=ServerSpecials("IPv4" in dat["specials"], "GPU" in dat["specials"], "iNIC" in dat["specials"], "ECC" in dat["specials"], "HWR" in dat["specials"])
        )
        for dat in data
    ]

    return add_objects_to_database(db, servers)


def download_server_list(db: DatabaseSession) -> list[Server] | None:
    data = get_hetzner_api()

    if data is None:
        return None

    existing_servers = read_servers_to_ids(db)

    if len(existing_servers) < 50:
        # Short-circuit because creating a database transaction for every item is quite expensive.
        return bulk_create_server_from_data(db, data["server"])

    for dat in data["server"]:
        if existing_servers.get(dat["id"], None) is None:
            # Don't know the server yet, simply create it and notify the user about it
            server = create_server(
                db, dat["id"], dat["price"], None if dat["fixed_price"] else dat["next_reduce_timestamp"], dat["datacenter"],
                dat["cpu"], dat["ram_size"], dat["ram"], dat["serverDiskData"],
                "IPv4" in dat["specials"], "GPU" in dat["specials"], "iNIC" in dat["specials"], "ECC" in dat["specials"], "HWR" in dat["specials"]
            )

            _ = server

            continue

    return []
