from __future__ import annotations

import httpx

from app.config import SETTINGS
from app.history import SQLiteHistoryRepository
from app.prompts import MODES


HISTORY_REPOSITORY = SQLiteHistoryRepository(SETTINGS.history_db_path)


async def ask_ollama(user_id: int, text: str, mode: str = "default") -> str:
    history = HISTORY_REPOSITORY.get_recent_messages(
        user_id,
        SETTINGS.max_history_messages,
    )
    system_prompt = MODES.get(mode, MODES["default"])

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": text})

    payload = {
        "model": SETTINGS.ollama_model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "top_p": 0.9
        }
    }

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(SETTINGS.ollama_url, json=payload)
        response.raise_for_status()
        data = response.json()

    answer = data.get("message", {}).get("content", "").strip()

    if not answer:
        answer = "Модель вернула пустой ответ."

    HISTORY_REPOSITORY.append_exchange(user_id, text, answer)
    HISTORY_REPOSITORY.trim_user_history(user_id, SETTINGS.max_history_messages)

    return answer


def reset_user_history(user_id: int) -> None:
    HISTORY_REPOSITORY.clear_user_history(user_id)
