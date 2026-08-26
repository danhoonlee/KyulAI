"""Small SQLite-backed account store for the ImperialAX MVP workspace."""

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

    _UTC = _timezone.utc

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "imperialax_auth.sqlite3"
DEFAULT_ENTITLEMENTS = ("module.laminate", "module.injection")
DEMO_ENTITLEMENTS = {
    "demo@imperialax.com": ("module.laminate", "module.injection"),
}
DEMO_EMAILS = frozenset(DEMO_ENTITLEMENTS)
DEMO_LOGIN_EMAILS = DEMO_EMAILS
LEGACY_DEMO_TOKENS = frozenset({"demo-token", "danlee-token"})

_PBKDF2_ITERATIONS = 210_000
_LOCK = threading.Lock()
_INITIALIZED_DATABASES: set[tuple[str, bool]] = set()


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
    expires_at: str


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
    return Path(os.environ.get("IMPERIALAX_AUTH_DB_PATH", DEFAULT_DB_PATH))


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _demo_access_enabled() -> bool:
    return _env_flag("IMPERIALAX_ENABLE_DEMO_LOGIN")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    path.chmod(0o600)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _now() -> str:
    return datetime.now(_UTC).isoformat()


def _positive_int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def _session_ttl_seconds(*, demo: bool = False) -> int:
    if demo:
        return _positive_int_env("IMPERIALAX_DEMO_SESSION_TTL_SECONDS", 4 * 60 * 60)
    return _positive_int_env("IMPERIALAX_SESSION_TTL_SECONDS", 12 * 60 * 60)


def _expires_at(ttl_seconds: int) -> str:
    return (datetime.now(_UTC) + timedelta(seconds=ttl_seconds)).isoformat()


def _launch_code_ttl_seconds() -> int:
    return _positive_int_env("IMPERIALAX_LAUNCH_CODE_TTL_SECONDS", 60)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    password = password or ""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, password_hash: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    _, candidate = _hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


def ensure_auth_db() -> None:
    signature = (str(_db_path().resolve()), _demo_access_enabled())
    with _LOCK, _connect() as connection:
        if signature in _INITIALIZED_DATABASES:
            return
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

            CREATE TABLE IF NOT EXISTS launch_codes (
                code_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                target TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_launch_codes_expires_at
            ON launch_codes(expires_at);
            """
        )
        _ensure_user_profile_columns(connection)
        _hash_legacy_session_tokens(connection)
        if _demo_access_enabled():
            _seed_demo_accounts(connection)
        connection.commit()
        _INITIALIZED_DATABASES.add(signature)


def _ensure_user_profile_columns(connection: sqlite3.Connection) -> None:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
    if "location" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN location TEXT")
    if "mobile" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN mobile TEXT")


def _hash_legacy_session_tokens(connection: sqlite3.Connection) -> None:
    rows = connection.execute("SELECT token FROM sessions").fetchall()
    for row in rows:
        token = row["token"]
        if len(token) == 64:
            try:
                bytes.fromhex(token)
                continue
            except ValueError:
                pass
        connection.execute(
            "UPDATE sessions SET token = ? WHERE token = ?",
            (_token_hash(token), token),
        )


def _seed_demo_accounts(connection: sqlite3.Connection) -> None:
    demo_accounts = (("demo-user", "demo@imperialax.com", "Demo Account", "ImperialAX MVP", ""),)
    for user_id, email, name, company, password in demo_accounts:
        existing = connection.execute(
            "SELECT id, password_salt, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
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
        elif not _verify_password("", existing["password_salt"], existing["password_hash"]):
            # Demo credentials are controlled by the feature flag, not by a
            # persisted password. Refresh legacy demo rows so enabling the
            # public demo cannot leave an older seeded password behind.
            salt, password_hash = _hash_password(password)
            connection.execute(
                """
                UPDATE users
                SET password_salt = ?, password_hash = ?
                WHERE email = ?
                """,
                (salt, password_hash, email),
            )
        allowed_entitlements = DEMO_ENTITLEMENTS[email]
        placeholders = ", ".join("?" for _ in allowed_entitlements)
        connection.execute(
            f"""
            DELETE FROM user_entitlements
            WHERE user_id = (SELECT id FROM users WHERE email = ?)
              AND entitlement_key NOT IN ({placeholders})
            """,
            (email, *allowed_entitlements),
        )
        for entitlement in allowed_entitlements:
            connection.execute(
                """
                INSERT OR IGNORE INTO user_entitlements (user_id, entitlement_key)
                VALUES ((SELECT id FROM users WHERE email = ?), ?)
                """,
                (email, entitlement),
            )


def create_account(
    *,
    email: str,
    password: str,
    name: str,
    company: str | None = None,
    location: str | None = None,
    mobile: str | None = None,
    entitlements: tuple[str, ...] = (),
) -> AuthSession:
    normalized_email = email.strip().lower()
    normalized_name = name.strip() or normalized_email.partition("@")[0]
    if len(password) < 8:
        raise WeakPasswordError("Password must be at least 8 characters.")
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE email = ?", (normalized_email,)
        ).fetchone()
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


def create_account_by_admin(
    *,
    email: str,
    password: str,
    name: str,
    company: str | None = None,
    location: str | None = None,
    mobile: str | None = None,
    entitlements: tuple[str, ...] = DEFAULT_ENTITLEMENTS,
) -> AuthUser:
    normalized_email = email.strip().lower()
    normalized_name = name.strip() or normalized_email.partition("@")[0]
    if len(password) < 8:
        raise WeakPasswordError("Password must be at least 8 characters.")
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        existing = connection.execute(
            "SELECT id FROM users WHERE email = ?", (normalized_email,)
        ).fetchone()
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
        normalized_entitlements = tuple(
            sorted({item.strip() for item in entitlements if item.strip()})
        )
        connection.executemany(
            "INSERT INTO user_entitlements (user_id, entitlement_key) VALUES (?, ?)",
            ((user_id, entitlement) for entitlement in normalized_entitlements),
        )
        connection.commit()
        return AuthUser(
            id=user_id,
            email=normalized_email,
            name=normalized_name,
            company=company,
            location=location,
            mobile=mobile,
        )


def reset_password_by_identity(*, email: str, name: str, password: str) -> AuthSession:
    normalized_email = email.strip().lower()
    normalized_name = " ".join(name.strip().split()).casefold()
    if len(password) < 8:
        raise WeakPasswordError("Password must be at least 8 characters.")
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE email = ?", (normalized_email,)
        ).fetchone()
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
        row = connection.execute("SELECT id, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise InvalidCredentialsError("No account matches this user.")
        if row["email"] in DEMO_LOGIN_EMAILS:
            normalized_entitlements = DEMO_ENTITLEMENTS[row["email"]]
        connection.execute("DELETE FROM user_entitlements WHERE user_id = ?", (user_id,))
        connection.executemany(
            "INSERT INTO user_entitlements (user_id, entitlement_key) VALUES (?, ?)",
            ((user_id, entitlement) for entitlement in normalized_entitlements),
        )
        connection.commit()
    return normalized_entitlements


def update_user_profile(
    *,
    user_id: str,
    name: str,
    company: str | None = None,
    location: str | None = None,
    mobile: str | None = None,
) -> AuthUser:
    normalized_name = name.strip()
    if not normalized_name:
        raise InvalidCredentialsError("Name is required.")
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        row = connection.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise InvalidCredentialsError("No account matches this user.")
        connection.execute(
            """
            UPDATE users
            SET name = ?, company = ?, location = ?, mobile = ?
            WHERE id = ?
            """,
            (normalized_name, company, location, mobile, user_id),
        )
        connection.commit()
        updated = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return AuthUser(
            id=updated["id"],
            email=updated["email"],
            name=updated["name"],
            company=updated["company"],
            location=updated["location"],
            mobile=updated["mobile"],
        )


def login(*, email: str, password: str, allow_demo: bool = False) -> AuthSession:
    normalized_email = email.strip().lower()
    is_allowed_demo_login = (
        allow_demo
        and normalized_email in DEMO_LOGIN_EMAILS
        and _demo_access_enabled()
        and password == ""
    )
    if not password and not is_allowed_demo_login:
        raise InvalidCredentialsError("Invalid email or password.")
    if normalized_email in DEMO_LOGIN_EMAILS and not is_allowed_demo_login:
        raise InvalidCredentialsError("Invalid email or password.")
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE email = ?", (normalized_email,)
        ).fetchone()
        if row is None or not _verify_password(
            password, row["password_salt"], row["password_hash"]
        ):
            raise InvalidCredentialsError("Invalid email or password.")
        token, expires_at = _insert_session(
            connection,
            user_id=row["id"],
            ttl_seconds=_session_ttl_seconds(demo=is_allowed_demo_login),
        )
        connection.commit()
        return _session_from_user_row(connection, token, row, expires_at)


def session_from_token(token: str | None) -> AuthSession | None:
    if not token or token in LEGACY_DEMO_TOKENS:
        return None
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        row = connection.execute(
            """
            SELECT users.*, sessions.expires_at AS session_expires_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ? AND sessions.expires_at > ?
            """,
            (_token_hash(token), _now()),
        ).fetchone()
        if row is None:
            return None
        if row["email"] in DEMO_LOGIN_EMAILS and not _demo_access_enabled():
            return None
        return _session_from_user_row(connection, token, row, row["session_expires_at"])


def revoke_session(token: str | None) -> bool:
    if not token:
        return False
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        cursor = connection.execute("DELETE FROM sessions WHERE token = ?", (_token_hash(token),))
        connection.commit()
        return cursor.rowcount > 0


def issue_launch_code(*, session_token: str, target: str) -> tuple[str, str]:
    session = session_from_token(session_token)
    if session is None:
        raise InvalidCredentialsError("The session is invalid or expired.")
    code = secrets.token_urlsafe(32)
    expires_at = _expires_at(_launch_code_ttl_seconds())
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        connection.execute("DELETE FROM launch_codes WHERE expires_at <= ?", (_now(),))
        connection.execute(
            """
            INSERT INTO launch_codes (code_hash, user_id, target, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (_token_hash(code), session.user.id, target, _now(), expires_at),
        )
        connection.commit()
    return code, expires_at


def consume_launch_code(*, code: str, target: str) -> AuthSession | None:
    if not code:
        return None
    ensure_auth_db()
    with _LOCK, _connect() as connection:
        row = connection.execute(
            """
            SELECT launch_codes.*, users.*
            FROM launch_codes
            JOIN users ON users.id = launch_codes.user_id
            WHERE launch_codes.code_hash = ?
              AND launch_codes.target = ?
              AND launch_codes.consumed_at IS NULL
              AND launch_codes.expires_at > ?
            """,
            (_token_hash(code), target, _now()),
        ).fetchone()
        if row is None:
            return None
        consumed_at = _now()
        cursor = connection.execute(
            """
            UPDATE launch_codes
            SET consumed_at = ?
            WHERE code_hash = ? AND consumed_at IS NULL
            """,
            (consumed_at, _token_hash(code)),
        )
        if cursor.rowcount != 1:
            connection.rollback()
            return None
        is_demo = row["email"] in DEMO_LOGIN_EMAILS
        token, expires_at = _insert_session(
            connection,
            user_id=row["user_id"],
            ttl_seconds=_session_ttl_seconds(demo=is_demo),
        )
        connection.commit()
        return _session_from_user_row(connection, token, row, expires_at)


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
    expires_at: str,
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
        expires_at=expires_at,
    )


def _insert_session(
    connection: sqlite3.Connection,
    *,
    user_id: str,
    ttl_seconds: int,
) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    expires_at = _expires_at(ttl_seconds)
    connection.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (_token_hash(token), user_id, _now(), expires_at),
    )
    return token, expires_at
