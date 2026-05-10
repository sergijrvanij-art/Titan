from __future__ import annotations

from aiogram import Bot, Dispatcher

from PostMove.bot.context import BotContext
from PostMove.bot.middleware import AdminOnlyMiddleware
from PostMove.bot.routers import build_root_router
from PostMove.database.repositories import ChannelRepository, LogRepository, RuntimeRepository, SettingsRepository
from PostMove.logging.live_stream import LiveLogStream
from PostMove.parsers.engine import ParserEngine
from PostMove.queue.manager import JobQueue
from PostMove.security.admin_guard import AdminGuard
from PostMove.security.audit import AuditService
from PostMove.settings.models import AppSettings
from PostMove.transfer.service import TransferService


class AdminBotRunner:
    def __init__(
        self,
        settings: AppSettings,
        admin_guard: AdminGuard,
        channels_repo: ChannelRepository,
        transfer_service: TransferService,
        parser_engine: ParserEngine,
        queue: JobQueue,
        runtime_repo: RuntimeRepository,
        logs_repo: LogRepository,
        settings_repo: SettingsRepository,
        audit_service: AuditService,
        live_logs: LiveLogStream,
    ) -> None:
        self._settings = settings
        self._bot = Bot(token=settings.telegram.admin_bot_token)
        self._dp = Dispatcher()
        self._dp.update.middleware(AdminOnlyMiddleware(admin_guard))
        context = BotContext(
            channels_repo=channels_repo,
            transfer_service=transfer_service,
            parser_engine=parser_engine,
            queue=queue,
            runtime_repo=runtime_repo,
            logs_repo=logs_repo,
            settings_repo=settings_repo,
            audit_service=audit_service,
            live_logs=live_logs,
        )
        self._dp.include_router(build_root_router(context))

    async def run(self) -> None:
        await self._dp.start_polling(self._bot)

    async def stop(self) -> None:
        await self._bot.session.close()
