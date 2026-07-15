from __future__ import annotations

import ipaddress
import json
import os
import secrets
import socket
import subprocess
import sys
from pathlib import Path

import psutil

APP_NAME = "Agate Remote"
APP_VERSION = "2.0.2"
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
LOG_FILE = DATA_DIR / "agate-remote.log"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SHARED_DIR.mkdir(parents=True, exist_ok=True)

TAILSCALE_NETWORK = ipaddress.ip_network("100.64.0.0/10")
VIRTUAL_ADAPTER_WORDS = (
    "virtual",
    "vmware",
    "virtualbox",
    "hyper-v",
    "vethernet",
    "wsl",
    "docker",
    "loopback",
    "bluetooth",
    "tailscale",
    "hamachi",
    "zerotier",
)
PHYSICAL_ADAPTER_WORDS = ("wi-fi", "wifi", "wireless", "wlan", "ethernet", "rede local")


def _default_route_ipv4() -> str | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("1.1.1.1", 80))
        value = sock.getsockname()[0]
        return value if value and not value.startswith("127.") else None
    except OSError:
        return None
    finally:
        sock.close()


def _is_lan_ipv4(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (
        address.version == 4
        and address.is_private
        and not address.is_loopback
        and not address.is_link_local
        and address not in TAILSCALE_NETWORK
    )


def local_ipv4_candidates() -> list[str]:
    default_address = _default_route_ipv4()
    stats = psutil.net_if_stats()
    ranked: list[tuple[int, str]] = []

    for interface, addresses in psutil.net_if_addrs().items():
        state = stats.get(interface)
        if state is not None and not state.isup:
            continue

        lowered = interface.casefold()
        if any(word in lowered for word in VIRTUAL_ADAPTER_WORDS):
            continue

        for item in addresses:
            if item.family != socket.AF_INET or not _is_lan_ipv4(item.address):
                continue
            score = 0
            if item.address == default_address:
                score += 100
            if any(word in lowered for word in PHYSICAL_ADAPTER_WORDS):
                score += 40
            ranked.append((score, item.address))

    if default_address and _is_lan_ipv4(default_address):
        ranked.append((120, default_address))

    ordered: list[str] = []
    for _score, address in sorted(ranked, key=lambda value: value[0], reverse=True):
        if address not in ordered:
            ordered.append(address)

    if ordered:
        return ordered
    try:
        for address in socket.gethostbyname_ex(socket.gethostname())[2]:
            if _is_lan_ipv4(address) and address not in ordered:
                ordered.append(address)
    except OSError:
        pass
    return ordered


def local_ipv4() -> str:
    candidates = local_ipv4_candidates()
    return candidates[0] if candidates else "127.0.0.1"


def local_control_url() -> str:
    return f"http://127.0.0.1:{PORT}"


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
        for value in result.stdout.strip().splitlines():
            try:
                address = ipaddress.ip_address(value.strip())
            except ValueError:
                continue
            if address in TAILSCALE_NETWORK:
                return str(address)
    return None


def access_urls() -> list[str]:
    urls = [f"http://{address}:{PORT}" for address in local_ipv4_candidates()]
    tail_ip = tailscale_ipv4()
    if tail_ip:
        urls.append(f"http://{tail_ip}:{PORT}")
    if not urls:
        urls.append(local_control_url())
    return list(dict.fromkeys(urls))


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
