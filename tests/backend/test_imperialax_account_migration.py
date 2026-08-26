from __future__ import annotations

import sqlite3

from scripts.migrate_imperialax_accounts import migrate_accounts


def _legacy_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE users (
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
        CREATE TABLE user_entitlements (
            user_id TEXT NOT NULL,
            entitlement_key TEXT NOT NULL,
            PRIMARY KEY (user_id, entitlement_key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE access_requests (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            module_id TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """
    )
    users = (
        ("demo", "demo@luvelox.com", "Demo", "Luvelox MVP", "demo-hash"),
        ("legacy-admin", "danlee@luvelox.com", "Dan Lee", "Luvelox", "legacy-hash"),
        ("primary", "dannylee9295@gmail.com", "Danny Lee", "Luvelox", "primary-hash"),
        ("smoke", "local-smoke-1@luvelox.com", "Smoke", "Luvelox", "smoke-hash"),
        ("member", "member@example.com", "Member", "G3MS", "member-hash"),
    )
    connection.executemany(
        """
        INSERT INTO users (
            id, email, name, company, location, mobile, password_salt, password_hash, created_at
        ) VALUES (?, ?, ?, ?, NULL, NULL, 'salt', ?, '2026-01-01T00:00:00+00:00')
        """,
        users,
    )
    connection.executemany(
        "INSERT INTO user_entitlements (user_id, entitlement_key) VALUES (?, ?)",
        (
            ("demo", "module.laminate"),
            ("legacy-admin", "module.optimization"),
            ("primary", "module.laminate"),
            ("smoke", "module.injection"),
        ),
    )
    connection.executemany(
        "INSERT INTO sessions VALUES (?, ?, '2026-01-01', '2099-01-01')",
        (("demo-token-old", "demo"), ("legacy-token", "legacy-admin"), ("primary-token", "primary")),
    )
    connection.execute(
        "INSERT INTO access_requests VALUES ('request', 'legacy-admin', 'optimization', 'access', '2026-01-01')"
    )
    connection.commit()
    return connection


def test_migration_preserves_primary_and_demo_credentials_and_removes_legacy_accounts() -> None:
    connection = _legacy_database()

    result = migrate_accounts(connection)

    users = {
        row["email"]: row
        for row in connection.execute("SELECT * FROM users ORDER BY email").fetchall()
    }
    assert set(users) == {
        "dannylee@imperialax.com",
        "demo@imperialax.com",
        "member@example.com",
    }
    assert users["dannylee@imperialax.com"]["password_hash"] == "primary-hash"
    assert users["demo@imperialax.com"]["password_hash"] == "demo-hash"
    assert users["dannylee@imperialax.com"]["company"] == "ImperialAX"
    assert users["demo@imperialax.com"]["company"] == "ImperialAX Demo"

    admin_entitlements = {
        row[0]
        for row in connection.execute(
            "SELECT entitlement_key FROM user_entitlements WHERE user_id = 'primary'"
        )
    }
    assert admin_entitlements == {
        "module.admin",
        "module.injection",
        "module.laminate",
        "module.optimization",
    }
    assert connection.execute(
        "SELECT user_id FROM access_requests WHERE id = 'request'"
    ).fetchone()[0] == "primary"
    assert connection.execute("SELECT COUNT(*) FROM sessions WHERE token = 'legacy-token'").fetchone()[
        0
    ] == 0
    assert connection.execute("SELECT COUNT(*) FROM sessions WHERE token = 'primary-token'").fetchone()[
        0
    ] == 1
    assert result["primary_admin"] == "dannylee@imperialax.com"


def test_migration_is_idempotent() -> None:
    connection = _legacy_database()
    migrate_accounts(connection)

    second = migrate_accounts(connection)

    assert second["changes"] == []
    assert all("luvelox" not in str(account).lower() for account in second["after"])
