from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.llm import ask_ollama


TELEGRAM_CHANNEL = "telegram"
EXPRESS_CHANNEL = "express"

PUBLIC_VISIBILITY = "public"
DEFAULT_DELIVERY_CHUNK_SIZE = 3900

MODE_COMMANDS = {
    "email": "email",
    "rewrite": "rewrite",
    "shorten": "shorten",
    "vip": "vip",
    "surf": "surf",
    "audit": "audit",
    "proposal": "proposal",
    "tender": "tender",
    "vendor": "vendor",
    "risk": "risk",
    "shell": "shell",
    "followup": "followup",
}

MODE_EXAMPLES = {
    "email": "Например:\n/email Напиши письмо партнеру: попроси прислать спецификацию Dell до пятницы",
    "rewrite": "Например:\n/rewrite Сделай текст более деловым: ...",
    "shorten": "Например:\n/shorten Сократи этот текст для Telegram: ...",
    "vip": "Например:\n/vip Опиши проект цифрового медицинского профиля для министра",
    "surf": "Например:\n/surf Упакуй этот текст в стиле SURF Consulting: ...",
    "audit": "Например:\n/audit Заказчик хочет модернизировать СХД и серверы, вводные такие: ...",
    "proposal": "Например:\n/proposal Подготовь структуру КП для обновления инфраструктуры филиалов",
    "tender": "Например:\n/tender Проанализируй требования закупки и выдели риски участия: ...",
    "vendor": "Например:\n/vendor Подбери альтернативы для СХД под VMware/Proxmox и резервное копирование",
    "risk": "Например:\n/risk Проверь риски поставки и внедрения для проекта: ...",
    "shell": "Например:\n/shell Как проверить, что Telegram-бот запущен и нет дублей?",
    "followup": "Например:\n/followup После встречи обсудили СХД, заказчик ждет сравнение Dell/HPE/NetApp",
}


@dataclass(frozen=True)
class AssistantAttachment:
    name: str
    content_type: str | None = None
    size_bytes: int | None = None
    file_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssistantRequest:
    channel: str
    channel_user_id: str
    internal_user_id: int
    text: str
    mode: str = "default"
    command: str | None = None
    chat_id: str | None = None
    message_id: str | None = None
    thread_id: str | None = None
    attachments: tuple[AssistantAttachment, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AssistantResponse:
    text: str
    attachments: tuple[AssistantAttachment, ...] = ()
    actions: tuple[str, ...] = ()
    visibility: str = PUBLIC_VISIBILITY
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_command(command: str) -> str:
    return command.strip().lstrip("/").split("@", 1)[0].lower()


def get_mode_for_command(command: str) -> str | None:
    return MODE_COMMANDS.get(normalize_command(command))


def get_example_for_mode(mode: str) -> str:
    return MODE_EXAMPLES.get(mode, "Пришлите текст после команды.")


def split_text_for_delivery(
    text: str,
    max_chars: int = DEFAULT_DELIVERY_CHUNK_SIZE,
) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > max_chars:
        split_at = _find_delivery_split(remaining, max_chars)
        chunk = remaining[:split_at].rstrip()

        if not chunk:
            chunk = remaining[:max_chars]

        chunks.append(chunk)
        remaining = remaining[len(chunk):].lstrip()

    if remaining:
        chunks.append(remaining)

    return chunks


def _find_delivery_split(text: str, max_chars: int) -> int:
    minimum_useful_split = max_chars // 2

    for separator in ("\n\n", "\n", " "):
        split_at = text.rfind(separator, 0, max_chars + 1)

        if split_at >= minimum_useful_split:
            return split_at + (0 if separator == " " else len(separator))

    return max_chars


async def handle_text_request(request: AssistantRequest) -> AssistantResponse:
    answer = await ask_ollama(
        request.internal_user_id,
        request.text,
        mode=request.mode,
    )
    return AssistantResponse(text=answer)
