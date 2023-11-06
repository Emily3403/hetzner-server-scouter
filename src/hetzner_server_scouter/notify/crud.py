from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_utils import add_object_to_database, add_objects_to_database
from hetzner_server_scouter.notify.models import ServerChange, ServerChangeLog, NotificationConfig
from hetzner_server_scouter.notify.notify_telegram import TelegramAuthenticationData
from hetzner_server_scouter.settings import error_exit


def create_logs_from_changes(db: DatabaseSession, changes: list[ServerChange]) -> list[ServerChangeLog] | None:
    return add_objects_to_database(db, [ServerChangeLog(change=change) for change in changes])


def create_notification_config(db: DatabaseSession, timeout: float, telegram_auth_data: TelegramAuthenticationData) -> NotificationConfig | None:
    return add_object_to_database(db, NotificationConfig(database_version=1, timeout=timeout, telegram_auth_data=telegram_auth_data))


def read_notification_config(db: DatabaseSession) -> NotificationConfig:
    configs = db.execute(select(NotificationConfig)).scalars().all()

    if len(configs) != 1:
        error_exit(2, f"Could not load notification config! Got {len(configs)} config database entries, expected 1\nPlease make sure you have set the config with `isisdl --init`!")

    return configs[0]
