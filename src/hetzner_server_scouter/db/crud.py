import random

from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_utils import add_object_to_database
from hetzner_server_scouter.db.models import SimpleModel


def create_simple_model(db: DatabaseSession, description: str, author: str | None = None) -> SimpleModel | None:
    return add_object_to_database(db, SimpleModel(id=random.randint(1, 100000), description=description, optional_author=author))
