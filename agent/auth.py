from __future__ import annotations

import secrets
import threading
import time
from collections import defaultdict

from fastapi import Header, HTTPException, Request, WebSocket

from agent.config import PRIVATE_ONLY, SESSION_HOURS
from agent.security import SessionStore, is_allowed_address

sessions = SessionStore(SESSION_HOURS)
_attempts: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()


def request_ip(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"


def bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    scheme, _, token = value.partition(" ")
    return token if scheme.lower() == "bearer" and token else None


def require_session(request: Request, authorization: str | None = Header(default=None)) -> str:
    address = request_ip(request)
    if not is_allowed_address(address, PRIVATE_ONLY):
        raise HTTPException(403, "Acesso permitido somente pela rede local ou Tailscale")
    token = bearer_token(authorization)
    if not sessions.valid(token, address):
        raise HTTPException(401, "Sessão inválida ou expirada")
    return token or ""


def websocket_authorized(websocket: WebSocket) -> bool:
    address = websocket.client.host if websocket.client else "127.0.0.1"
    token = websocket.query_params.get("token")
    return is_allowed_address(address, PRIVATE_ONLY) and sessions.valid(token, address)


def pair(address: str, supplied_pin: str, expected_pin: str) -> str:
    now = time.time()
    with _lock:
        recent = [stamp for stamp in _attempts[address] if now - stamp < 300]
        _attempts[address] = recent
        if len(recent) >= 8:
            raise HTTPException(429, "Muitas tentativas. Aguarde cinco minutos.")
        if not secrets.compare_digest(supplied_pin.strip(), expected_pin):
            recent.append(now)
            raise HTTPException(401, "PIN incorreto")
        _attempts.pop(address, None)
    return sessions.create(address)
