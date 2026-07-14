from __future__ import annotations

import socket

import psutil
import pyautogui
import pyperclip
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.auth import pair, request_ip, require_session, websocket_authorized
from agent.config import APP_NAME, APP_VERSION, MAX_UPLOAD_MB, PAIR_PIN, PORT, PRIVATE_ONLY, SHARED_DIR, WEB_DIR, access_urls, tailscale_ipv4
from agent.files import list_shared_files, resolve_download, save_stream
from agent.input_control import execute
from agent.profiles import load_profiles, save_profiles
from agent.security import is_allowed_address
from agent.tray import start_tray
from agent.webrtc import close_all, create_answer

app = FastAPI(title=APP_NAME, version=APP_VERSION, docs_url=None, redoc_url=None)


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


def serve() -> None:
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")


if __name__ == "__main__":
    print(f"{APP_NAME} {APP_VERSION}")
    print(f"PIN de pareamento: {PAIR_PIN}")
    for url in access_urls():
        print(f"Acesso: {url}")
    start_tray(serve)
