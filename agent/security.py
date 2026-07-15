from __future__ import annotations

import hashlib
import ipaddress
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

TAILSCALE_NETWORK = ipaddress.ip_network("100.64.0.0/10")


def is_allowed_address(value: str, private_only: bool = True) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    if not private_only:
        return True
    return address.is_loopback or address.is_private or address.is_link_local or address in TAILSCALE_NETWORK


def sanitize_filename(value: str) -> str:
    name = Path(value or "arquivo").name
    safe = "".join(char for char in name if char.isalnum() or char in "._- ()").strip(" .")[:160]
    return safe or "arquivo"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Session:
    client_ip: str
    expires_at: datetime


class SessionStore:
    def __init__(self, lifetime_hours: int = 12) -> None:
        self.lifetime = timedelta(hours=lifetime_hours)
        self.sessions: dict[str, Session] = {}
        self.lock = threading.Lock()

    def create(self, client_ip: str) -> str:
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.sessions[token] = Session(client_ip, datetime.now(timezone.utc) + self.lifetime)
        return token

    def valid(self, token: str | None, client_ip: str) -> bool:
        if not token:
            return False
        with self.lock:
            session = self.sessions.get(token)
            if not session or session.expires_at <= datetime.now(timezone.utc):
                self.sessions.pop(token, None)
                return False
            return secrets.compare_digest(session.client_ip, client_ip)
