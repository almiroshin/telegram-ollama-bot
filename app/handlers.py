from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from app.access import get_update_user_id, reject_unauthorized
from app.config import SETTINGS
from app.documents import extract_text_from_file, trim_document_text
from app.llm import USER_HISTORY, ask_ollama
from app.stt import transcribe_audio_file


LOGGER = logging.getLogger("telegram_ollama_bot")


def get_command_text(update: Update, command: str) -> str:
    text = update.message.text or ""
    return text.replace(f"/{command}", "", 1).strip()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_unauthorized(update):
        return

    await update.message.reply_text(
        "Я локальный AI-бот на Ollama.\n\n"
        "Команды:\n"
        "/status — статус\n"
        "/model — текущая модель\n"
        "/reset — очистить историю\n"
        "/email — деловое письмо\n"
        "/rewrite — переписать текст\n"
        "/shorten — сократить текст\n"
        "/vip — текст для высокого руководителя\n"
        "/surf — стиль SURF Consulting\n"
        "/shell — помощь по терминалу\n"
        "/followup — письмо после встречи\n\n"
        "Голосовые сообщения тоже можно отправлять — я распознаю их локально.\n"
        "Файлы .txt, .md, .pdf и .docx тоже можно отправлять — я извлеку текст и проанализирую.\n"
        "Если PDF является сканом, попробую распознать его через OCR.\n\n"
        "Можно писать и обычным сообщением."
    )


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ваш Telegram ID: {update.effective_user.id}")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_unauthorized(update):
        return

    USER_HISTORY.pop(update.effective_user.id, None)
    await update.message.reply_text("История диалога очищена.")


async def model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_unauthorized(update):
        return

    await update.message.reply_text(f"Текущая модель: {SETTINGS.ollama_model}")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_unauthorized(update):
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                SETTINGS.ollama_url,
                json={
                    "model": SETTINGS.ollama_model,
                    "messages": [
                        {"role": "user", "content": "Ответь одним словом: OK"}
                    ],
                    "stream": False
                }
            )
            response.raise_for_status()

        await update.message.reply_text(
            "Статус: работает\n"
            f"Модель: {SETTINGS.ollama_model}\n"
            f"Ollama URL: {SETTINGS.ollama_url}\n"
            f"Whisper: {SETTINGS.whisper_model_size}, "
            f"{SETTINGS.whisper_device}, {SETTINGS.whisper_compute_type}\n"
            f"Файлы: лимит {SETTINGS.max_file_size_mb} MB, "
            f"анализ до {SETTINGS.max_document_chars} символов\n"
            f"OCR: lang={SETTINGS.ocr_lang}, dpi={SETTINGS.ocr_dpi}, "
            f"max_pages={SETTINGS.max_ocr_pages}\n"
            f"Poppler path: {SETTINGS.poppler_path}\n"
            f"Tesseract cmd: {SETTINGS.tesseract_cmd}"
        )
    except Exception:
        LOGGER.exception("Status check failed")
        await update.message.reply_text(
            "Статус: ошибка\nНе удалось обратиться к Ollama. Подробности записаны в лог."
        )


async def handle_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
    if await reject_unauthorized(update):
        return

    text = get_command_text(update, mode)

    if not text:
        examples = {
            "email": "Например:\n/email Напиши письмо партнеру: попроси прислать спецификацию Dell до пятницы",
            "rewrite": "Например:\n/rewrite Сделай текст более деловым: ...",
            "shorten": "Например:\n/shorten Сократи этот текст для Telegram: ...",
            "vip": "Например:\n/vip Опиши проект цифрового медицинского профиля для министра",
            "surf": "Например:\n/surf Упакуй этот текст в стиле SURF Consulting: ...",
            "shell": "Например:\n/shell Как проверить, что Telegram-бот запущен и нет дублей?",
            "followup": "Например:\n/followup После встречи обсудили СХД, заказчик ждет сравнение Dell/HPE/NetApp"
        }
        await update.message.reply_text(examples.get(mode, "Пришлите текст после команды."))
        return

    await update.message.chat.send_action(action="typing")

    try:
        answer = await ask_ollama(update.effective_user.id, text, mode=mode)
        await update.message.reply_text(answer)
    except Exception:
        LOGGER.exception(
            "Ollama request failed: user_id=%s mode=%s",
            get_update_user_id(update),
            mode,
        )
        await update.message.reply_text(
            "Ошибка при обращении к Ollama. Подробности записаны в лог."
        )


async def email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "email")


async def rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "rewrite")


async def shorten(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "shorten")


async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "vip")


async def surf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "surf")


async def shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "shell")


async def followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "followup")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_unauthorized(update):
        return

    await update.message.reply_text("Голосовое получил. Распознаю локально...")

    try:
        voice = update.message.voice

        if not voice:
            await update.message.reply_text("Не вижу голосового сообщения.")
            return

        tg_file = await context.bot.get_file(voice.file_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = str(Path(tmpdir) / "voice.ogg")
            await tg_file.download_to_drive(audio_path)

            transcript = transcribe_audio_file(audio_path)

        if not transcript:
            await update.message.reply_text("Не удалось распознать речь.")
            return

        prompt = (
            "Это расшифровка голосового сообщения пользователя.\n\n"
            f"Расшифровка:\n{transcript}\n\n"
            "Обработай эту голосовую заметку: кратко перескажи смысл, "
            "выдели задачи, важные детали и следующие шаги."
        )

        answer = await ask_ollama(update.effective_user.id, prompt, mode="voice")

        final_answer = (
            "Расшифровка:\n"
            f"{transcript}\n\n"
            "Обработка:\n"
            f"{answer}"
        )

        await update.message.reply_text(final_answer)

    except Exception:
        LOGGER.exception(
            "Voice processing failed: user_id=%s",
            get_update_user_id(update),
        )
        await update.message.reply_text(
            "Ошибка при обработке голосового. Подробности записаны в лог."
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_unauthorized(update):
        return

    document = update.message.document

    if not document:
        await update.message.reply_text("Не вижу файла.")
        return

    filename = document.file_name or "document"
    file_size = document.file_size or 0
    file_size_mb = file_size / 1024 / 1024

    if file_size_mb > SETTINGS.max_file_size_mb:
        await update.message.reply_text(
            f"Файл слишком большой: {file_size_mb:.1f} MB.\n"
            f"Лимит сейчас: {SETTINGS.max_file_size_mb} MB."
        )
        return

    supported = filename.lower().endswith((".txt", ".md", ".pdf", ".docx"))

    if not supported:
        await update.message.reply_text(
            "Пока поддерживаю только файлы:\n"
            ".txt\n"
            ".md\n"
            ".pdf\n"
            ".docx"
        )
        return

    await update.message.reply_text(
        f"Файл получил: {filename}\n"
        "Извлекаю текст. Если это скан, включу OCR..."
    )

    try:
        tg_file = await context.bot.get_file(document.file_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = str(Path(tmpdir) / filename)
            await tg_file.download_to_drive(file_path)

            extracted_text, used_ocr = extract_text_from_file(file_path, filename)

        if not extracted_text:
            await update.message.reply_text(
                "Не удалось извлечь текст из файла даже через OCR. "
                "Возможно, качество скана слишком низкое, документ защищён или это файл без читаемого текста."
            )
            return

        prepared_text, was_trimmed = trim_document_text(extracted_text)

        prompt = (
            f"Пользователь прислал файл: {filename}\n\n"
            "Ниже извлеченный текст документа.\n\n"
            f"{prepared_text}\n\n"
            "Проанализируй документ. Дай краткое резюме, ключевые тезисы, "
            "важные требования, задачи, риски, вопросы и следующие шаги."
        )

        answer = await ask_ollama(update.effective_user.id, prompt, mode="document")

        header = f"Анализ файла: {filename}\n\n"

        if used_ocr:
            header += (
                "Текстовый слой не найден, поэтому я использовал OCR-распознавание скана.\n\n"
            )

        if was_trimmed:
            header += (
                "Важно: документ длинный, я проанализировал первую часть текста. "
                "Для полного анализа позже лучше добавить RAG/индексацию документов.\n\n"
            )

        await update.message.reply_text(header + answer)

    except Exception:
        LOGGER.exception(
            "Document processing failed: user_id=%s filename=%s",
            get_update_user_id(update),
            filename,
        )
        await update.message.reply_text(
            "Ошибка при обработке файла. Подробности записаны в лог."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_unauthorized(update):
        return

    text = update.message.text.strip()

    if not text:
        return

    await update.message.chat.send_action(action="typing")

    try:
        answer = await ask_ollama(update.effective_user.id, text, mode="default")
        await update.message.reply_text(answer)
    except Exception:
        LOGGER.exception(
            "Ollama request failed: user_id=%s mode=default",
            get_update_user_id(update),
        )
        await update.message.reply_text(
            "Ошибка при обращении к Ollama. Подробности записаны в лог."
        )
