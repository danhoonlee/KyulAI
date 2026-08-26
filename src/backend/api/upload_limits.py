"""Shared upload-size guards for public multipart API endpoints."""

from __future__ import annotations

import os

from fastapi import HTTPException, UploadFile, status

DEFAULT_CSV_UPLOAD_LIMIT_BYTES = 16 * 1024 * 1024
DEFAULT_CSV_BATCH_LIMIT_BYTES = 256 * 1024 * 1024


def _positive_env_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def csv_upload_limit_bytes() -> int:
    """Return the configured per-file CSV limit."""
    return _positive_env_int("IMPERIALAX_MAX_CSV_UPLOAD_BYTES", DEFAULT_CSV_UPLOAD_LIMIT_BYTES)


def csv_batch_limit_bytes() -> int:
    """Return the configured cumulative CSV batch limit."""
    return _positive_env_int("IMPERIALAX_MAX_CSV_BATCH_BYTES", DEFAULT_CSV_BATCH_LIMIT_BYTES)


async def read_upload_limited(
    upload: UploadFile,
    *,
    max_bytes: int | None = None,
    description: str = "CSV file",
) -> bytes:
    """Read at most one byte beyond the limit and reject oversized uploads."""
    limit = max_bytes if max_bytes is not None else csv_upload_limit_bytes()
    content = await upload.read(limit + 1)
    if len(content) > limit:
        limit_mib = limit / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{description} exceeds the {limit_mib:g} MiB upload limit.",
        )
    return content
