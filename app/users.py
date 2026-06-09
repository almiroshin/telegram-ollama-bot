from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.config import SETTINGS


ACTIVE_STATUS = "active"
BLOCKED_STATUS = "blocked"
PENDING_STATUS = "pending"

USER_ROLE = "user"
ADMIN_ROLE = "admin"
OWNER_ROLE = "owner"

VALID_STATUSES = {ACTIVE_STATUS, BLOCKED_STATUS, PENDING_STATUS}
VALID_ROLES = {USER_ROLE, ADMIN_ROLE, OWNER_ROLE}


@dataclass(frozen=True)
class ManagedUser:
    user_id: int
    username: str | None
    full_name: str | None
    role: str
    status: str
    created_at: str
    updated_at: str
    approved_at: str | None
    approved_by: int | None
    blocked_at: str | None
    blocked_by: int | None


class SQLiteUserRepository:
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
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    role TEXT NOT NULL DEFAULT 'user'
                        CHECK (role IN ('owner', 'admin', 'user')),
                    status TEXT NOT NULL
                        CHECK (status IN ('pending', 'active', 'blocked')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    approved_at TEXT,
                    approved_by INTEGER,
                    blocked_at TEXT,
                    blocked_by INTEGER
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_status_updated_at
                ON users (status, updated_at)
                """
            )

    def get_user(self, user_id: int) -> ManagedUser | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        return self._row_to_user(row)

    def is_active_user(self, user_id: int | None) -> bool:
        if user_id is None:
            return False

        user = self.get_user(user_id)
        return bool(user and user.status == ACTIVE_STATUS)

    def request_access(
        self,
        user_id: int,
        username: str | None = None,
        full_name: str | None = None,
    ) -> ManagedUser:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT *
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if not existing:
                connection.execute(
                    """
                    INSERT INTO users (user_id, username, full_name, role, status)
                    VALUES (?, ?, ?, 'user', 'pending')
                    """,
                    (user_id, username, full_name),
                )
            else:
                connection.execute(
                    """
                    UPDATE users
                    SET username = ?,
                        full_name = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (username, full_name, user_id),
                )

            row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        user = self._row_to_user(row)
        if user is None:
            raise RuntimeError("Failed to create access request")

        return user

    def approve_user(
        self,
        user_id: int,
        approved_by: int,
        role: str = USER_ROLE,
    ) -> ManagedUser:
        self._validate_role(role)

        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT user_id
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if existing:
                connection.execute(
                    """
                    UPDATE users
                    SET role = ?,
                        status = 'active',
                        updated_at = CURRENT_TIMESTAMP,
                        approved_at = CURRENT_TIMESTAMP,
                        approved_by = ?,
                        blocked_at = NULL,
                        blocked_by = NULL
                    WHERE user_id = ?
                    """,
                    (role, approved_by, user_id),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO users (
                        user_id,
                        role,
                        status,
                        approved_at,
                        approved_by
                    )
                    VALUES (?, ?, 'active', CURRENT_TIMESTAMP, ?)
                    """,
                    (user_id, role, approved_by),
                )

            row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        user = self._row_to_user(row)
        if user is None:
            raise RuntimeError("Failed to approve user")

        return user

    def block_user(self, user_id: int, blocked_by: int) -> ManagedUser:
        with self._connect() as connection:
            existing = connection.execute(
                """
                SELECT user_id
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            if existing:
                connection.execute(
                    """
                    UPDATE users
                    SET status = 'blocked',
                        updated_at = CURRENT_TIMESTAMP,
                        blocked_at = CURRENT_TIMESTAMP,
                        blocked_by = ?
                    WHERE user_id = ?
                    """,
                    (blocked_by, user_id),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO users (
                        user_id,
                        role,
                        status,
                        blocked_at,
                        blocked_by
                    )
                    VALUES (?, 'user', 'blocked', CURRENT_TIMESTAMP, ?)
                    """,
                    (user_id, blocked_by),
                )

            row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        user = self._row_to_user(row)
        if user is None:
            raise RuntimeError("Failed to block user")

        return user

    def list_users(self, limit: int = 50) -> list[ManagedUser]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM users
                ORDER BY
                    CASE status
                        WHEN 'pending' THEN 0
                        WHEN 'active' THEN 1
                        ELSE 2
                    END,
                    updated_at DESC,
                    user_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            user
            for row in rows
            if (user := self._row_to_user(row)) is not None
        ]

    def count_by_status(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM users
                GROUP BY status
                """
            ).fetchall()

        counts = {status: 0 for status in sorted(VALID_STATUSES)}
        counts.update({row["status"]: row["count"] for row in rows})
        return counts

    def _row_to_user(self, row: sqlite3.Row | None) -> ManagedUser | None:
        if row is None:
            return None

        return ManagedUser(
            user_id=row["user_id"],
            username=row["username"],
            full_name=row["full_name"],
            role=row["role"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            approved_at=row["approved_at"],
            approved_by=row["approved_by"],
            blocked_at=row["blocked_at"],
            blocked_by=row["blocked_by"],
        )

    def _validate_role(self, role: str) -> None:
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid user role: {role}")


USER_REPOSITORY = SQLiteUserRepository(SETTINGS.history_db_path)
