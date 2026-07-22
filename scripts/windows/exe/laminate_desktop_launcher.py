"""Double-click launcher for the existing Laminate Forecast Windows bundle."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

import requests


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def wait_for_backend(base_url: str, timeout: float, debug: bool) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for endpoint in ("/ready", "/health"):
            try:
                response = requests.get(base_url + endpoint, timeout=1.5)
                if response.status_code < 500:
                    if debug:
                        print(f"Backend ready via {endpoint}: {response.status_code}")
                    return True
            except requests.RequestException as exc:
                if debug:
                    print(f"Waiting for backend {endpoint}: {exc}")
        time.sleep(0.8)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--port", type=int, default=int(os.environ.get("LAMINATE_PORT", "8765")))
    parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()

    root = app_dir()
    backend_exe = root / "backend" / "laminate_backend.exe"
    if not backend_exe.exists():
        raise FileNotFoundError(f"Missing backend executable: {backend_exe}")

    env = os.environ.copy()
    env["LAMINATE_HOST"] = "127.0.0.1"
    env["LAMINATE_PORT"] = str(args.port)
    env["LAMINATE_REQUIRE_AUTH"] = "1"
    env["IMPERIALAX_DISABLE_DEMO_LOGIN"] = "1"
    env["KYULAI_PROJECT_ROOT"] = str(root)
    env["LAMINATE_FRONTEND_DIR"] = str(root / "src" / "frontend" / "dd-laminate")
    env["IMPERIALAX_FRONTEND_DIR"] = str(root / "src" / "frontend" / "imperialax")
    env.setdefault("LAMINATE_ENV", "portable_exe")

    stdout = None if args.debug else subprocess.DEVNULL
    stderr = None if args.debug else subprocess.DEVNULL
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        [str(backend_exe)],
        cwd=str(root),
        env=env,
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
    )

    base_url = f"http://127.0.0.1:{args.port}"
    try:
        if not wait_for_backend(base_url, args.timeout, args.debug):
            print(f"Laminate backend did not become ready within {args.timeout} seconds.")
            return 2
        webbrowser.open(base_url)
        print("Laminate Forecast is running in licensed local mode.")
        print(base_url)
        print("Close this window to stop the backend.")
        while process.poll() is None:
            time.sleep(1.0)
        return process.returncode or 0
    finally:
        if process.poll() is None:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
                time.sleep(1.0)
            if process.poll() is None:
                process.terminate()
                time.sleep(1.0)
            if process.poll() is None:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
