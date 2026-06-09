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


@dataclass(frozen=True)
class ChannelIdentity:
    id: int
    internal_user_id: int
    channel: str
    channel_user_id: str
    username: str | None
    display_name: str | None
    created_at: str
    updated_at: str


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
        connection.execute("PRAGMA foreign_keys = ON")
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS internal_users (
                    id INTEGER PRIMARY KEY,
                    display_name TEXT,
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
                CREATE TABLE IF NOT EXISTS channel_identities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    internal_user_id INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    channel_user_id TEXT NOT NULL,
                    username TEXT,
                    display_name TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (internal_user_id)
                        REFERENCES internal_users (id)
                        ON DELETE CASCADE,
                    UNIQUE (channel, channel_user_id)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_channel_identities_internal_user_id
                ON channel_identities (internal_user_id)
                """
            )
            self._sync_all_legacy_telegram_users(connection)

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

    def get_internal_user_id(
        self,
        channel: str,
        channel_user_id: str,
    ) -> int | None:
        identity = self.get_channel_identity(channel, channel_user_id)
        if identity is None:
            return None

        return identity.internal_user_id

    def get_channel_identity(
        self,
        channel: str,
        channel_user_id: str,
    ) -> ChannelIdentity | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM channel_identities
                WHERE channel = ?
                  AND channel_user_id = ?
                """,
                (channel, str(channel_user_id)),
            ).fetchone()

        return self._row_to_channel_identity(row)

    def is_active_channel_user(
        self,
        channel: str,
        channel_user_id: str | None,
    ) -> bool:
        if channel_user_id is None:
            return False

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT internal_users.status
                FROM channel_identities
                JOIN internal_users
                    ON internal_users.id = channel_identities.internal_user_id
                WHERE channel_identities.channel = ?
                  AND channel_identities.channel_user_id = ?
                """,
                (channel, str(channel_user_id)),
            ).fetchone()

        return bool(row and row["status"] == ACTIVE_STATUS)

    def link_channel_identity(
        self,
        internal_user_id: int,
        channel: str,
        channel_user_id: str,
        username: str | None = None,
        display_name: str | None = None,
    ) -> ChannelIdentity:
        with self._connect() as connection:
            internal_user = connection.execute(
                """
                SELECT id
                FROM internal_users
                WHERE id = ?
                """,
                (internal_user_id,),
            ).fetchone()

            if internal_user is None:
                raise ValueError(f"Internal user not found: {internal_user_id}")

            connection.execute(
                """
                INSERT INTO channel_identities (
                    internal_user_id,
                    channel,
                    channel_user_id,
                    username,
                    display_name
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(channel, channel_user_id) DO UPDATE SET
                    internal_user_id = excluded.internal_user_id,
                    username = excluded.username,
                    display_name = excluded.display_name,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    internal_user_id,
                    channel,
                    str(channel_user_id),
                    username,
                    display_name,
                ),
            )
            row = connection.execute(
                """
                SELECT *
                FROM channel_identities
                WHERE channel = ?
                  AND channel_user_id = ?
                """,
                (channel, str(channel_user_id)),
            ).fetchone()

        identity = self._row_to_channel_identity(row)
        if identity is None:
            raise RuntimeError("Failed to link channel identity")

        return identity

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
            self._sync_legacy_telegram_user(connection, user_id)

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
            self._sync_legacy_telegram_user(connection, user_id)

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
            self._sync_legacy_telegram_user(connection, user_id)

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

    def _row_to_channel_identity(
        self,
        row: sqlite3.Row | None,
    ) -> ChannelIdentity | None:
        if row is None:
            return None

        return ChannelIdentity(
            id=row["id"],
            internal_user_id=row["internal_user_id"],
            channel=row["channel"],
            channel_user_id=row["channel_user_id"],
            username=row["username"],
            display_name=row["display_name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _validate_role(self, role: str) -> None:
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid user role: {role}")

    def _sync_all_legacy_telegram_users(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        rows = connection.execute(
            """
            SELECT user_id
            FROM users
            """
        ).fetchall()

        for row in rows:
            self._sync_legacy_telegram_user(connection, row["user_id"])

    def _sync_legacy_telegram_user(
        self,
        connection: sqlite3.Connection,
        user_id: int,
    ) -> None:
        row = connection.execute(
            """
            SELECT *
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        if row is None:
            return

        display_name = row["full_name"] or row["username"]

        connection.execute(
            """
            INSERT INTO internal_users (
                id,
                display_name,
                role,
                status,
                created_at,
                updated_at,
                approved_at,
                approved_by,
                blocked_at,
                blocked_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                display_name = excluded.display_name,
                role = excluded.role,
                status = excluded.status,
                updated_at = excluded.updated_at,
                approved_at = excluded.approved_at,
                approved_by = excluded.approved_by,
                blocked_at = excluded.blocked_at,
                blocked_by = excluded.blocked_by
            """,
            (
                row["user_id"],
                display_name,
                row["role"],
                row["status"],
                row["created_at"],
                row["updated_at"],
                row["approved_at"],
                row["approved_by"],
                row["blocked_at"],
                row["blocked_by"],
            ),
        )
        connection.execute(
            """
            INSERT INTO channel_identities (
                internal_user_id,
                channel,
                channel_user_id,
                username,
                display_name
            )
            VALUES (?, 'telegram', ?, ?, ?)
            ON CONFLICT(channel, channel_user_id) DO UPDATE SET
                internal_user_id = excluded.internal_user_id,
                username = excluded.username,
                display_name = excluded.display_name,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                row["user_id"],
                str(row["user_id"]),
                row["username"],
                row["full_name"],
            ),
        )


USER_REPOSITORY = SQLiteUserRepository(SETTINGS.history_db_path)
