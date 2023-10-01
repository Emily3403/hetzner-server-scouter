from sqlalchemy import Text
from sqlalchemy.orm import mapped_column, Mapped

from hetzner_server_scouter.db.db_conf import DataBase


class SimpleModel(DataBase):  # type:ignore[valid-type, misc]
    __tablename__ = "simple_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    optional_author: Mapped[str | None] = mapped_column(Text, nullable=True)
