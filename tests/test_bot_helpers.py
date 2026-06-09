import asyncio
import importlib
import os
import sys
import tempfile
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


def clear_app_modules():
    for module_name in list(sys.modules):
        if module_name == "bot" or module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)


class BotHelperTests(unittest.TestCase):
    def import_module(self, module_name, allowed_user_ids=""):
        clear_app_modules()
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)

        with patch.dict(sys.modules, build_dependency_stubs()):
            with patch.dict(
                os.environ,
                {
                    "ALLOWED_TELEGRAM_USER_IDS": allowed_user_ids,
                    "HISTORY_DB_PATH": os.path.join(tempdir.name, "history.sqlite"),
                    "LOG_LEVEL": "CRITICAL",
                },
            ):
                return importlib.import_module(module_name)

    def test_parse_allowed_user_ids_accepts_comma_and_space_separated_values(self):
        config = self.import_module("app.config")

        self.assertEqual(
            config.parse_allowed_user_ids("123, 456 789"),
            {123, 456, 789},
        )

    def test_parse_allowed_user_ids_rejects_invalid_values(self):
        config = self.import_module("app.config")

        with self.assertRaisesRegex(ValueError, "abc"):
            config.parse_allowed_user_ids("123,abc")

    def test_is_user_allowed_allows_everyone_when_allowlist_is_empty(self):
        access = self.import_module("app.access")

        self.assertTrue(access.is_user_allowed(None))
        self.assertTrue(access.is_user_allowed(123))

    def test_is_user_allowed_checks_configured_allowlist(self):
        access = self.import_module("app.access", allowed_user_ids="100,200")

        self.assertTrue(access.is_user_allowed(100))
        self.assertFalse(access.is_user_allowed(300))
        self.assertFalse(access.is_user_allowed(None))

    def test_reject_unauthorized_replies_and_returns_true(self):
        access = self.import_module("app.access", allowed_user_ids="100")
        replies = []

        async def reply_text(text):
            replies.append(text)

        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=200, username="unknown"),
            message=SimpleNamespace(reply_text=reply_text),
        )

        self.assertTrue(asyncio.run(access.reject_unauthorized(update)))
        self.assertEqual(replies, ["Доступ к этому боту ограничен."])

    def test_reject_unauthorized_returns_false_for_allowed_user(self):
        access = self.import_module("app.access", allowed_user_ids="100")
        replies = []

        async def reply_text(text):
            replies.append(text)

        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=100, username="owner"),
            message=SimpleNamespace(reply_text=reply_text),
        )

        self.assertFalse(asyncio.run(access.reject_unauthorized(update)))
        self.assertEqual(replies, [])

    def test_trim_document_text_strips_and_marks_truncation(self):
        documents = self.import_module("app.documents")

        self.assertEqual(
            documents.trim_document_text("  abc  ", max_chars=5),
            ("abc", False),
        )
        self.assertEqual(
            documents.trim_document_text("abcdef", max_chars=5),
            ("abcde", True),
        )

    def test_sqlite_history_repository_persists_trims_and_clears_messages(self):
        history = self.import_module("app.history")

        with tempfile.TemporaryDirectory() as tempdir:
            repository = history.SQLiteHistoryRepository(
                os.path.join(tempdir, "history.sqlite")
            )

            repository.append_exchange(100, "hello", "hi")
            repository.append_exchange(100, "next", "done")
            repository.append_exchange(200, "other", "answer")
            repository.trim_user_history(100, 2)

            self.assertEqual(
                repository.get_recent_messages(100, 10),
                [
                    {"role": "user", "content": "next"},
                    {"role": "assistant", "content": "done"},
                ],
            )
            self.assertEqual(
                repository.get_recent_messages(200, 10),
                [
                    {"role": "user", "content": "other"},
                    {"role": "assistant", "content": "answer"},
                ],
            )

            repository.clear_user_history(100)

            self.assertEqual(repository.get_recent_messages(100, 10), [])

    def test_get_command_text_removes_command_prefix(self):
        handlers = self.import_module("app.handlers")
        update = SimpleNamespace(message=SimpleNamespace(text="/email hello"))

        self.assertEqual(handlers.get_command_text(update, "email"), "hello")

    def test_bot_module_exposes_thin_entrypoint(self):
        bot = self.import_module("bot")

        self.assertTrue(callable(bot.main))


if __name__ == "__main__":
    unittest.main()
