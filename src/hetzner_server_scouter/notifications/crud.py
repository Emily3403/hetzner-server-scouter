import os

from sqlalchemy import select, delete
from sqlalchemy.orm import Session as DatabaseSession

from hetzner_server_scouter.db.db_utils import add_object_to_database, add_objects_to_database, database_transaction
from hetzner_server_scouter.notifications.models import ServerChange, ServerChangeLog, NotificationConfig
from hetzner_server_scouter.notifications.notify_telegram import TelegramNotificationData, telegram_notify_about_changes
from hetzner_server_scouter.settings import error_exit


def create_logs_from_changes(db: DatabaseSession, changes: list[ServerChange]) -> list[ServerChangeLog] | None:
    return add_objects_to_database(db, [ServerChangeLog(server_id=change.server_id, change=change) for change in changes])


def create_notification_config(db: DatabaseSession, telegram_auth_data: TelegramNotificationData | None) -> NotificationConfig | None:
    return add_object_to_database(db, NotificationConfig(database_version=1, telegram_auth_data=telegram_auth_data))


def read_notification_config(db: DatabaseSession) -> NotificationConfig:
    configs = db.execute(select(NotificationConfig)).scalars().all()

    api_token = os.getenv("TELEGRAM_API_TOKEN")
    chat_id = int(it) if (it := os.getenv("TELEGRAM_CHAT_ID")) is not None else it

    if len(configs) in {0, 1}:
        return maybe_update_notification_config(db, configs[0], api_token, chat_id)

    # The configuration is malformed. Delete all and create anew
    db.execute(delete(NotificationConfig))
    database_transaction(db, lambda: None)

    notification_data = TelegramNotificationData(10, api_token, chat_id) if api_token is not None and chat_id is not None else None
    config = create_notification_config(db, notification_data)
    if config is None:
        error_exit(1, "Failed to create a new notification config!")

    return config


def maybe_update_notification_config(db: DatabaseSession, config: NotificationConfig, api_token: str | None, chat_id: int | None) -> NotificationConfig:
    if api_token is None or chat_id is None:
        return config

    auth_data = config.telegram_notification_data
    if auth_data is None:
        config.telegram_notification_data = TelegramNotificationData(10, api_token, chat_id)
        database_transaction(db, lambda: None)
        return config

    if api_token is not None and auth_data.api_token != api_token:
        auth_data.api_token = api_token

    if chat_id is not None and auth_data.chat_id != chat_id:
        auth_data.chat_id = chat_id

    database_transaction(db, lambda: None)
    return config


def console_notify_about_changes(change_logs: list[ServerChangeLog]) -> None:
    print(f"\n\n\n{'─' * 20}\n\n\n".join(log.change.to_console_str() or f"Error producing the message for server {log.server_id}!" for log in change_logs))


async def process_changes(db: DatabaseSession, config: NotificationConfig, changes: list[ServerChange]) -> None:
    logs = create_logs_from_changes(db, changes)
    if logs is None:
        return

    console_notify_about_changes(logs)

    if config.telegram_notification_data is not None:
        await telegram_notify_about_changes(db, logs, config)
