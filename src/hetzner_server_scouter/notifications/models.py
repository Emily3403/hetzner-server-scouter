from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, composite, relationship
from sqlalchemy_utils import JSONType
from typing import Any

from hetzner_server_scouter.db.db_conf import DataBase
from hetzner_server_scouter.db.models import Server
from hetzner_server_scouter.settings import Datacenters
from hetzner_server_scouter.utils import hetzner_notify_format_disks, hetzner_notify_calculate_price_time_decrease, datetime_nullable_fromisoformat


class ServerChangeType(Enum):
    # Split the updated typed into Created, Updated or Destroyed
    new = 1  # Complete attribute set
    price_changed = 2  # New Price
    sold = 4  # Server ID


@dataclass
class ServerChangeMessage:
    """
    This class exists to make formatting the messages easier as e.g. telegram expects HTML.
    """
    server_id: int
    was_sold: bool

    header: tuple[str, str]
    url: str
    price: float
    price_decreases_in: str
    specs: str
    specials: str
    location: Datacenters | None

    def to_console(self) -> str:
        if self.was_sold:
            return f"""{self.header[0]} {self.url} {self.header[1]} for {self.price:.2f}€!"""

        return f"""{self.header[0]} {self.url} {self.header[1]}
Price: {self.price:.2f}€  {f'({self.price_decreases_in})' if self.price_decreases_in else ''}

Specs:
{self.specs}

Specials:
{self.specials}

Location: {self.location}"""

    def to_telegram(self) -> str:
        if self.was_sold:
            return f"""{self.header[0]} <a href='{self.url}'>{self.server_id}</a> {self.header[1]} for {self.price:.2f}€!"""

        return f"""{self.header[0]} <a href='{self.url}'>{self.server_id}</a> {self.header[1]}
<b>Price</b>: {self.price:.2f}€  {f'({self.price_decreases_in})' if self.price_decreases_in else ''}

<u><b>Specs</b></u>
{self.specs}

<u><b>Specials</b></u>
{self.specials}

<b>Location:</b> {self.location}"""


@dataclass
class ServerChange:
    kind: ServerChangeType
    server_id: int
    last_message_id: int | None

    attrs: dict[str, Any]

    def to_console_str(self) -> str | None:
        it = self.to_message()
        if it is None:
            return it

        return it.to_console()

    def to_telegram_str(self) -> str | None:
        it = self.to_message()
        if it is None:
            return it

        return it.to_telegram()

    def to_message(self) -> ServerChangeMessage | None:

        was_sold = False
        match self.kind:
            case ServerChangeType.new:
                header = "A new server", "has appeared."
            case ServerChangeType.price_changed:
                header = "The price of the server", "has changed."
            case ServerChangeType.sold:
                header = "The server", "was sold"
                was_sold = True
            case _:
                return None  # type:ignore[unreachable]

        _specials: dict[str, bool] = self.attrs.get("specials", {})
        features = {
            "GPU": _specials.get("has_GPU", False),
            "iNIC": _specials.get("has_iNIC", False),
            "ECC": _specials.get("has_ECC", False),
            "HWR": _specials.get("has_HWR", False),
        }

        url = f"https://www.hetzner.com/sb?search={self.server_id}"
        specials = "\n".join([f"{feature}: ✓" for feature, has_it in features.items() if has_it])
        price = Server._calculate_price(self.attrs.get("price", 0), _specials.get("has_IPv4", True))
        price_decreases_in = hetzner_notify_calculate_price_time_decrease(datetime_nullable_fromisoformat(self.attrs.get("time_of_next_price_reduce")))

        location = Datacenters.from_data(self.attrs.get("datacenter"))
        specs = f"""CPU: {self.attrs.get("cpu_name")}
RAM: {self.attrs.get("ram_size")}GB ({self.attrs.get("ram_num")}× {self.attrs.get("ram_size", 0) // self.attrs.get("ram_num", 1)}GB)
Disks: {', '.join(hetzner_notify_format_disks(self.attrs.get("nvme_disks", []), "NVME") + hetzner_notify_format_disks(self.attrs.get("sata_disks", []), "SATA") + hetzner_notify_format_disks(self.attrs.get("hdd_disks", []), "HDD"))}"""

        return ServerChangeMessage(self.server_id, was_sold, header, url, price, price_decreases_in, specs, specials, location)


class ServerChangeLog(DataBase):  # type:ignore[valid-type, misc]
    __tablename__ = "server_change_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"), nullable=True)
    time: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now)

    change: Mapped[ServerChange] = composite(mapped_column("kind", nullable=False), mapped_column("change_server_id"), mapped_column("last_message_id"), mapped_column("attrs", JSONType))
    server: Mapped[Server] = relationship(Server)
