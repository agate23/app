from __future__ import annotations

import ctypes
import json
import logging
import os
import socket
import subprocess
import threading
import time
import traceback
import webbrowser
from pathlib import Path
from typing import Callable

import pyperclip
import pystray
import qrcode
from PIL import Image, ImageDraw

from agent.config import (
    APP_NAME,
    APP_VERSION,
    DATA_DIR,
    LOG_FILE,
    PAIR_PIN,
    PORT,
    SHARED_DIR,
    access_urls,
    local_control_url,
)

FIREWALL_RULE_NAME = "Agate Remote TCP 8765"


def icon_image() -> Image.Image:
    image = Image.new("RGB", (64, 64), "#171221")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 12, 56, 49), radius=7, fill="#7c3aed")
    draw.rectangle((28, 49, 36, 57), fill="#d8b4fe")
    draw.rectangle((19, 56, 45, 60), fill="#d8b4fe")
    draw.ellipse((44, 5, 60, 21), fill="#22c55e")
    return image


def _message(text: str, title: str = APP_NAME, flags: int = 0x40) -> int:
    if os.name != "nt":
        return 0
    return int(ctypes.windll.user32.MessageBoxW(None, text, title, flags))


def _server_ready(timeout: float = 25.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.25)
    return False


def _tail_log(max_chars: int = 3500) -> str:
    try:
        text = LOG_FILE.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return "O arquivo de log ainda não foi criado."
    if not text:
        return "O arquivo de log está vazio."
    return text[-max_chars:]


def open_log(_icon=None, _item=None) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.touch(exist_ok=True)
        if os.name == "nt":
            os.startfile(LOG_FILE)
        else:
            webbrowser.open(LOG_FILE.as_uri())
    except OSError as exc:
        _message(f"Não foi possível abrir o log.\n\n{exc}", flags=0x10)


def _firewall_rule_exists() -> bool:
    if os.name != "nt":
        return True
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={FIREWALL_RULE_NAME}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and FIREWALL_RULE_NAME.casefold() in result.stdout.casefold()


def request_firewall_rule(_icon=None, _item=None) -> None:
    if os.name != "nt":
        return
    arguments = (
        "advfirewall firewall add rule "
        f'name="{FIREWALL_RULE_NAME}" dir=in action=allow protocol=TCP '
        f"localport={PORT} profile=any enable=yes"
    )
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", "netsh.exe", arguments, None, 0)
    if int(result) <= 32:
        _message("Não foi possível solicitar a liberação do Firewall do Windows.", flags=0x10)


def _offer_firewall_setup() -> None:
    if os.name != "nt" or _firewall_rule_exists():
        return
    answer = _message(
        "Para o celular acessar este PC, o Agate Remote precisa liberar a porta 8765 no Firewall do Windows.\n\n"
        "Deseja configurar agora? Será exibida uma confirmação de administrador.",
        flags=0x24,
    )
    if answer == 6:
        request_firewall_rule()


def qr_path() -> Path:
    urls = access_urls()
    payload = json.dumps(
        {"url": urls[0], "urls": urls, "pin": PAIR_PIN, "name": socket.gethostname()},
        ensure_ascii=False,
    )
    image = qrcode.make(payload)
    path = DATA_DIR / "pairing-qr.png"
    image.save(path)
    return path


def start_tray(start_server: Callable[[], None]) -> None:
    server_failed = threading.Event()

    def server_worker() -> None:
        try:
            start_server()
        except BaseException:
            server_failed.set()
            details = traceback.format_exc()
            try:
                with LOG_FILE.open("a", encoding="utf-8") as output:
                    output.write("\nFALHA FATAL DO SERVIDOR\n")
                    output.write(details)
                    output.write("\n")
            except OSError:
                pass
            logging.getLogger(__name__).exception("O servidor do Agate Remote não conseguiu iniciar")

    threading.Thread(target=server_worker, daemon=True, name="agate-server").start()
    threading.Thread(target=_offer_firewall_setup, daemon=True, name="agate-firewall").start()

    def open_control(_icon=None, _item=None) -> None:
        if not _server_ready():
            state = "O servidor encerrou durante a inicialização." if server_failed.is_set() else "O servidor não abriu a porta dentro do tempo esperado."
            details = _tail_log()
            _message(
                f"{state}\n\nPorta: {PORT}\nLog: {LOG_FILE}\n\nÚltimas informações do log:\n{details}",
                flags=0x10,
            )
            return
        webbrowser.open(local_control_url())

    def show_qr(_icon=None, _item=None) -> None:
        if not _server_ready():
            _message(
                f"O servidor ainda não está pronto.\n\nÚltimas informações do log:\n{_tail_log(1800)}",
                flags=0x30,
            )
            return
        path = qr_path()
        os.startfile(path) if os.name == "nt" else webbrowser.open(path.as_uri())

    def copy_pairing(_icon=None, _item=None) -> None:
        urls = access_urls()
        pyperclip.copy("\n".join([*urls, f"PIN {PAIR_PIN}"]))

    def open_shared(_icon=None, _item=None) -> None:
        os.startfile(SHARED_DIR) if os.name == "nt" else webbrowser.open(SHARED_DIR.as_uri())

    def stop(icon: pystray.Icon, _item=None) -> None:
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Abrir controle", open_control, default=True),
        pystray.MenuItem("Mostrar QR Code", show_qr),
        pystray.MenuItem("Copiar endereços e PIN", copy_pairing),
        pystray.MenuItem("Liberar no Firewall do Windows", request_firewall_rule),
        pystray.MenuItem("Abrir log de diagnóstico", open_log),
        pystray.MenuItem("Abrir pasta compartilhada", open_shared),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sair", stop),
    )
    icon = pystray.Icon("AgateRemote", icon_image(), f"{APP_NAME} {APP_VERSION} • PIN {PAIR_PIN}", menu)
    icon.run()
