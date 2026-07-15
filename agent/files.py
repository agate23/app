from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import BinaryIO

from agent.config import MAX_UPLOAD_MB, SHARED_DIR
from agent.security import sanitize_filename


def _safe_path(filename: str) -> Path:
    name = sanitize_filename(filename)
    path = (SHARED_DIR / name).resolve()
    if SHARED_DIR.resolve() not in path.parents:
        raise ValueError("Caminho inválido")
    return path


def unique_path(filename: str) -> Path:
    base = _safe_path(filename)
    if not base.exists():
        return base
    stem, suffix = base.stem, base.suffix
    for number in range(1, 10_000):
        candidate = base.with_name(f"{stem} ({number}){suffix}")
        if not candidate.exists():
            return candidate
    raise ValueError("Não foi possível criar um nome único")


def save_stream(filename: str, source: BinaryIO) -> dict:
    destination = unique_path(filename)
    limit = MAX_UPLOAD_MB * 1024 * 1024
    digest = hashlib.sha256()
    size = 0
    try:
        with destination.open("wb") as output:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise ValueError(f"Arquivo maior que {MAX_UPLOAD_MB} MB")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return file_metadata(destination, digest.hexdigest())


def file_metadata(path: Path, sha256: str | None = None) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "sha256": sha256,
        "contentType": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
    }


def list_shared_files() -> list[dict]:
    files = [file_metadata(path) for path in SHARED_DIR.iterdir() if path.is_file()]
    return sorted(files, key=lambda item: item["modified"], reverse=True)


def resolve_download(filename: str) -> Path:
    path = _safe_path(filename)
    if not path.is_file():
        raise FileNotFoundError(filename)
    return path
