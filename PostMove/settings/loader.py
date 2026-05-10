from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from PostMove.settings.models import AppSettings


def _deep_set(target: dict, path: list[str], value: object) -> None:
    current = target
    for key in path[:-1]:
        current = current.setdefault(key, {})
    current[path[-1]] = value


def _parse_value(raw: str) -> object:
    lowered = raw.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if "," in raw:
        chunks = [chunk.strip() for chunk in raw.split(",") if chunk.strip()]
        if chunks and all(chunk.lstrip("-").isdigit() for chunk in chunks):
            return [int(chunk) for chunk in chunks]
        return chunks
    if raw.lstrip("-").isdigit():
        return int(raw)
    try:
        return float(raw)
    except ValueError:
        return raw


def load_settings(config_path: Path) -> AppSettings:
    load_dotenv(override=False)
    payload = json.loads(config_path.read_text(encoding="utf-8"))

    prefix = "PM_"
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        path = env_key[len(prefix):].lower().split("__")
        _deep_set(payload, path, _parse_value(env_value))

    return AppSettings.from_dict(payload)
