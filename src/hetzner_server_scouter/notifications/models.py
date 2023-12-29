from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, composite, relationship
from sqlalchemy_utils import JSONType

from hetzner_server_scouter.db.db_conf import DataBase
from hetzner_server_scouter.db.models import Server
from hetzner_server_scouter.notifications.notify_telegram import TelegramAuthenticationData
from hetzner_server_scouter.settings import separator, Datacenters
from hetzner_server_scouter.utils import T, hetzner_notify_format_disks, hetzner_notify_calculate_price_time_decrease, datetime_nullable_fromisoformat


class ServerChangeType(Enum):
    # Split the updated typed into Created, Updated or Destroyed
    new = 1  # Complete attribute set
    price_changed = 2  # New Price
    sold = 4  # Server ID


@dataclass
class ServerChange:
    kind: ServerChangeType
    server_id: int
    last_message_id: int | None

    prev_attr_set: dict[str, Any]
    new_attr_set: dict[str, Any]

    def to_str(self) -> str | None:

        server_link = f"<a  href='https://www.hetzner.com/sb?search={self.server_id}'>{self.server_id}</a>"

        match self.kind:
            case ServerChangeType.new:
                message = f"A new server has appeared: {server_link}."

            case ServerChangeType.price_changed:
                message = f"The price of server {server_link} has changed."

            case ServerChangeType.sold:
                return f"The server {server_link} was sold!"

            case _:
                return None  # type:ignore[unreachable]

        try:
            server_description = self.message_server_description()
        except Exception as e:
            return message + separator + f"There was an error in generating the server description:\n{e}"

        return message + "\n" + server_description

    def message_server_description(self) -> str:
        from hetzner_server_scouter.db.models import Server

        price_decreases_in = hetzner_notify_calculate_price_time_decrease(datetime_nullable_fromisoformat(self.new_attr_set["time_of_next_price_reduce"]))
        disk_strings = hetzner_notify_format_disks(self.new_attr_set["nvme_disks"], "NVME") + \
                       hetzner_notify_format_disks(self.new_attr_set["sata_disks"], "SATA") + \
                       hetzner_notify_format_disks(self.new_attr_set["hdd_disks"], "HDD")

        specials, specials_strings = self.new_attr_set["specials"], []
        if not specials.get("has_IPv4", None):
            specials_strings.append("There is **no** IPv4 included!")
        if specials.get("has_GPU", None):
            specials_strings.append("GPU: ✓")
        if specials.get("has_iNIC", None):
            specials_strings.append("iNIC: ✓")
        if specials.get("has_ECC", None):
            specials_strings.append("ECC Memory: ✓")
        if specials.get("has_HWR", None):
            specials_strings.append("Hardware RAID: ✓")

        return f"""<b>Price</b>: {Server._calculate_price(self.new_attr_set["price"], specials["has_IPv4"]):.2f}€  {f'({price_decreases_in})' if price_decreases_in else ''}
{separator}
<u><b>Specs</b></u>
CPU: {self.new_attr_set["cpu_name"]}
RAM: {self.new_attr_set["ram_size"]}GB ({self.new_attr_set["ram_num"]}× {self.new_attr_set["ram_size"] // self.new_attr_set["ram_num"]}GB)
Disks: {', '.join(disk_strings)}
""" + (f"""{separator}
<u><b>Specials</b></u>
{chr(10).join(specials_strings)}
""" if specials_strings else "") + f"""
<b>Location:</b> {Datacenters.from_data(self.new_attr_set["datacenter"])}
"""

    def compute_diff_dict(self) -> dict[str, tuple[T | None, T | None]]:
        diff: dict[str, tuple[T | None, T | None]] = {}

        for key, prev_value in self.prev_attr_set.items():
            new_value = self.new_attr_set.get(key, None)
            if new_value == prev_value:
                continue

            diff[key] = (prev_value, new_value)

        for key, new_value in self.new_attr_set.items():
            prev_value = self.prev_attr_set.get(key, None)
            if key in diff or new_value == prev_value:
                continue

            diff[key] = (prev_value, new_value)

        return diff


class ServerChangeLog(DataBase):  # type:ignore[valid-type, misc]
    __tablename__ = "server_change_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"))
    time: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now)

    change: Mapped[ServerChange] = composite(mapped_column("kind", nullable=False), mapped_column("last_message_id"), server_id, mapped_column("prev_attr_set", JSONType), mapped_column("new_attr_set", JSONType))
    server: Mapped[Server] = relationship(Server)


class NotificationConfig(DataBase):  # type:ignore[valid-type, misc]
    __tablename__ = "notification_config"

    database_version: Mapped[int] = mapped_column(primary_key=True)
    timeout: Mapped[float] = mapped_column()
    telegram_auth_data: Mapped[TelegramAuthenticationData] = composite(mapped_column("telegram_api_token", nullable=False), mapped_column("telegram_chat_id", nullable=False))
