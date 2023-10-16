from dataclasses import dataclass

from telegram import Bot

from hetzner_server_scouter.notify.models import ServerChange, NotificationConfig


@dataclass
class TelegramAuthenticationData:
    api_token: str
    chat_id: int

def telegram_notify_about_changes(changes: list[ServerChange], config: NotificationConfig) -> None:
    bot = Bot(token=config.telegram_auth_data.api_token)
    bot.send_message(chat_id=config.telegram_auth_data.chat_id, text="Hello World!")