from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteHistoryRepository:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._ensure_parent_dir()
        self.initialize()

    def _ensure_parent_dir(self) -> None:
        parent = self.db_path.parent

        if str(parent) and str(parent) != ".":
            parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_messages_user_id_id
                ON messages (user_id, id)
                """
            )

    def get_recent_messages(self, user_id: int, limit: int) -> list[dict[str, str]]:
        if limit <= 0:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

        return [
            {"role": row["role"], "content": row["content"]}
            for row in reversed(rows)
        ]

    def append_message(self, user_id: int, role: str, content: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO messages (user_id, role, content)
                VALUES (?, ?, ?)
                """,
                (user_id, role, content),
            )

    def append_exchange(self, user_id: int, user_text: str, assistant_text: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO messages (user_id, role, content)
                VALUES (?, 'user', ?)
                """,
                (user_id, user_text),
            )
            connection.execute(
                """
                INSERT INTO messages (user_id, role, content)
                VALUES (?, 'assistant', ?)
                """,
                (user_id, assistant_text),
            )

    def trim_user_history(self, user_id: int, max_messages: int) -> None:
        if max_messages <= 0:
            self.clear_user_history(user_id)
            return

        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM messages
                WHERE user_id = ?
                  AND id NOT IN (
                    SELECT id
                    FROM messages
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                  )
                """,
                (user_id, user_id, max_messages),
            )

    def clear_user_history(self, user_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM messages WHERE user_id = ?",
                (user_id,),
            )
