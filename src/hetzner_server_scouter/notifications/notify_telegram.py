from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session as DatabaseSession
from telegram import Bot

from hetzner_server_scouter.db.db_utils import database_transaction

if TYPE_CHECKING:
    from hetzner_server_scouter.notifications.models import ServerChangeLog


# TODO: Enforce a 30/s and 20/min Rate limit

async def telegram_notify_about_changes(db: DatabaseSession, change_logs: list[ServerChangeLog]) -> None:
    api_token = os.getenv("TELEGRAM_API_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if api_token is None or chat_id is None:
        return

    bot = Bot(token=api_token)

    async def send_message(log: ServerChangeLog) -> None:
        last_message_id = log.server.last_message_id if log.server is not None else log.change.attrs.get("last_message_id")

        while True:
            try:
                msg = await bot.send_message(
                    chat_id=chat_id, text=log.change.to_telegram_str() or f"Error producing the message for server {log.server_id}!",
                    reply_to_message_id=last_message_id, read_timeout=10, parse_mode="html", disable_web_page_preview=True,
                )
                break

            except Exception:
                await asyncio.sleep(1)

        if log.server is not None:
            log.server.last_message_id = msg.message_id

    messages = [send_message(log) for log in change_logs]
    for message in messages:
        # We deliberately not use as_completed because it is *too* fast
        await message

    database_transaction(db, lambda: None)


async def notify_exception_via_telegram(ex: Exception) -> None:
    api_token = os.getenv("TELEGRAM_API_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if api_token is None or chat_id is None:
        return

    bot = Bot(token=api_token)

    i = 0
    while i < 5:
        try:
            await bot.send_message(chat_id=chat_id, text=f"An exception has occurred:\n```\n{ex}\n```", read_timeout=10, parse_mode="markdown")
            break

        except Exception:
            i += 1
            await asyncio.sleep(1)
