from __future__ import annotations

import os
import subprocess
import webbrowser
from typing import Any

import pyautogui
import pyperclip

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.01

KEY_ALIASES = {
    "win": "winleft",
    "windows": "winleft",
    "control": "ctrl",
    "escape": "esc",
    "return": "enter",
    "pageup": "pgup",
    "pagedown": "pgdn",
}
MEDIA_KEYS = {
    "previous": "prevtrack",
    "play_pause": "playpause",
    "next": "nexttrack",
    "volume_down": "volumedown",
    "mute": "volumemute",
    "volume_up": "volumeup",
}


def normalize_key(value: str) -> str:
    key = KEY_ALIASES.get(value.lower().strip(), value.lower().strip())
    if key not in pyautogui.KEYBOARD_KEYS:
        raise ValueError(f"Tecla não permitida: {value}")
    return key


def execute(message: dict[str, Any]) -> dict[str, Any]:
    action = str(message.get("action", ""))
    if action == "mouse_move":
        dx = max(-250, min(float(message.get("dx", 0)), 250))
        dy = max(-250, min(float(message.get("dy", 0)), 250))
        pyautogui.moveRel(dx, dy, duration=0)
    elif action == "mouse_click":
        button = str(message.get("button", "left"))
        if button not in {"left", "right", "middle"}:
            raise ValueError("Botão de mouse inválido")
        pyautogui.click(button=button, clicks=max(1, min(int(message.get("clicks", 1)), 2)))
    elif action == "mouse_scroll":
        pyautogui.scroll(max(-20, min(int(message.get("amount", 0)), 20)))
    elif action == "mouse_down":
        pyautogui.mouseDown(button="left")
    elif action == "mouse_up":
        pyautogui.mouseUp(button="left")
    elif action == "key":
        pyautogui.press(normalize_key(str(message.get("key", ""))))
    elif action == "hotkey":
        keys = [normalize_key(str(key)) for key in message.get("keys", [])][:5]
        if not keys:
            raise ValueError("Atalho vazio")
        pyautogui.hotkey(*keys)
    elif action == "text":
        text = str(message.get("text", ""))[:5000]
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
    elif action == "clipboard_set":
        pyperclip.copy(str(message.get("text", ""))[:100_000])
    elif action == "clipboard_get":
        return {"ok": True, "clipboard": pyperclip.paste()[:100_000]}
    elif action == "media":
        key = MEDIA_KEYS.get(str(message.get("value", "")))
        if not key:
            raise ValueError("Comando de mídia inválido")
        pyautogui.press(key)
    elif action == "open_url":
        url = str(message.get("url", ""))[:2048]
        if not url.startswith(("https://", "http://")):
            raise ValueError("URL inválida")
        webbrowser.open(url)
    elif action == "lock":
        if os.name == "nt":
            subprocess.run(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    else:
        raise ValueError("Ação não reconhecida")
    return {"ok": True}
