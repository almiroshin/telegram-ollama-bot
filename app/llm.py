from __future__ import annotations

import httpx

from app.config import SETTINGS
from app.prompts import MODES


USER_HISTORY = {}


async def ask_ollama(user_id: int, text: str, mode: str = "default") -> str:
    history = USER_HISTORY.setdefault(user_id, [])
    system_prompt = MODES.get(mode, MODES["default"])

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-SETTINGS.max_history_messages:])
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

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": answer})
    USER_HISTORY[user_id] = history[-SETTINGS.max_history_messages:]

    return answer
