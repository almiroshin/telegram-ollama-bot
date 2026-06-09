from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from app.access import (
    get_owner_telegram_user_ids,
    get_update_user_id,
    is_access_control_configured,
    is_owner,
    is_user_allowed,
    reject_non_owner,
    reject_unauthorized,
)
from app.assistant import (
    TELEGRAM_CHANNEL,
    AssistantRequest,
    AssistantResponse,
    get_example_for_mode,
    handle_text_request,
    split_text_for_delivery,
)
from app.config import SETTINGS
from app.documents import extract_text_from_file, trim_document_text
from app.llm import ask_ollama, reset_user_history
from app.stt import transcribe_audio_file
from app.users import (
    ACTIVE_STATUS,
    BLOCKED_STATUS,
    PENDING_STATUS,
    USER_REPOSITORY,
    USER_ROLE,
    ManagedUser,
)


LOGGER = logging.getLogger("telegram_ollama_bot")


def get_command_text(update: Update, command: str) -> str:
    text = update.message.text or ""
    return text.replace(f"/{command}", "", 1).strip()


def get_effective_full_name(update: Update) -> str | None:
    user = update.effective_user

    if not user:
        return None

    full_name = getattr(user, "full_name", None)
    if full_name:
        return full_name

    first_name = getattr(user, "first_name", None)
    last_name = getattr(user, "last_name", None)
    return " ".join(part for part in (first_name, last_name) if part) or None


def format_user_identity(user: ManagedUser) -> str:
    parts = [str(user.user_id)]

    if user.username:
        parts.append(f"@{user.username}")

    if user.full_name:
        parts.append(f"({user.full_name})")

    return " ".join(parts)


def parse_target_user_id(context: ContextTypes.DEFAULT_TYPE) -> int | None:
    args = getattr(context, "args", None) or []

    if not args:
        return None

    try:
        user_id = int(args[0])
    except ValueError:
        return None

    if user_id <= 0:
        return None

    return user_id


def build_telegram_assistant_request(
    update: Update,
    text: str,
    mode: str = "default",
    command: str | None = None,
) -> AssistantRequest:
    user_id = get_update_user_id(update)
    if user_id is None:
        raise ValueError("Telegram update does not contain an effective user")

    chat = getattr(update, "effective_chat", None)
    message = getattr(update, "message", None)
    internal_user_id = (
        USER_REPOSITORY.get_internal_user_id(TELEGRAM_CHANNEL, str(user_id))
        or user_id
    )

    return AssistantRequest(
        channel=TELEGRAM_CHANNEL,
        channel_user_id=str(user_id),
        internal_user_id=internal_user_id,
        text=text,
        mode=mode,
        command=command,
        chat_id=str(chat.id) if chat else None,
        message_id=(
            str(message.message_id)
            if message and hasattr(message, "message_id")
            else None
        ),
        metadata={
            "username": getattr(update.effective_user, "username", None),
            "full_name": get_effective_full_name(update),
        },
    )


async def reply_text_for_delivery(message, text: str) -> None:
    for chunk in split_text_for_delivery(text):
        await message.reply_text(chunk)


async def reply_assistant_response(
    update: Update,
    response: AssistantResponse,
) -> None:
    await reply_text_for_delivery(update.message, response.text)


async def notify_owners_about_access_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: ManagedUser,
) -> None:
    owner_ids = get_owner_telegram_user_ids()

    if not owner_ids:
        return

    requester_id = get_update_user_id(update)
    text = (
        "New Telegram bot access request:\n\n"
        f"User: {format_user_identity(user)}\n"
        f"Status: {user.status}\n\n"
        f"Approve: /approve {user.user_id}\n"
        f"Deny: /deny {user.user_id}"
    )

    for owner_id in owner_ids:
        if owner_id == requester_id:
            continue

        try:
            await context.bot.send_message(chat_id=owner_id, text=text)
        except Exception:
            LOGGER.exception(
                "Failed to notify owner about access request: owner_id=%s requester_id=%s",
                owner_id,
                requester_id,
            )


async def notify_user(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    text: str,
) -> None:
    try:
        await context.bot.send_message(chat_id=user_id, text=text)
    except Exception:
        LOGGER.info("Could not notify Telegram user: user_id=%s", user_id)


async def handle_access_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user_id = get_update_user_id(update)

    if not user_id:
        await update.message.reply_text("Не удалось определить ваш Telegram ID.")
        return

    if is_user_allowed(user_id):
        if not is_access_control_configured():
            await update.message.reply_text(
                "Доступ сейчас открыт для всех. Ваш Telegram ID: "
                f"{user_id}"
            )
        else:
            await update.message.reply_text(
                "У вас уже есть доступ. Ваш Telegram ID: "
                f"{user_id}"
            )
        return

    user = USER_REPOSITORY.request_access(
        user_id=user_id,
        username=getattr(update.effective_user, "username", None),
        full_name=get_effective_full_name(update),
    )

    if user.status == ACTIVE_STATUS:
        await update.message.reply_text(
            "У вас уже есть доступ. Ваш Telegram ID: "
            f"{user_id}"
        )
        return

    if user.status == BLOCKED_STATUS:
        await update.message.reply_text(
            "Ваш доступ был отклонен или отозван. "
            "Обратитесь к владельцу бота.\n\n"
            f"Ваш Telegram ID: {user_id}"
        )
        return

    await notify_owners_about_access_request(update, context, user)

    if get_owner_telegram_user_ids():
        await update.message.reply_text(
            "Запрос доступа отправлен владельцу бота.\n\n"
            f"Ваш Telegram ID: {user_id}"
        )
    else:
        await update.message.reply_text(
            "Запрос доступа сохранен, но владелец бота не настроен.\n"
            "Попросите администратора задать OWNER_TELEGRAM_USER_IDS в .env.\n\n"
            f"Ваш Telegram ID: {user_id}"
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_user_allowed(get_update_user_id(update)):
        await handle_access_request(update, context)
        return

    help_text = (
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
        "/audit — подготовка ИТ-аудита\n"
        "/proposal — структура КП\n"
        "/tender — анализ тендера/RFP/ТЗ\n"
        "/vendor — подбор вендорских альтернатив\n"
        "/risk — риск-разбор проекта или поставки\n"
        "/shell — помощь по терминалу\n"
        "/followup — письмо после встречи\n\n"
        "Голосовые сообщения тоже можно отправлять — я распознаю их локально.\n"
        "Файлы .txt, .md, .pdf и .docx тоже можно отправлять — я извлеку текст и проанализирую.\n"
        "Если PDF является сканом, попробую распознать его через OCR.\n\n"
        "Можно писать и обычным сообщением."
    )

    if is_owner(get_update_user_id(update)):
        help_text += (
            "\n\n"
            "Команды владельца:\n"
            "/users — список пользователей\n"
            "/approve <telegram_id> — выдать доступ\n"
            "/deny <telegram_id> — отклонить запрос\n"
            "/revoke <telegram_id> — отозвать доступ"
        )

    await update.message.reply_text(help_text)


async def request_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_access_request(update, context)


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Ваш Telegram ID: {update.effective_user.id}")


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_non_owner(update):
        return

    target_user_id = parse_target_user_id(context)

    if not target_user_id:
        await update.message.reply_text(
            "Использование: /approve <telegram_id>"
        )
        return

    owner_id = get_update_user_id(update)
    user = USER_REPOSITORY.approve_user(
        user_id=target_user_id,
        approved_by=owner_id,
        role=USER_ROLE,
    )

    LOGGER.info(
        "Telegram user approved: user_id=%s role=%s approved_by=%s",
        target_user_id,
        USER_ROLE,
        owner_id,
    )
    await update.message.reply_text(
        f"Доступ выдан: {format_user_identity(user)} — {user.role}."
    )
    await notify_user(
        context,
        target_user_id,
        "Ваш доступ к Telegram Ollama Bot одобрен. Отправьте /start.",
    )


async def deny(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_non_owner(update):
        return

    target_user_id = parse_target_user_id(context)

    if not target_user_id:
        await update.message.reply_text("Использование: /deny <telegram_id>")
        return

    if is_owner(target_user_id):
        await update.message.reply_text("Нельзя отклонить владельца из .env.")
        return

    owner_id = get_update_user_id(update)
    user = USER_REPOSITORY.block_user(
        user_id=target_user_id,
        blocked_by=owner_id,
    )

    LOGGER.info(
        "Telegram user denied: user_id=%s denied_by=%s",
        target_user_id,
        owner_id,
    )
    await update.message.reply_text(
        f"Запрос отклонен: {format_user_identity(user)}."
    )
    await notify_user(
        context,
        target_user_id,
        "Ваш запрос доступа к Telegram Ollama Bot отклонен.",
    )


async def revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_non_owner(update):
        return

    target_user_id = parse_target_user_id(context)

    if not target_user_id:
        await update.message.reply_text("Использование: /revoke <telegram_id>")
        return

    if is_owner(target_user_id):
        await update.message.reply_text("Нельзя отозвать владельца из .env.")
        return

    owner_id = get_update_user_id(update)
    user = USER_REPOSITORY.block_user(
        user_id=target_user_id,
        blocked_by=owner_id,
    )

    LOGGER.info(
        "Telegram user revoked: user_id=%s revoked_by=%s",
        target_user_id,
        owner_id,
    )
    await update.message.reply_text(
        f"Доступ отозван: {format_user_identity(user)}."
    )
    await notify_user(
        context,
        target_user_id,
        "Ваш доступ к Telegram Ollama Bot отозван.",
    )


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_non_owner(update):
        return

    owner_ids = sorted(get_owner_telegram_user_ids())
    users_list = USER_REPOSITORY.list_users()

    lines = ["Пользователи:"]

    if owner_ids:
        lines.append("")
        lines.append("Owners from .env:")
        lines.extend(f"- {owner_id}" for owner_id in owner_ids)

    lines.append("")
    lines.append("Managed users in SQLite:")

    if users_list:
        for user in users_list:
            lines.append(
                f"- {format_user_identity(user)} — {user.status}/{user.role}"
            )
    else:
        lines.append("- none")

    counts = USER_REPOSITORY.count_by_status()
    lines.append("")
    lines.append(
        "Counts: "
        f"pending={counts[PENDING_STATUS]}, "
        f"active={counts[ACTIVE_STATUS]}, "
        f"blocked={counts[BLOCKED_STATUS]}"
    )

    await update.message.reply_text("\n".join(lines))


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await reject_unauthorized(update):
        return

    reset_user_history(update.effective_user.id)
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

        counts = USER_REPOSITORY.count_by_status()
        await update.message.reply_text(
            "Статус: работает\n"
            f"Модель: {SETTINGS.ollama_model}\n"
            f"Ollama URL: {SETTINGS.ollama_url}\n"
            f"History DB: {SETTINGS.history_db_path}\n"
            f"Access: owners={len(get_owner_telegram_user_ids())}, "
            f"pending={counts[PENDING_STATUS]}, "
            f"active={counts[ACTIVE_STATUS]}, "
            f"blocked={counts[BLOCKED_STATUS]}\n"
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
        await update.message.reply_text(get_example_for_mode(mode))
        return

    await update.message.chat.send_action(action="typing")

    try:
        request = build_telegram_assistant_request(
            update,
            text,
            mode=mode,
            command=mode,
        )
        response = await handle_text_request(request)
        await reply_assistant_response(update, response)
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


async def audit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "audit")


async def proposal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "proposal")


async def tender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "tender")


async def vendor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "vendor")


async def risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_mode(update, context, "risk")


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

        await reply_text_for_delivery(update.message, final_answer)

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

        await reply_text_for_delivery(update.message, header + answer)

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
        request = build_telegram_assistant_request(update, text)
        response = await handle_text_request(request)
        await reply_assistant_response(update, response)
    except Exception:
        LOGGER.exception(
            "Ollama request failed: user_id=%s mode=default",
            get_update_user_id(update),
        )
        await update.message.reply_text(
            "Ошибка при обращении к Ollama. Подробности записаны в лог."
        )
