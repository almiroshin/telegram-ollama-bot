from __future__ import annotations

import logging

from app.config import SETTINGS
from app.users import USER_REPOSITORY


LOGGER = logging.getLogger("telegram_ollama_bot")


def get_owner_telegram_user_ids() -> set[int]:
    if SETTINGS.owner_telegram_user_ids:
        return SETTINGS.owner_telegram_user_ids

    return SETTINGS.allowed_telegram_user_ids


def is_access_control_configured() -> bool:
    return bool(SETTINGS.owner_telegram_user_ids or SETTINGS.allowed_telegram_user_ids)


def is_owner(user_id: int | None) -> bool:
    return bool(user_id and user_id in get_owner_telegram_user_ids())


def is_user_allowed(user_id: int | None) -> bool:
    if not is_access_control_configured():
        return True

    return (
        is_owner(user_id)
        or user_id in SETTINGS.allowed_telegram_user_ids
        or USER_REPOSITORY.is_active_user(user_id)
    )


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
        await update.message.reply_text(
            "Доступ к этому боту ограничен.\n"
            "Отправьте /request_access, чтобы запросить доступ."
        )

    return True


async def reject_non_owner(update) -> bool:
    user_id = get_update_user_id(update)

    if is_owner(user_id):
        return False

    username = getattr(update.effective_user, "username", None)
    LOGGER.warning(
        "Owner-only Telegram command rejected: user_id=%s username=%s",
        user_id,
        username,
    )

    if update.message:
        await update.message.reply_text("Эта команда доступна только владельцу бота.")

    return True
