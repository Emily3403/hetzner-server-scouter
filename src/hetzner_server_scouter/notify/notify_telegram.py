from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session as DatabaseSession
from telegram import Bot

from hetzner_server_scouter.db.db_utils import database_transaction

if TYPE_CHECKING:
    from hetzner_server_scouter.notify.models import NotificationConfig, ServerChangeLog


@dataclass
class TelegramAuthenticationData:
    api_token: str
    chat_id: int


async def telegram_notify_about_changes(db: DatabaseSession, change_logs: list[ServerChangeLog], config: NotificationConfig) -> None:
    bot = Bot(token=config.telegram_auth_data.api_token)

    async def send_message(log: ServerChangeLog) -> None:
        msg = await bot.send_message(
            chat_id=config.telegram_auth_data.chat_id, reply_to_message_id=log.server.last_message_id if log.server is not None else None,
            text=log.change.to_str() or f"Error producing the message for server {log.server_id}!",
            read_timeout=config.timeout, parse_mode="html", disable_web_page_preview=True,
        )

        log.server.last_message_id = msg.message_id

    messages = [send_message(log) for log in change_logs]
    for message in messages:
        await message

    database_transaction(db, lambda: 0)

    # for it in asyncio.as_completed(messages):
    #     await it

    pass
