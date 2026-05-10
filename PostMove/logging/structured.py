from __future__ import annotations

import logging
import sys

import structlog

from PostMove.settings.models import LoggingSettings


def configure_logging(settings: LoggingSettings) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    processors: list[object] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if settings.json
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    return structlog.get_logger(name)
