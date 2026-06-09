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
    def import_module(self, module_name, allowed_user_ids="", owner_user_ids=""):
        clear_app_modules()
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)

        with patch.dict(sys.modules, build_dependency_stubs()):
            with patch.dict(
                os.environ,
                {
                    "ALLOWED_TELEGRAM_USER_IDS": allowed_user_ids,
                    "OWNER_TELEGRAM_USER_IDS": owner_user_ids,
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

    def test_parse_telegram_user_ids_reports_variable_name(self):
        config = self.import_module("app.config")

        with self.assertRaisesRegex(ValueError, "OWNER_TELEGRAM_USER_IDS"):
            config.parse_telegram_user_ids("abc", "OWNER_TELEGRAM_USER_IDS")

    def test_is_user_allowed_allows_everyone_when_allowlist_is_empty(self):
        access = self.import_module("app.access")

        self.assertTrue(access.is_user_allowed(None))
        self.assertTrue(access.is_user_allowed(123))

    def test_is_user_allowed_checks_configured_allowlist(self):
        access = self.import_module("app.access", allowed_user_ids="100,200")

        self.assertTrue(access.is_user_allowed(100))
        self.assertFalse(access.is_user_allowed(300))
        self.assertFalse(access.is_user_allowed(None))

    def test_owner_ids_fall_back_to_legacy_allowlist(self):
        access = self.import_module("app.access", allowed_user_ids="100,200")

        self.assertEqual(access.get_owner_telegram_user_ids(), {100, 200})
        self.assertTrue(access.is_owner(100))

    def test_owner_ids_prefer_owner_env_when_configured(self):
        access = self.import_module(
            "app.access",
            allowed_user_ids="100",
            owner_user_ids="900",
        )

        self.assertEqual(access.get_owner_telegram_user_ids(), {900})
        self.assertTrue(access.is_owner(900))
        self.assertFalse(access.is_owner(100))
        self.assertTrue(access.is_user_allowed(100))

    def test_is_user_allowed_accepts_active_database_user(self):
        access = self.import_module("app.access", owner_user_ids="100")

        access.USER_REPOSITORY.approve_user(300, approved_by=100)

        self.assertTrue(access.is_user_allowed(300))

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
        self.assertEqual(
            replies,
            [
                "Доступ к этому боту ограничен.\n"
                "Отправьте /request_access, чтобы запросить доступ."
            ],
        )

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

    def test_reject_non_owner_replies_and_returns_true(self):
        access = self.import_module("app.access", owner_user_ids="100")
        replies = []

        async def reply_text(text):
            replies.append(text)

        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=200, username="regular"),
            message=SimpleNamespace(reply_text=reply_text),
        )

        self.assertTrue(asyncio.run(access.reject_non_owner(update)))
        self.assertEqual(replies, ["Эта команда доступна только владельцу бота."])

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

    def test_sqlite_user_repository_manages_access_lifecycle(self):
        users = self.import_module("app.users")

        with tempfile.TemporaryDirectory() as tempdir:
            repository = users.SQLiteUserRepository(
                os.path.join(tempdir, "users.sqlite")
            )

            requested = repository.request_access(
                200,
                username="new_user",
                full_name="New User",
            )

            self.assertEqual(requested.status, users.PENDING_STATUS)
            self.assertFalse(repository.is_active_user(200))

            approved = repository.approve_user(200, approved_by=100)

            self.assertEqual(approved.status, users.ACTIVE_STATUS)
            self.assertTrue(repository.is_active_user(200))

            blocked = repository.block_user(200, blocked_by=100)

            self.assertEqual(blocked.status, users.BLOCKED_STATUS)
            self.assertFalse(repository.is_active_user(200))
            self.assertEqual(repository.count_by_status()[users.BLOCKED_STATUS], 1)

    def test_parse_target_user_id(self):
        handlers = self.import_module("app.handlers")

        self.assertEqual(
            handlers.parse_target_user_id(SimpleNamespace(args=["123"])),
            123,
        )
        self.assertIsNone(
            handlers.parse_target_user_id(SimpleNamespace(args=["abc"]))
        )

    def test_assistant_command_routing_is_channel_neutral(self):
        assistant = self.import_module("app.assistant")

        self.assertEqual(assistant.normalize_command("/audit@my_bot"), "audit")
        self.assertEqual(assistant.get_mode_for_command("/proposal"), "proposal")
        self.assertEqual(assistant.get_mode_for_command("unknown"), None)
        self.assertIn("/risk", assistant.get_example_for_mode("risk"))

    def test_assistant_request_and_response_models(self):
        assistant = self.import_module("app.assistant")

        request = assistant.AssistantRequest(
            channel=assistant.EXPRESS_CHANNEL,
            channel_user_id="u-1",
            internal_user_id=1,
            chat_id="chat-1",
            text="hello",
            mode="default",
        )
        response = assistant.AssistantResponse(text="done")

        self.assertEqual(request.channel, assistant.EXPRESS_CHANNEL)
        self.assertEqual(request.text, "hello")
        self.assertEqual(response.visibility, assistant.PUBLIC_VISIBILITY)

    def test_build_telegram_assistant_request(self):
        handlers = self.import_module("app.handlers")

        update = SimpleNamespace(
            effective_user=SimpleNamespace(
                id=100,
                username="owner",
                full_name="Owner User",
            ),
            effective_chat=SimpleNamespace(id=200),
            message=SimpleNamespace(message_id=300),
        )

        request = handlers.build_telegram_assistant_request(
            update,
            "hello",
            mode="audit",
            command="audit",
        )

        self.assertEqual(request.channel, "telegram")
        self.assertEqual(request.channel_user_id, "100")
        self.assertEqual(request.internal_user_id, 100)
        self.assertEqual(request.chat_id, "200")
        self.assertEqual(request.message_id, "300")
        self.assertEqual(request.mode, "audit")
        self.assertEqual(request.metadata["username"], "owner")

    def test_get_command_text_removes_command_prefix(self):
        handlers = self.import_module("app.handlers")
        update = SimpleNamespace(message=SimpleNamespace(text="/email hello"))

        self.assertEqual(handlers.get_command_text(update, "email"), "hello")

    def test_surf_business_prompt_modes_exist(self):
        prompts = self.import_module("app.prompts")

        self.assertTrue(
            {
                "audit",
                "proposal",
                "tender",
                "vendor",
                "risk",
            }.issubset(prompts.MODES)
        )

    def test_bot_module_exposes_thin_entrypoint(self):
        bot = self.import_module("bot")

        self.assertTrue(callable(bot.main))


if __name__ == "__main__":
    unittest.main()
