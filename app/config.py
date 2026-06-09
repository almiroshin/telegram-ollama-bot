from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass


def parse_allowed_user_ids(raw_value: str) -> set[int]:
    user_ids = set()

    for token in raw_value.replace(",", " ").split():
        try:
            user_id = int(token)
        except ValueError as exc:
            raise ValueError(
                f"Invalid Telegram user ID in ALLOWED_TELEGRAM_USER_IDS: {token}"
            ) from exc

        if user_id <= 0:
            raise ValueError(
                f"Telegram user IDs must be positive integers: {token}"
            )

        user_ids.add(user_id)

    return user_ids


@dataclass(frozen=True)
class Settings:
    telegram_token: str | None
    ollama_url: str
    ollama_model: str
    max_history_messages: int
    history_db_path: str
    allowed_telegram_user_ids: set[int]
    log_level: str
    whisper_model_size: str
    whisper_device: str
    whisper_compute_type: str
    max_file_size_mb: int
    max_document_chars: int
    ocr_dpi: int
    ocr_lang: str
    max_ocr_pages: int
    poppler_path: str
    tesseract_cmd: str


def load_settings() -> Settings:
    return Settings(
        telegram_token=os.getenv("TELEGRAM_TOKEN"),
        ollama_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/chat"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        max_history_messages=int(os.getenv("MAX_HISTORY_MESSAGES", "12")),
        history_db_path=os.getenv("HISTORY_DB_PATH", "bot.sqlite"),
        allowed_telegram_user_ids=parse_allowed_user_ids(
            os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
        ),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        whisper_model_size=os.getenv("WHISPER_MODEL_SIZE", "small"),
        whisper_device=os.getenv("WHISPER_DEVICE", "cpu"),
        whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
        max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "20")),
        max_document_chars=int(os.getenv("MAX_DOCUMENT_CHARS", "18000")),
        ocr_dpi=int(os.getenv("OCR_DPI", "200")),
        ocr_lang=os.getenv("OCR_LANG", "rus+eng"),
        max_ocr_pages=int(os.getenv("MAX_OCR_PAGES", "20")),
        poppler_path=os.getenv("POPPLER_PATH", "/opt/homebrew/bin"),
        tesseract_cmd=os.getenv("TESSERACT_CMD", "/opt/homebrew/bin/tesseract"),
    )


SETTINGS = load_settings()


def configure_logging(settings: Settings = SETTINGS) -> logging.Logger:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    return logging.getLogger("telegram_ollama_bot")
