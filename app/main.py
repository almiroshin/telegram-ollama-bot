from __future__ import annotations

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.assistant import MODE_COMMANDS
from app.config import SETTINGS, configure_logging
from app.handlers import (
    approve,
    deny,
    handle_document,
    handle_message,
    handle_voice,
    model,
    myid,
    request_access,
    reset,
    revoke,
    start,
    status,
    TELEGRAM_MODE_HANDLERS,
    users,
)


LOGGER = configure_logging()


def main():
    if not SETTINGS.telegram_token:
        raise RuntimeError("Не задан TELEGRAM_TOKEN")

    LOGGER.info("Bot starting")
    LOGGER.info("OLLAMA_URL: %s", SETTINGS.ollama_url)
    LOGGER.info("OLLAMA_MODEL: %s", SETTINGS.ollama_model)
    LOGGER.info("MAX_HISTORY_MESSAGES: %s", SETTINGS.max_history_messages)
    LOGGER.info("HISTORY_DB_PATH: %s", SETTINGS.history_db_path)
    LOGGER.info("OWNER_USER_COUNT: %s", len(SETTINGS.owner_telegram_user_ids))
    LOGGER.info(
        "WHISPER: model=%s device=%s compute_type=%s",
        SETTINGS.whisper_model_size,
        SETTINGS.whisper_device,
        SETTINGS.whisper_compute_type,
    )
    LOGGER.info(
        "DOCUMENTS: max_file_size=%sMB max_document_chars=%s",
        SETTINGS.max_file_size_mb,
        SETTINGS.max_document_chars,
    )
    LOGGER.info(
        "OCR: lang=%s dpi=%s max_pages=%s poppler_path=%s tesseract_cmd=%s",
        SETTINGS.ocr_lang,
        SETTINGS.ocr_dpi,
        SETTINGS.max_ocr_pages,
        SETTINGS.poppler_path,
        SETTINGS.tesseract_cmd,
    )

    if SETTINGS.allowed_telegram_user_ids:
        LOGGER.info(
            "Legacy Telegram allowlist configured: allowed_user_count=%s",
            len(SETTINGS.allowed_telegram_user_ids),
        )
    if not SETTINGS.owner_telegram_user_ids and not SETTINGS.allowed_telegram_user_ids:
        LOGGER.warning(
            "Access control disabled: OWNER_TELEGRAM_USER_IDS and "
            "ALLOWED_TELEGRAM_USER_IDS are empty"
        )

    app = Application.builder().token(SETTINGS.telegram_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("request_access", request_access))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("deny", deny))
    app.add_handler(CommandHandler("revoke", revoke))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("model", model))
    app.add_handler(CommandHandler("status", status))

    for command in MODE_COMMANDS:
        app.add_handler(CommandHandler(command, TELEGRAM_MODE_HANDLERS[command]))

    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    LOGGER.info("Bot polling started")

    app.run_polling()
