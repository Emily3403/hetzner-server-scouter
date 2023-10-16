from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Text
from sqlalchemy.orm import mapped_column, Mapped, composite
from sqlalchemy_utils import JSONType

from hetzner_server_scouter.db.db_conf import DataBase
from hetzner_server_scouter.notify.models import ServerChange, ServerChangeType
from hetzner_server_scouter.settings import Datacenters, ServerSpecials
from hetzner_server_scouter.utils import datetime_nullable_fromtimestamp, program_args, hetzner_ipv4_price




class Server(DataBase):  # type:ignore[valid-type, misc]
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    last_message_id: Mapped[int] = mapped_column(unique=True, nullable=True, default=None)

    price: Mapped[float] = mapped_column(nullable=False)
    time_of_next_price_reduce: Mapped[datetime | None] = mapped_column(nullable=True)
    datacenter: Mapped[Datacenters] = mapped_column(nullable=False)
    cpu_name: Mapped[str] = mapped_column(Text, nullable=False)

    ram_size: Mapped[int] = mapped_column(nullable=False)
    ram_num: Mapped[int] = mapped_column(nullable=False)

    hdd_disks: Mapped[list[int]] = mapped_column(JSONType)
    sata_disks: Mapped[list[int]] = mapped_column(JSONType)
    nvme_disks: Mapped[list[int]] = mapped_column(JSONType)

    specials: Mapped[ServerSpecials] = composite(
        mapped_column("has_ipv4"), mapped_column("has_gpu"), mapped_column("has_inic"), mapped_column("has_ecc"), mapped_column("has_hwr")
    )

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Server | None:
        from hetzner_server_scouter.utils import filter_server_with_program_args

        return filter_server_with_program_args(
            Server(
                id=data["id"], price=data["price"], time_of_next_price_reduce=datetime_nullable_fromtimestamp(None if data["fixed_price"] else data["next_reduce_timestamp"]), datacenter=Datacenters.from_data(data["datacenter"]),
                cpu_name=data["cpu"], ram_size=data["ram_size"], ram_num=int(data["ram"][0][0]), hdd_disks=data["serverDiskData"]["hdd"], sata_disks=data["serverDiskData"]["sata"], nvme_disks=data["serverDiskData"]["nvme"],
                specials=ServerSpecials("IPv4" in data["specials"], "GPU" in data["specials"], "iNIC" in data["specials"], "ECC" in data["specials"], "HWR" in data["specials"])
            )
        )

    def __eq__(self, other: object | Server) -> bool:
        if not isinstance(other, Server):
            return False

        return self.id == other.id and self.price == other.price and self.datacenter == other.datacenter and self.cpu_name == other.cpu_name and self.ram_size == other.ram_size and \
            self.ram_num == other.ram_num and self.hdd_disks == other.hdd_disks and self.sata_disks == other.sata_disks and self.nvme_disks == other.nvme_disks and self.specials == other.specials

    def process_change(self, other: Server | None) -> ServerChange | None:
        if other is None:
            return ServerChange(ServerChangeType.new, self.id, "", "", "")

        if self.price != other.price:
            return ServerChange(ServerChangeType.price_changed, self.id, "price", "price", "price")

        for attr in ["datacenter", "cpu_name", "ram_size", "ram_num", "hdd_disks", "sata_disks", "nvme_disks", "specials"]:
            if (new_attr := getattr(self, attr)) != (prev_attr := getattr(other, attr)):
                return ServerChange(ServerChangeType.hardware_changed, self.id, attr, prev_attr, new_attr)

        return None

    def calculate_price(self) -> float:
        return float(self.price * (1 + program_args.tax / 100) + (hetzner_ipv4_price or 0))
