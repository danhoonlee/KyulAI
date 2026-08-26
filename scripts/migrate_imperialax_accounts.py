#!/usr/bin/env python3
"""Migrate the live ImperialAX account database away from legacy identities."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python 3.10 support environment
    from datetime import timezone

    UTC = timezone.utc

PRIMARY_TARGET = "dannylee@imperialax.com"
PRIMARY_SOURCES = ("dannylee9295@gmail.com", "danlee@luvelox.com")
DEMO_TARGET = "demo@imperialax.com"
DEMO_SOURCE = "demo@luvelox.com"
PRIMARY_ENTITLEMENTS = (
    "module.admin",
    "module.injection",
    "module.laminate",
    "module.optimization",
)
DEMO_ENTITLEMENTS = ("module.injection", "module.laminate")


def _user(connection: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()


def _require_user(connection: sqlite3.Connection, email: str) -> sqlite3.Row:
    user = _user(connection, email)
    if user is None:
        raise RuntimeError(f"Required account is missing after migration: {email}")
    return user


def _merge_user(
    connection: sqlite3.Connection,
    *,
    source: sqlite3.Row,
    target: sqlite3.Row,
) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO user_entitlements (user_id, entitlement_key)
        SELECT ?, entitlement_key
        FROM user_entitlements
        WHERE user_id = ?
        """,
        (target["id"], source["id"]),
    )
    connection.execute(
        "UPDATE access_requests SET user_id = ? WHERE user_id = ?",
        (target["id"], source["id"]),
    )
    # Legacy source sessions include pre-security-audit long-lived tokens. Do not carry them forward.
    connection.execute("DELETE FROM sessions WHERE user_id = ?", (source["id"],))
    connection.execute("DELETE FROM users WHERE id = ?", (source["id"],))


def _ensure_entitlements(
    connection: sqlite3.Connection,
    *,
    user_id: str,
    entitlements: tuple[str, ...],
) -> None:
    connection.executemany(
        "INSERT OR IGNORE INTO user_entitlements (user_id, entitlement_key) VALUES (?, ?)",
        ((user_id, entitlement) for entitlement in entitlements),
    )


def _account_summary(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            users.email,
            users.name,
            users.company,
            COUNT(DISTINCT sessions.token) AS session_count,
            GROUP_CONCAT(DISTINCT user_entitlements.entitlement_key) AS entitlements
        FROM users
        LEFT JOIN sessions ON sessions.user_id = users.id
        LEFT JOIN user_entitlements ON user_entitlements.user_id = users.id
        GROUP BY users.id
        ORDER BY users.created_at, users.email
        """
    ).fetchall()
    return [
        {
            "email": row["email"],
            "name": row["name"],
            "company": row["company"],
            "session_count": int(row["session_count"] or 0),
            "entitlements": sorted(filter(None, (row["entitlements"] or "").split(","))),
        }
        for row in rows
    ]


def migrate_accounts(connection: sqlite3.Connection) -> dict[str, Any]:
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    before = _account_summary(connection)
    changes: list[str] = []

    with connection:
        demo = _user(connection, DEMO_TARGET)
        legacy_demo = _user(connection, DEMO_SOURCE)
        if demo is None:
            if legacy_demo is None:
                raise RuntimeError(f"Neither {DEMO_TARGET} nor {DEMO_SOURCE} exists.")
            connection.execute(
                "UPDATE users SET email = ?, company = ? WHERE id = ?",
                (DEMO_TARGET, "ImperialAX Demo", legacy_demo["id"]),
            )
            demo = _user(connection, DEMO_TARGET)
            changes.append(f"renamed {DEMO_SOURCE} to {DEMO_TARGET}")
        elif legacy_demo is not None:
            _merge_user(connection, source=legacy_demo, target=demo)
            changes.append(f"merged and removed {DEMO_SOURCE}")
        demo = _require_user(connection, DEMO_TARGET)
        connection.execute(
            "UPDATE users SET company = ? WHERE id = ?",
            ("ImperialAX Demo", demo["id"]),
        )
        _ensure_entitlements(
            connection,
            user_id=str(demo["id"]),
            entitlements=DEMO_ENTITLEMENTS,
        )

        primary = _user(connection, PRIMARY_TARGET)
        if primary is None:
            source = next(
                (candidate for email in PRIMARY_SOURCES if (candidate := _user(connection, email))),
                None,
            )
            if source is None:
                raise RuntimeError(
                    f"No source account exists for the primary target {PRIMARY_TARGET}."
                )
            connection.execute(
                "UPDATE users SET email = ?, company = ? WHERE id = ?",
                (PRIMARY_TARGET, "ImperialAX", source["id"]),
            )
            changes.append(f"renamed {source['email']} to {PRIMARY_TARGET}")
        primary = _require_user(connection, PRIMARY_TARGET)

        for source_email in PRIMARY_SOURCES:
            source = _user(connection, source_email)
            if source is not None:
                _merge_user(connection, source=source, target=primary)
                changes.append(f"merged and removed {source_email}")

        connection.execute(
            "UPDATE users SET company = ? WHERE id = ?",
            ("ImperialAX", primary["id"]),
        )
        _ensure_entitlements(
            connection,
            user_id=str(primary["id"]),
            entitlements=PRIMARY_ENTITLEMENTS,
        )

        smoke_accounts = connection.execute(
            "SELECT * FROM users WHERE email LIKE 'local-smoke-%@luvelox.com'"
        ).fetchall()
        for smoke in smoke_accounts:
            connection.execute("DELETE FROM users WHERE id = ?", (smoke["id"],))
            changes.append(f"removed obsolete smoke account {smoke['email']}")

        legacy_rows = connection.execute(
            """
            SELECT email, company
            FROM users
            WHERE lower(email) LIKE '%luvelox%'
               OR lower(COALESCE(company, '')) LIKE '%luvelox%'
            """
        ).fetchall()
        if legacy_rows:
            values = ", ".join(str(row["email"]) for row in legacy_rows)
            raise RuntimeError(f"Legacy Luvelox identities remain: {values}")

    after = _account_summary(connection)
    return {
        "primary_admin": PRIMARY_TARGET,
        "demo_account": DEMO_TARGET,
        "changes": changes,
        "before": before,
        "after": after,
    }


def backup_database(source: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_dir / f"imperialax_auth.pre-account-migration.{stamp}.sqlite3"
    source_connection = sqlite3.connect(source)
    backup_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(backup_connection)
        integrity = backup_connection.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise RuntimeError(f"Backup integrity check failed: {integrity}")
    finally:
        backup_connection.close()
        source_connection.close()
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/imperialax_auth.sqlite3"))
    parser.add_argument("--backup-dir", type=Path, default=Path("runtime/backups/auth"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.db.is_file():
        raise SystemExit(f"Authentication database does not exist: {args.db}")

    backup_path: Path | None = None
    target_path = args.db
    temporary_directory: tempfile.TemporaryDirectory[str] | None = None
    if args.apply:
        backup_path = backup_database(args.db, args.backup_dir)
    else:
        temporary_directory = tempfile.TemporaryDirectory(prefix="imperialax-account-preview-")
        target_path = Path(temporary_directory.name) / args.db.name
        shutil.copy2(args.db, target_path)

    try:
        connection = sqlite3.connect(target_path)
        try:
            result = migrate_accounts(connection)
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            result["integrity_check"] = integrity[0] if integrity else None
        finally:
            connection.close()
    finally:
        if temporary_directory is not None:
            temporary_directory.cleanup()

    result["mode"] = "applied" if args.apply else "preview"
    result["database"] = str(args.db)
    result["backup"] = str(backup_path) if backup_path else None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
