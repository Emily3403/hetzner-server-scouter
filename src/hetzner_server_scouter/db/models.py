from __future__ import annotations

from datetime import datetime
from typing import Any, TYPE_CHECKING, TypedDict, Literal

from sqlalchemy import Text
from sqlalchemy.orm import Session as DatabaseSession, mapped_column, Mapped, composite, relationship
from sqlalchemy_utils import JSONType

from hetzner_server_scouter.db.db_conf import DataBase
from hetzner_server_scouter.settings import Datacenters, ServerSpecials
from hetzner_server_scouter.utils import datetime_nullable_fromtimestamp, program_args, hetzner_ipv4_price

if TYPE_CHECKING:
    from hetzner_server_scouter.notifications.models import ServerChange, ServerChangeLog

DiskType = Literal["hdd"] | Literal["enterprise_hdd"] | Literal["ssd"] | Literal["enterprise_ssd"]


class DiskTypeDict(TypedDict):
    hdd: list[int]
    enterprise_hdd: list[int]
    ssd: list[int]
    enterprise_ssd: list[int]


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
    ram_is_ecc: Mapped[bool] = mapped_column(nullable=False)

    disks: Mapped[DiskTypeDict] = mapped_column(JSONType, nullable=False)
    specials: Mapped[ServerSpecials] = composite(
        mapped_column("has_ipv4"), mapped_column("has_gpu"), mapped_column("has_inic"), mapped_column("has_hwr")
    )

    change_logs: Mapped[list[ServerChangeLog]] = relationship("ServerChangeLog", back_populates="server")

    @property
    def all_disks(self) -> list[int]:
        return [disk for disks in self.disks.values() for disk in disks]  # type:ignore[attr-defined]  # Mypy somehow doesn't get that .values creates an iterator of lists

    @property
    def all_hdds(self) -> list[int]:
        return [disk for disk in self.disks["hdd"] + self.disks["enterprise_hdd"]]

    @property
    def all_ssds(self) -> list[int]:
        return [disk for disk in self.disks["ssd"] + self.disks["enterprise_ssd"]]

    @classmethod
    def from_data(cls, data: dict[str, Any], last_message_id: int | None = None) -> Server | None:
        from hetzner_server_scouter.utils import filter_server_with_program_args
        from hetzner_server_scouter.db.crud import create_disk_dict_from_hdd_arr

        return filter_server_with_program_args(
            Server(
                id=data["id"], price=data["price"],
                time_of_next_price_reduce=datetime_nullable_fromtimestamp(None if data["fixed_price"] else data["next_reduce_timestamp"]),
                datacenter=Datacenters.from_data(data["datacenter"]), cpu_name=data["cpu"],
                ram_size=data["ram_size"], ram_num=int(data["ram"][0][0]), ram_is_ecc="ECC" in data["specials"],
                disks=create_disk_dict_from_hdd_arr(data["hdd_arr"], data["serverDiskData"]),
                specials=ServerSpecials("IPv4" in data["specials"], "GPU" in data["specials"], "iNIC" in data["specials"], "HWR" in data["specials"]),
                last_message_id=last_message_id
            )
        )

    def to_dict(self) -> dict[str, Any]:
        ret: dict[str, Any] = {}

        for key, item in self.__dict__.items():
            if key.startswith("_sa"):
                continue

            if isinstance(item, ServerSpecials):
                ret[key] = item.__dict__
            elif isinstance(item, Datacenters):
                ret[key] = item.value
            elif isinstance(item, datetime):
                ret[key] = item.isoformat()
            else:
                ret[key] = item

        return ret

    def __eq__(self, other: object | Server) -> bool:
        if not isinstance(other, Server):
            return False

        return (self.id == other.id and self.price == other.price and self.datacenter == other.datacenter and self.cpu_name == other.cpu_name and
                self.ram_size == other.ram_size and self.ram_num == other.ram_num and self.disks == other.disks and self.specials == other.specials)

    def new(self, db: DatabaseSession) -> ServerChange:
        from hetzner_server_scouter.notifications.models import ServerChange, ServerChangeType

        db.add(self)
        return ServerChange(ServerChangeType.new, self.id, None, self.to_dict())

    def update(self, db: DatabaseSession, new: Server | None) -> ServerChange | None:
        from hetzner_server_scouter.notifications.models import ServerChange, ServerChangeType

        if new is None:
            change = ServerChange(ServerChangeType.sold, self.id, self.last_message_id, self.to_dict())
            db.delete(self)
            return change

        if self.price == new.price:
            return None

        self.price = new.price
        self.time_of_next_price_reduce = new.time_of_next_price_reduce
        return ServerChange(ServerChangeType.price_changed, self.id, self.last_message_id, self.to_dict())

    def calculate_price(self) -> float:
        return self._calculate_price(self.price, self.specials.has_IPv4)

    @staticmethod
    def _calculate_price(price: float, has_ipv4: bool) -> float:
        return float(price * (1 + program_args.tax / 100) + (hetzner_ipv4_price or 0) * has_ipv4)
