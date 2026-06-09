from __future__ import annotations

import logging

from app.config import SETTINGS


LOGGER = logging.getLogger("telegram_ollama_bot")


def is_user_allowed(user_id: int | None) -> bool:
    if not SETTINGS.allowed_telegram_user_ids:
        return True

    return user_id in SETTINGS.allowed_telegram_user_ids


def get_update_user_id(update) -> int | None:
    if not update.effective_user:
        return None

    return update.effective_user.id


async def reject_unauthorized(update) -> bool:
    user_id = get_update_user_id(update)

    if is_user_allowed(user_id):
        return False

    username = getattr(update.effective_user, "username", None)
    LOGGER.warning(
        "Unauthorized Telegram access rejected: user_id=%s username=%s",
        user_id,
        username,
    )

    if update.message:
        await update.message.reply_text("Доступ к этому боту ограничен.")

    return True
