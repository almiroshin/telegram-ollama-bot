from __future__ import annotations

import logging

from faster_whisper import WhisperModel

from app.config import SETTINGS


LOGGER = logging.getLogger("telegram_ollama_bot")
STT_MODEL = None


def get_stt_model():
    global STT_MODEL

    if STT_MODEL is None:
        LOGGER.info(
            "Loading Whisper model: model=%s device=%s compute_type=%s",
            SETTINGS.whisper_model_size,
            SETTINGS.whisper_device,
            SETTINGS.whisper_compute_type,
        )

        STT_MODEL = WhisperModel(
            SETTINGS.whisper_model_size,
            device=SETTINGS.whisper_device,
            compute_type=SETTINGS.whisper_compute_type
        )

        LOGGER.info("Whisper model loaded")

    return STT_MODEL


def transcribe_audio_file(audio_path: str) -> str:
    model = get_stt_model()

    segments, info = model.transcribe(
        audio_path,
        language="ru",
        vad_filter=True,
        beam_size=5
    )

    text_parts = []

    for segment in segments:
        chunk = segment.text.strip()
        if chunk:
            text_parts.append(chunk)

    return " ".join(text_parts).strip()
