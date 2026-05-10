from __future__ import annotations

from dataclasses import dataclass

from PostMove.database.repositories import ChannelRepository, LogRepository, RuntimeRepository, SettingsRepository
from PostMove.logging.live_stream import LiveLogStream
from PostMove.parsers.engine import ParserEngine
from PostMove.queue.manager import JobQueue
from PostMove.security.audit import AuditService
from PostMove.transfer.service import TransferService


@dataclass(slots=True)
class BotContext:
    channels_repo: ChannelRepository
    transfer_service: TransferService
    parser_engine: ParserEngine
    queue: JobQueue
    runtime_repo: RuntimeRepository
    logs_repo: LogRepository
    settings_repo: SettingsRepository
    audit_service: AuditService
    live_logs: LiveLogStream
