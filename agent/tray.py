from __future__ import annotations

import json
import os
import socket
import threading
import webbrowser
from pathlib import Path
from typing import Callable

import pyperclip
import pystray
import qrcode
from PIL import Image, ImageDraw

from agent.config import APP_NAME, APP_VERSION, DATA_DIR, PAIR_PIN, SHARED_DIR, access_urls


def icon_image() -> Image.Image:
    image = Image.new("RGB", (64, 64), "#171221")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 12, 56, 49), radius=7, fill="#7c3aed")
    draw.rectangle((28, 49, 36, 57), fill="#d8b4fe")
    draw.rectangle((19, 56, 45, 60), fill="#d8b4fe")
    draw.ellipse((44, 5, 60, 21), fill="#22c55e")
    return image


def qr_path() -> Path:
    payload = json.dumps({"url": access_urls()[-1], "pin": PAIR_PIN, "name": socket.gethostname()})
    image = qrcode.make(payload)
    path = DATA_DIR / "pairing-qr.png"
    image.save(path)
    return path


def start_tray(start_server: Callable[[], None]) -> None:
    threading.Thread(target=start_server, daemon=True, name="agate-server").start()

    def open_control(_icon=None, _item=None) -> None:
        webbrowser.open(access_urls()[0])

    def show_qr(_icon=None, _item=None) -> None:
        path = qr_path()
        os.startfile(path) if os.name == "nt" else webbrowser.open(path.as_uri())

    def copy_pairing(_icon=None, _item=None) -> None:
        pyperclip.copy(f"{access_urls()[-1]} | PIN {PAIR_PIN}")

    def open_shared(_icon=None, _item=None) -> None:
        os.startfile(SHARED_DIR) if os.name == "nt" else webbrowser.open(SHARED_DIR.as_uri())

    def stop(icon: pystray.Icon, _item=None) -> None:
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Abrir controle", open_control, default=True),
        pystray.MenuItem("Mostrar QR Code", show_qr),
        pystray.MenuItem("Copiar endereço e PIN", copy_pairing),
        pystray.MenuItem("Abrir pasta compartilhada", open_shared),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sair", stop),
    )
    icon = pystray.Icon("AgateRemote", icon_image(), f"{APP_NAME} {APP_VERSION} • PIN {PAIR_PIN}", menu)
    icon.run()
