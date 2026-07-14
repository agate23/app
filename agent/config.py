from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import sys
from pathlib import Path

APP_NAME = "Agate Remote"
APP_VERSION = "2.0.0"
PORT = int(os.getenv("AGATE_REMOTE_PORT", "8765"))
PRIVATE_ONLY = os.getenv("AGATE_REMOTE_PRIVATE_ONLY", "1") != "0"
SESSION_HOURS = int(os.getenv("AGATE_REMOTE_SESSION_HOURS", "12"))
MAX_UPLOAD_MB = int(os.getenv("AGATE_REMOTE_MAX_UPLOAD_MB", "100"))
PAIR_PIN = os.getenv("AGATE_REMOTE_PIN", "").strip() or f"{secrets.randbelow(1_000_000):06d}"

ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
WEB_DIR = ROOT_DIR / "web"
DEFAULT_PROFILES = ROOT_DIR / "profiles.json"
DATA_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / "AgateRemote"
SHARED_DIR = Path(os.getenv("AGATE_REMOTE_SHARED_DIR", Path.home() / "Downloads" / "AgateRemote"))
USER_PROFILES = DATA_DIR / "profiles.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SHARED_DIR.mkdir(parents=True, exist_ok=True)


def local_ipv4() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def tailscale_ipv4() -> str | None:
    for executable in ("tailscale", "tailscale.exe"):
        try:
            result = subprocess.run(
                [executable, "ip", "-4"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            continue
        values = result.stdout.strip().splitlines()
        if values and values[0].startswith("100."):
            return values[0]
    return None


def access_urls() -> list[str]:
    urls = [f"http://{local_ipv4()}:{PORT}"]
    tail_ip = tailscale_ipv4()
    if tail_ip:
        urls.append(f"http://{tail_ip}:{PORT}")
    return urls


def load_json(path: Path, fallback: dict) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
