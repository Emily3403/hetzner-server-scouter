from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, composite

from hetzner_server_scouter.db.db_conf import DataBase


class ServerChangeType(Enum):
    # Split the updated typed into Created, Updated or Destroyed
    new = 1
    price_changed = 2
    hardware_changed = 3
    sold = 4


@dataclass
class ServerChange:
    kind: ServerChangeType
    server_id: int

    attr_name: str
    prev_attr: str
    new_attr: str


class ServerChangeLog(DataBase):  # type:ignore[valid-type, misc]
    __tablename__ = "server_changes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    time: Mapped[datetime] = mapped_column(nullable=False, default=datetime.now)

    change: Mapped[ServerChange] = composite(mapped_column("kind"), mapped_column(ForeignKey("servers.id")), mapped_column("attr_name"), mapped_column("prev_attr_value"), mapped_column("new_attr_value"))
