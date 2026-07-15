from __future__ import annotations

import faulthandler
import logging
import socket
import sys
from logging.handlers import RotatingFileHandler

import psutil
import pyautogui
import pyperclip
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.auth import pair, request_ip, require_session, websocket_authorized
from agent.config import (
    APP_NAME,
    APP_VERSION,
    LOG_FILE,
    MAX_UPLOAD_MB,
    PAIR_PIN,
    PORT,
    PRIVATE_ONLY,
    SHARED_DIR,
    WEB_DIR,
    access_urls,
    tailscale_ipv4,
)
from agent.files import list_shared_files, resolve_download, save_stream
from agent.input_control import execute
from agent.profiles import load_profiles, save_profiles
from agent.security import is_allowed_address
from agent.tray import start_tray
from agent.webrtc import close_all, create_answer

app = FastAPI(title=APP_NAME, version=APP_VERSION, docs_url=None, redoc_url=None)
_LOG_STREAM = None


class PairRequest(BaseModel):
    pin: str = Field(min_length=6, max_length=6)


class WebRtcOffer(BaseModel):
    sdp: str
    type: str
    fps: int = Field(default=20, ge=5, le=30)
    quality: int = Field(default=70, ge=30, le=90)


class ProfilesPayload(BaseModel):
    profiles: list[dict]


@app.middleware("http")
async def network_guard(request: Request, call_next):
    address = request_ip(request)
    if not is_allowed_address(address, PRIVATE_ONLY):
        return JSONResponse({"detail": "Acesso permitido somente pela rede local ou Tailscale"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/info")
async def info():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "computer": socket.gethostname(),
        "urls": access_urls(),
        "tailscale": tailscale_ipv4() is not None,
        "maxUploadMb": MAX_UPLOAD_MB,
    }


@app.post("/api/pair")
async def pair_device(body: PairRequest, request: Request):
    token = pair(request_ip(request), body.pin, PAIR_PIN)
    return {"token": token, "expiresHours": 12}


@app.get("/api/status")
async def status(_token: str = Depends(require_session)):
    battery = psutil.sensors_battery()
    return {
        "cpu": psutil.cpu_percent(interval=None),
        "memory": psutil.virtual_memory().percent,
        "battery": None if battery is None else round(battery.percent),
        "plugged": None if battery is None else battery.power_plugged,
        "clipboard": pyperclip.paste()[:10_000],
    }


@app.get("/api/profiles")
async def get_profiles(_token: str = Depends(require_session)):
    return load_profiles()


@app.put("/api/profiles")
async def put_profiles(body: ProfilesPayload, _token: str = Depends(require_session)):
    try:
        return save_profiles(body.model_dump())
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/files")
async def get_files(_token: str = Depends(require_session)):
    return {"folder": str(SHARED_DIR), "files": list_shared_files()}


@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...), _token: str = Depends(require_session)):
    try:
        item = save_stream(file.filename or "arquivo", file.file)
    except ValueError as exc:
        raise HTTPException(413, str(exc)) from exc
    finally:
        await file.close()
    return item


@app.get("/api/files/{filename}")
async def download_file(filename: str, _token: str = Depends(require_session)):
    try:
        path = resolve_download(filename)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(404, "Arquivo não encontrado") from exc
    return FileResponse(path, filename=path.name)


@app.post("/api/webrtc/offer")
async def webrtc_offer(body: WebRtcOffer, _token: str = Depends(require_session)):
    return await create_answer(body.sdp, body.type, body.fps, body.quality)


@app.websocket("/ws/control")
async def control_socket(websocket: WebSocket):
    if not websocket_authorized(websocket):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_json()
            try:
                result = execute(message)
            except (ValueError, pyautogui.FailSafeException) as exc:
                result = {"ok": False, "error": str(exc)}
            await websocket.send_json(result)
    except WebSocketDisconnect:
        return


@app.on_event("shutdown")
async def shutdown_event():
    await close_all()


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")


def configure_runtime_logging() -> None:
    global _LOG_STREAM
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _LOG_STREAM is None or _LOG_STREAM.closed:
        _LOG_STREAM = LOG_FILE.open("a", encoding="utf-8", buffering=1)

    # Aplicativos PyInstaller sem console deixam stdout/stderr como None. Uvicorn
    # e bibliotecas de mídia esperam esses canais e podem falhar antes de abrir a porta.
    if sys.stdout is None:
        sys.stdout = _LOG_STREAM
    if sys.stderr is None:
        sys.stderr = _LOG_STREAM

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(handler, RotatingFileHandler) for handler in root.handlers):
        handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)

    try:
        faulthandler.enable(_LOG_STREAM)
    except (RuntimeError, OSError):
        pass


def serve() -> None:
    configure_runtime_logging()
    logging.getLogger(__name__).info(
        "Iniciando %s %s em 0.0.0.0:%s; web=%s",
        APP_NAME,
        APP_VERSION,
        PORT,
        WEB_DIR,
    )
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=PORT,
        log_config=None,
        access_log=False,
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    server.run()
    if not server.started:
        raise RuntimeError(f"Uvicorn encerrou sem abrir a porta {PORT}.")


if __name__ == "__main__":
    configure_runtime_logging()
    if "--server-only" in sys.argv:
        serve()
    else:
        logging.getLogger(__name__).info("Abrindo bandeja do %s %s", APP_NAME, APP_VERSION)
        start_tray(serve)
