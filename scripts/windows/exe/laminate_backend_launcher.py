"""PyInstaller entry point for the Laminate Forecast local backend."""

from __future__ import annotations

import os

import uvicorn


def main() -> int:
    host = os.environ.get("LAMINATE_HOST", "127.0.0.1")
    port = int(os.environ.get("LAMINATE_PORT", "8765"))
    os.environ.setdefault("LAMINATE_REQUIRE_AUTH", "1")
    os.environ.setdefault("IMPERIALAX_ENABLE_DEMO_LOGIN", "0")
    uvicorn.run(
        "src.backend.dd_laminate_app:app",
        host=host,
        port=port,
        log_level=os.environ.get("LAMINATE_LOG_LEVEL", "info"),
        factory=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
