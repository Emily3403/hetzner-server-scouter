from __future__ import annotations

import asyncio
import os
import re
from sqlalchemy.orm import Session as DatabaseSession
from telegram import Bot
from traceback import format_exception
from typing import TYPE_CHECKING

from hetzner_server_scouter.db.db_utils import database_transaction
from hetzner_server_scouter.settings import error_text
from hetzner_server_scouter.utils import RateLimiter, print_exception

if TYPE_CHECKING:
    from hetzner_server_scouter.notifications.models import ServerChangeLog


async def telegram_notify_about_changes(db: DatabaseSession, change_logs: list[ServerChangeLog]) -> None:
    api_token = os.getenv("TELEGRAM_API_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if api_token is None or chat_id is None:
        return

    bot = Bot(token=api_token)
    limiter = RateLimiter(rate_s=1, rate_m=20)

    async def send_message(log: ServerChangeLog) -> None:
        last_message_id = log.server.last_message_id if log.server is not None else log.change.attrs.get("last_message_id")

        i = 0
        while i < 20:
            try:
                await limiter.wait()
                msg = await bot.send_message(
                    chat_id=chat_id, text=log.change.to_telegram_str() or f"Error producing the message for server {log.server_id}!",
                    reply_to_message_id=last_message_id, read_timeout=10, parse_mode="html", disable_web_page_preview=True,
                )
                break

            except Exception as ex:
                i += 1

                if (it := re.match(r"Flood control exceeded. Retry in (\d+) seconds", str(ex))) is not None:
                    to_sleep = int(it.group(1)) + 1
                    print(f"{error_text} Telegram flood control exceeded. Retrying in {to_sleep} seconds...", flush=True)
                    await asyncio.sleep(to_sleep)
                    await notify_exception_via_telegram(ex)

                else:
                    await notify_exception_via_telegram(ex)
                    await asyncio.sleep(5)

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
            print_exception(ex)
            await bot.send_message(chat_id=chat_id, text=f"{error_text} An unexpected error has occured:\n```{chr(10).join(format_exception(ex))}```", parse_mode="markdown")
            break

        except Exception:
            i += 1
            await asyncio.sleep(1)
