from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.notify.models import ServerChange, ServerChangeLog


def create_logs_from_changes(db: DatabaseSession, changes: list[ServerChange]) -> list[ServerChangeLog] | None:
    return None
