"""Small SQLite-backed account store for the Luvelox MVP workspace."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

try:
    from datetime import UTC as _UTC
except ImportError:  # pragma: no cover - Python 3.10 compatibility
    from datetime import timezone as _timezone

    _UTC = _timezone.utc  # noqa: UP017

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "luvelox_auth.sqlite3"
DEFAULT_ENTITLEMENTS = ("module.laminate", "module.injection")
DEMO_ENTITLEMENTS = {
    "demo@luvelox.com": ("module.laminate", "module.injection"),
    "danlee@luvelox.com": ("module.laminate", "module.injection", "module.optimization"),
}

_PBKDF2_ITERATIONS = 210_000
_LOCK = threading.Lock()


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    name: str
    company: str | None
    location: str | None
    mobile: str | None


@dataclass(frozen=True)
class AuthSession:
    token: str
    user: AuthUser
    entitlements: tuple[str, ...]


@dataclass(frozen=True)
class AdminUserRecord:
    id: str
    email: str
    name: str
    company: str | None
    location: str | None
    mobile: str | None
    created_at: str
    entitlements: tuple[str, ...]
    session_count: int
    last_session_at: str | None


class AuthError(Exception):
    """Base auth store error."""


class DuplicateAccountError(AuthError):
    """Raised when an email is already registered."""


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""


class WeakPasswordError(AuthError):
    """Raised when a password is too short for account signup."""


def _db_path() -> Path:
    return Path(os.environ.get("LUVELOX_AUTH_DB_PATH", DEFAULT_DB_PATH))


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _now() -> str:
    return datetime.now(_UTC).isoformat()


def _expires_at() -> str:
    return (datetime.now(_UTC) + timedelta(days=30)).isoformat()


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    password = password or ""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, password_hash: str) -> bool:
    _, candidate = _hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(candidate, password_hash)


def ensure_auth_db() -> None:
    with _LOCK, _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                company TEXT,
                location TEXT,
                mobile TEXT,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_entitlements (
                user_id TEXT NOT NULL,
                entitlement_key TEXT NOT NULL,
                PRIMARY KEY (user_id, entitlement_key),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS access_requests (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                module_id TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            """
        )
        _ensure_user_profile_columns(connection)
        _seed_demo_accounts(connection)
        connection.commit()


def _ensure_user_profile_columns(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
    if "location" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN location TEXT")
    if "mobile" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN mobile TEXT")


def _seed_demo_accounts(connection: sqlite3.Connection) -> None:
    demo_accounts = (
        ("demo-user", "demo@luvelox.com", "Demo Account", "Luvelox MVP", ""),
        ("danlee", "danlee@luvelox.com", "Dan Lee", "Luvelox", ""),
    )
    for user_id, email, name, company, password in demo_accounts:
        existing = connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing is None:
            salt, password_hash = _hash_password(password)
            connection.execute(
                """
                INSERT INTO users (
                    id, email, name, company, location, mobile, password_salt, password_hash, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, email, name, company, None, None, salt, password_hash, _now()),
            )
        for entitlement in DEMO_ENTITLEMENTS[email]:
            connection.execute(
                """
                INSERT OR IGNORE INTO user_entitlements (user_id, entitlement_key)
                VALUES ((SELECT id FROM users WHERE email = ?), ?)
                """,
                (email, entitlement),
            )
    legacy_sessions = (
        ("demo-token", "demo@luvelox.com"),
        ("danlee-token", "danlee@luvelox.com"),
    )
    for token, email in legacy_sessions:
        connection.execute(
            """
            INSERT OR IGNORE INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, (SELECT id FROM users WHERE email = ?), ?, ?)
            """,
            (token, email, _now(), "2099-12-31T00:00:00+00:00"),
        )


def create_account(
    *,
    email: str,
    password: str,
    name: str,
    company: str | None = None,
    location: str | None = None,
    mobile: str | None = None,
    entitlements: tuple[str, ...] = DEFAULT_ENTITLEMENTS,
) -> AuthSession:
    normalized_email = email.strip().lower()
    normalized_name = name.strip() or normalized_email.partition("@")[0]
    if len(password) < 8:
        raise WeakPasswordError("Password must be at least 8 characters.")
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        existing = connection.execute("SELECT id FROM users WHERE email = ?", (normalized_email,)).fetchone()
        if existing is not None:
            raise DuplicateAccountError("An account with this email already exists.")
        user_id = str(uuid.uuid4())
        salt, password_hash = _hash_password(password)
        connection.execute(
            """
            INSERT INTO users (
                id, email, name, company, location, mobile, password_salt, password_hash, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                normalized_email,
                normalized_name,
                company,
                location,
                mobile,
                salt,
                password_hash,
                _now(),
            ),
        )
        for entitlement in entitlements:
            connection.execute(
                "INSERT INTO user_entitlements (user_id, entitlement_key) VALUES (?, ?)",
                (user_id, entitlement),
            )
        connection.commit()
    return login(email=normalized_email, password=password)


def reset_password_by_identity(*, email: str, name: str, password: str) -> AuthSession:
    normalized_email = email.strip().lower()
    normalized_name = " ".join(name.strip().split()).casefold()
    if len(password) < 8:
        raise WeakPasswordError("Password must be at least 8 characters.")
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (normalized_email,)).fetchone()
        if row is None or " ".join(row["name"].strip().split()).casefold() != normalized_name:
            raise InvalidCredentialsError("No account matches this name and email.")
        salt, password_hash = _hash_password(password)
        connection.execute(
            """
            UPDATE users
            SET password_salt = ?, password_hash = ?
            WHERE id = ?
            """,
            (salt, password_hash, row["id"]),
        )
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
        connection.commit()
    return login(email=normalized_email, password=password)


def reset_password_by_user_id(*, user_id: str, password: str) -> AuthUser:
    if len(password) < 8:
        raise WeakPasswordError("Password must be at least 8 characters.")
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise InvalidCredentialsError("No account matches this user.")
        salt, password_hash = _hash_password(password)
        connection.execute(
            """
            UPDATE users
            SET password_salt = ?, password_hash = ?
            WHERE id = ?
            """,
            (salt, password_hash, row["id"]),
        )
        connection.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
        connection.commit()
        return AuthUser(
            id=row["id"],
            email=row["email"],
            name=row["name"],
            company=row["company"],
            location=row["location"],
            mobile=row["mobile"],
        )


def set_user_entitlements(*, user_id: str, entitlements: tuple[str, ...]) -> tuple[str, ...]:
    ensure_auth_db()
    normalized_entitlements = tuple(sorted({item.strip() for item in entitlements if item.strip()}))
    with _LOCK, _connect() as connection:
        row = connection.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise InvalidCredentialsError("No account matches this user.")
        connection.execute("DELETE FROM user_entitlements WHERE user_id = ?", (user_id,))
        connection.executemany(
            "INSERT INTO user_entitlements (user_id, entitlement_key) VALUES (?, ?)",
            ((user_id, entitlement) for entitlement in normalized_entitlements),
        )
        connection.commit()
    return normalized_entitlements


def login(*, email: str, password: str) -> AuthSession:
    normalized_email = email.strip().lower()
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (normalized_email,)).fetchone()
        if row is None or not _verify_password(password, row["password_salt"], row["password_hash"]):
            raise InvalidCredentialsError("Invalid email or password.")
        token = secrets.token_urlsafe(32)
        connection.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, row["id"], _now(), _expires_at()),
        )
        connection.commit()
        return _session_from_user_row(connection, token, row)


def session_from_token(token: str | None) -> AuthSession | None:
    if not token:
        return None
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        row = connection.execute(
            """
            SELECT users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ?
            """,
            (token, _now()),
        ).fetchone()
        if row is None:
            return None
        return _session_from_user_row(connection, token, row)


def record_access_request(user_id: str | None, module_id: str, message: str) -> None:
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        connection.execute(
            """
            INSERT INTO access_requests (id, user_id, module_id, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), user_id, module_id, message, _now()),
        )
        connection.commit()


def list_admin_users() -> tuple[AdminUserRecord, ...]:
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        rows = connection.execute(
            """
            SELECT
                users.id,
                users.email,
                users.name,
                users.company,
                users.location,
                users.mobile,
                users.created_at,
                COUNT(DISTINCT sessions.token) AS session_count,
                MAX(sessions.created_at) AS last_session_at,
                GROUP_CONCAT(DISTINCT user_entitlements.entitlement_key) AS entitlements
            FROM users
            LEFT JOIN sessions ON sessions.user_id = users.id
            LEFT JOIN user_entitlements ON user_entitlements.user_id = users.id
            GROUP BY users.id
            ORDER BY users.created_at DESC
            """
        ).fetchall()
    return tuple(
        AdminUserRecord(
            id=row["id"],
            email=row["email"],
            name=row["name"],
            company=row["company"],
            location=row["location"],
            mobile=row["mobile"],
            created_at=row["created_at"],
            entitlements=tuple(sorted(filter(None, (row["entitlements"] or "").split(",")))),
            session_count=int(row["session_count"] or 0),
            last_session_at=row["last_session_at"],
        )
        for row in rows
    )


def _session_from_user_row(
    connection: sqlite3.Connection,
    token: str,
    row: sqlite3.Row,
) -> AuthSession:
    entitlements = connection.execute(
        """
        SELECT entitlement_key
        FROM user_entitlements
        WHERE user_id = ?
        ORDER BY entitlement_key
        """,
        (row["id"],),
    ).fetchall()
    user = AuthUser(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        company=row["company"],
        location=row["location"],
        mobile=row["mobile"],
    )
    return AuthSession(
        token=token,
        user=user,
        entitlements=tuple(item["entitlement_key"] for item in entitlements),
    )
