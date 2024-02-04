from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_utils import add_objects_to_database
from hetzner_server_scouter.notifications.models import ServerChange, ServerChangeLog
from hetzner_server_scouter.notifications.notify_telegram import telegram_notify_about_changes


def create_logs_from_changes(db: DatabaseSession, changes: list[ServerChange]) -> list[ServerChangeLog] | None:
    return add_objects_to_database(db, [ServerChangeLog(server_id=change.server_id, change=change) for change in changes])


def console_notify_about_changes(change_logs: list[ServerChangeLog]) -> None:
    print(f"\n\n\n{'─' * 20}\n\n\n".join(log.change.to_console_str() or f"Error producing the message for server {log.server_id}!" for log in change_logs))


async def process_changes(db: DatabaseSession, changes: list[ServerChange]) -> None:
    logs = create_logs_from_changes(db, changes)
    if logs is None:
        return

    console_notify_about_changes(logs)
    await telegram_notify_about_changes(db, logs)
