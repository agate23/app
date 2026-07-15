from __future__ import annotations

from typing import Any

from agent.config import DEFAULT_PROFILES, USER_PROFILES, load_json, save_json

ALLOWED_TYPES = {"key", "hotkey", "media", "text", "open_url"}


def load_profiles() -> dict[str, Any]:
    if USER_PROFILES.exists():
        return load_json(USER_PROFILES, {"profiles": []})
    return load_json(DEFAULT_PROFILES, {"profiles": []})


def validate_profiles(payload: dict[str, Any]) -> dict[str, Any]:
    profiles = payload.get("profiles")
    if not isinstance(profiles, list) or len(profiles) > 20:
        raise ValueError("Lista de perfis inválida")
    output: list[dict[str, Any]] = []
    for profile in profiles:
        if not isinstance(profile, dict):
            raise ValueError("Perfil inválido")
        actions = profile.get("actions", [])
        if not isinstance(actions, list) or len(actions) > 30:
            raise ValueError("Ações inválidas")
        safe_actions = []
        for action in actions:
            if not isinstance(action, dict) or action.get("type") not in ALLOWED_TYPES:
                raise ValueError("Tipo de ação não permitido")
            safe_actions.append({
                "label": str(action.get("label", "Ação"))[:40],
                "type": action["type"],
                "value": action.get("value"),
            })
        output.append({
            "id": str(profile.get("id", "perfil"))[:40],
            "name": str(profile.get("name", "Perfil"))[:40],
            "icon": str(profile.get("icon", "tune"))[:40],
            "actions": safe_actions,
        })
    return {"profiles": output}


def save_profiles(payload: dict[str, Any]) -> dict[str, Any]:
    validated = validate_profiles(payload)
    save_json(USER_PROFILES, validated)
    return validated
