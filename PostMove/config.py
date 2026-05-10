from __future__ import annotations

from pathlib import Path

from PostMove.settings.loader import load_settings
from PostMove.settings.models import AppSettings


def get_settings(config_path: str | Path = "config.json") -> AppSettings:
    """Load merged settings from config.json and environment."""
    base = Path(__file__).resolve().parent
    return load_settings(base / config_path)
