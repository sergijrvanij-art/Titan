from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CoreSettings(BaseModel):
    parser_workers: int = 2
    queue_workers: int = 4
    config_reload_interval: int = 15
    graceful_shutdown_timeout: int = 20


class TelegramSettings(BaseModel):
    api_id: int
    api_hash: str
    session_name: str = "postmove.session"
    admin_bot_token: str
    request_timeout: int = 30
    flood_sleep_threshold: int = 120


class DatabaseSettings(BaseModel):
    path: str = "postmove.db"


class SecuritySettings(BaseModel):
    admin_ids: list[int] = Field(default_factory=list)
    allow_forwarding_to_unlisted: bool = False


class QueueSettings(BaseModel):
    max_size: int = 10_000
    default_retries: int = 5
    worker_concurrency: int = 4
    base_backoff_seconds: float = 2
    max_backoff_seconds: float = 60
    rate_limit_per_second: float = 6.0


class ButtonConfig(BaseModel):
    text: str
    url: str


class ProcessingSettings(BaseModel):
    source_markers: list[str] = Field(default_factory=list)
    replacers: dict[str, str] = Field(default_factory=dict)
    deny_words: list[str] = Field(default_factory=list)
    auto_bold_title: bool = True
    default_buttons: list[ButtonConfig] = Field(default_factory=list)


class MediaSettings(BaseModel):
    temp_dir: str = "./tmp_media"
    compress_photos: bool = True
    compress_videos: bool = False
    cleanup_temp: bool = True


class LoggingSettings(BaseModel):
    level: str = "INFO"
    json: bool = True
    live_buffer: int = 2000


class AISettings(BaseModel):
    enabled: bool = True
    moderation_threshold: float = 0.75
    fake_detection_threshold: float = 0.70


class AppSettings(BaseModel):
    core: CoreSettings
    telegram: TelegramSettings
    database: DatabaseSettings
    security: SecuritySettings
    queue: QueueSettings
    processing: ProcessingSettings
    media: MediaSettings
    logging: LoggingSettings
    ai: AISettings

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppSettings":
        return cls.model_validate(payload)
