from __future__ import annotations

import logging

from app.config import SETTINGS
from app.users import USER_REPOSITORY


LOGGER = logging.getLogger("telegram_ollama_bot")
TELEGRAM_CHANNEL = "telegram"


def get_owner_telegram_user_ids() -> set[int]:
    if SETTINGS.owner_telegram_user_ids:
        return SETTINGS.owner_telegram_user_ids

    return SETTINGS.allowed_telegram_user_ids


def is_access_control_configured() -> bool:
    return bool(SETTINGS.owner_telegram_user_ids or SETTINGS.allowed_telegram_user_ids)


def is_owner(user_id: int | None) -> bool:
    return bool(user_id and user_id in get_owner_telegram_user_ids())


def is_user_allowed(user_id: int | None) -> bool:
    return is_channel_user_allowed(
        TELEGRAM_CHANNEL,
        str(user_id) if user_id is not None else None,
    )


def is_channel_user_allowed(
    channel: str,
    channel_user_id: str | None,
) -> bool:
    if not is_access_control_configured():
        return True

    if channel_user_id is None:
        return False

    if channel == TELEGRAM_CHANNEL:
        try:
            telegram_user_id = int(channel_user_id)
        except ValueError:
            telegram_user_id = None

        if (
            is_owner(telegram_user_id)
            or telegram_user_id in SETTINGS.allowed_telegram_user_ids
        ):
            return True

    return USER_REPOSITORY.is_active_channel_user(channel, channel_user_id)


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
