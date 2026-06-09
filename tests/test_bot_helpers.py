import asyncio
import importlib
import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch


def build_dependency_stubs():
    httpx = types.ModuleType("httpx")

    class AsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    httpx.AsyncClient = AsyncClient

    pytesseract = types.ModuleType("pytesseract")
    pytesseract.pytesseract = SimpleNamespace(tesseract_cmd=None)
    pytesseract.image_to_string = lambda *args, **kwargs: ""

    docx = types.ModuleType("docx")
    docx.Document = lambda *args, **kwargs: SimpleNamespace(paragraphs=[], tables=[])

    faster_whisper = types.ModuleType("faster_whisper")
    faster_whisper.WhisperModel = object

    pdf2image = types.ModuleType("pdf2image")
    pdf2image.convert_from_path = lambda *args, **kwargs: []

    pypdf = types.ModuleType("pypdf")
    pypdf.PdfReader = lambda *args, **kwargs: SimpleNamespace(pages=[])

    telegram = types.ModuleType("telegram")
    telegram.Update = object

    telegram_ext = types.ModuleType("telegram.ext")
    telegram_ext.Application = object
    telegram_ext.CommandHandler = object
    telegram_ext.MessageHandler = object
    telegram_ext.ContextTypes = SimpleNamespace(DEFAULT_TYPE=object)
    telegram_ext.filters = SimpleNamespace(
        VOICE=object(),
        Document=SimpleNamespace(ALL=object()),
        TEXT=object(),
        COMMAND=object(),
    )

    return {
        "httpx": httpx,
        "pytesseract": pytesseract,
        "docx": docx,
        "faster_whisper": faster_whisper,
        "pdf2image": pdf2image,
        "pypdf": pypdf,
        "telegram": telegram,
        "telegram.ext": telegram_ext,
    }


class BotHelperTests(unittest.TestCase):
    def load_bot(self, allowed_user_ids=""):
        sys.modules.pop("bot", None)

        with patch.dict(sys.modules, build_dependency_stubs()):
            with patch.dict(
                os.environ,
                {
                    "ALLOWED_TELEGRAM_USER_IDS": allowed_user_ids,
                    "LOG_LEVEL": "CRITICAL",
                },
            ):
                return importlib.import_module("bot")

    def test_parse_allowed_user_ids_accepts_comma_and_space_separated_values(self):
        bot = self.load_bot()

        self.assertEqual(
            bot.parse_allowed_user_ids("123, 456 789"),
            {123, 456, 789},
        )

    def test_parse_allowed_user_ids_rejects_invalid_values(self):
        bot = self.load_bot()

        with self.assertRaisesRegex(ValueError, "abc"):
            bot.parse_allowed_user_ids("123,abc")

    def test_is_user_allowed_allows_everyone_when_allowlist_is_empty(self):
        bot = self.load_bot()

        self.assertTrue(bot.is_user_allowed(None))
        self.assertTrue(bot.is_user_allowed(123))

    def test_is_user_allowed_checks_configured_allowlist(self):
        bot = self.load_bot(allowed_user_ids="100,200")

        self.assertTrue(bot.is_user_allowed(100))
        self.assertFalse(bot.is_user_allowed(300))
        self.assertFalse(bot.is_user_allowed(None))

    def test_reject_unauthorized_replies_and_returns_true(self):
        bot = self.load_bot(allowed_user_ids="100")
        replies = []

        async def reply_text(text):
            replies.append(text)

        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=200, username="unknown"),
            message=SimpleNamespace(reply_text=reply_text),
        )

        self.assertTrue(asyncio.run(bot.reject_unauthorized(update)))
        self.assertEqual(replies, ["Доступ к этому боту ограничен."])

    def test_reject_unauthorized_returns_false_for_allowed_user(self):
        bot = self.load_bot(allowed_user_ids="100")
        replies = []

        async def reply_text(text):
            replies.append(text)

        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=100, username="owner"),
            message=SimpleNamespace(reply_text=reply_text),
        )

        self.assertFalse(asyncio.run(bot.reject_unauthorized(update)))
        self.assertEqual(replies, [])

    def test_trim_document_text_strips_and_marks_truncation(self):
        bot = self.load_bot()
        bot.MAX_DOCUMENT_CHARS = 5

        self.assertEqual(bot.trim_document_text("  abc  "), ("abc", False))
        self.assertEqual(bot.trim_document_text("abcdef"), ("abcde", True))

    def test_get_command_text_removes_command_prefix(self):
        bot = self.load_bot()
        update = SimpleNamespace(message=SimpleNamespace(text="/email hello"))

        self.assertEqual(bot.get_command_text(update, "email"), "hello")


if __name__ == "__main__":
    unittest.main()
