from datetime import datetime

from sqlalchemy import Text
from sqlalchemy.orm import mapped_column, Mapped, composite
from sqlalchemy_utils import JSONType

from hetzner_server_scouter.db.db_conf import DataBase
from hetzner_server_scouter.settings import Datacenters, ServerSpecials


class Server(DataBase):  # type:ignore[valid-type, misc]
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)

    price: Mapped[float] = mapped_column(nullable=False)
    time_of_next_price_reduce: Mapped[datetime | None] = mapped_column(nullable=True)
    datacenter: Mapped[Datacenters] = mapped_column(nullable=False)
    cpu_name: Mapped[str] = mapped_column(Text, nullable=False)

    ram_size: Mapped[int] = mapped_column(nullable=False)
    ram_num: Mapped[int] = mapped_column(nullable=False)

    disks: Mapped[dict[str, list[int]]] = mapped_column(JSONType)

    specials: Mapped[ServerSpecials] = composite(
        mapped_column("has_ipv4"), mapped_column("has_gpu"), mapped_column("has_inic"), mapped_column("has_ecc"), mapped_column("has_hwr")
    )
