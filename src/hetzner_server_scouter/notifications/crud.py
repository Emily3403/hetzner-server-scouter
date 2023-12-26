import os

from sqlalchemy import select, delete
from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_utils import add_object_to_database, add_objects_to_database, database_transaction
from hetzner_server_scouter.notifications.models import ServerChange, ServerChangeLog, NotificationConfig
from hetzner_server_scouter.notifications.notify_telegram import TelegramAuthenticationData
from hetzner_server_scouter.settings import error_exit


def create_logs_from_changes(db: DatabaseSession, changes: list[ServerChange]) -> list[ServerChangeLog] | None:
    return add_objects_to_database(db, [ServerChangeLog(change=change) for change in changes])


def create_notification_config(db: DatabaseSession, timeout: float, telegram_auth_data: TelegramAuthenticationData) -> NotificationConfig | None:
    return add_object_to_database(db, NotificationConfig(database_version=1, timeout=timeout, telegram_auth_data=telegram_auth_data))


def read_notification_config(db: DatabaseSession) -> NotificationConfig:
    configs = db.execute(select(NotificationConfig)).scalars().all()

    api_token = os.getenv("TELEGRAM_API_TOKEN")
    chat_id = int(it) if (it := os.getenv("TELEGRAM_CHAT_ID")) is not None else it

    print(api_token, chat_id)

    if len(configs) == 1:
        return maybe_update_notification_config(db, configs[0], api_token, chat_id)

    if api_token is None or chat_id is None:
        error_exit(1, "Telegram API token or chat ID not provided!")

    # The configuration is either malformed or not present. Let's create a new one.
    db.execute(delete(NotificationConfig))
    database_transaction(db, lambda: None)

    config = create_notification_config(db, 10, TelegramAuthenticationData(api_token, chat_id))
    if config is None:
        error_exit(1, "Failed to create a new notification config!")

    return config


def maybe_update_notification_config(db: DatabaseSession, config: NotificationConfig, api_token: str | None, chat_id: int | None) -> NotificationConfig:
    auth_data = config.telegram_auth_data

    if api_token is not None and auth_data.api_token != api_token:
        auth_data.api_token = api_token

    if chat_id is not None and auth_data.chat_id != chat_id:
        auth_data.chat_id = chat_id

    database_transaction(db, lambda: None)
    return config
