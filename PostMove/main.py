from __future__ import annotations

import asyncio
import signal
from pathlib import Path

from PostMove.ai.modules import AIModuleService
from PostMove.bot.runner import AdminBotRunner
from PostMove.config import get_settings
from PostMove.core.supervisor import ModuleSupervisor
from PostMove.database.connection import Database
from PostMove.database.migrator import Migrator
from PostMove.database.repositories import (
    AdminActionRepository,
    ChannelRepository,
    CheckpointRepository,
    LogRepository,
    ParserStatsRepository,
    PostRepository,
    RuntimeRepository,
    SettingsRepository,
    TransferJobRepository,
)
from PostMove.logging.live_stream import LiveLogStream
from PostMove.logging.structured import configure_logging, get_logger
from PostMove.media.service import MediaService
from PostMove.parsers.engine import ParserEngine
from PostMove.processing.pipeline import ContentProcessor
from PostMove.queue.manager import JobQueue, QueueJob
from PostMove.security.admin_guard import AdminGuard
from PostMove.security.audit import AuditService
from PostMove.settings.reloader import ConfigReloader
from PostMove.telemetry.heartbeat import HeartbeatService
from PostMove.transfer.service import TransferService
from PostMove.userbot.client import UserbotClient

LOGGER = get_logger(__name__)


async def bootstrap() -> None:
    settings = get_settings(Path("config.json"))
    configure_logging(settings.logging)

    db = Database(settings.database.path)
    await db.connect()
    await Migrator(db, Path(__file__).resolve().parent / "database" / "migrations").run()

    channels_repo = ChannelRepository(db)
    transfer_repo = TransferJobRepository(db)
    posts_repo = PostRepository(db)
    logs_repo = LogRepository(db)
    runtime_repo = RuntimeRepository(db)
    checkpoint_repo = CheckpointRepository(db)
    parser_stats_repo = ParserStatsRepository(db)
    settings_repo = SettingsRepository(db)
    admin_actions_repo = AdminActionRepository(db)

    log_stream = LiveLogStream(max_items=settings.logging.live_buffer)
    job_queue = JobQueue(settings.queue, logs_repo, log_stream)
    media_service = MediaService(settings.media)
    content_processor = ContentProcessor(settings.processing)
    ai_service = AIModuleService()

    userbot = UserbotClient(settings.telegram)
    transfer_service = TransferService(
        settings=settings,
        userbot=userbot,
        queue=job_queue,
        channels_repo=channels_repo,
        transfer_repo=transfer_repo,
        posts_repo=posts_repo,
        checkpoint_repo=checkpoint_repo,
        content_processor=content_processor,
        media_service=media_service,
        logs_repo=logs_repo,
        ai_service=ai_service,
    )

    parser_engine = ParserEngine(
        settings=settings,
        queue=job_queue,
        parser_stats_repo=parser_stats_repo,
        checkpoint_repo=checkpoint_repo,
        logs_repo=logs_repo,
    )

    admin_guard = AdminGuard(set(settings.security.admin_ids))
    audit = AuditService(admin_actions_repo, logs_repo)

    bot_runner = AdminBotRunner(
        settings=settings,
        admin_guard=admin_guard,
        channels_repo=channels_repo,
        transfer_service=transfer_service,
        parser_engine=parser_engine,
        queue=job_queue,
        runtime_repo=runtime_repo,
        logs_repo=logs_repo,
        settings_repo=settings_repo,
        audit_service=audit,
        live_logs=log_stream,
    )

    heartbeat = HeartbeatService(runtime_repo, job_queue, parser_engine)
    reloader = ConfigReloader(Path(__file__).resolve().parent / "config.json", interval=settings.core.config_reload_interval)

    supervisor = ModuleSupervisor()
    shutdown_event = asyncio.Event()

    async def on_transfer_job(job: QueueJob) -> None:
        await transfer_service.handle_queue_job(job)

    job_queue.register_handler("transfer", on_transfer_job)

    async def reload_callback() -> None:
        new_settings = get_settings(Path("config.json"))
        transfer_service.reload_settings(new_settings)
        parser_engine.reload_settings(new_settings)
        LOGGER.info("config_reloaded")

    reloader.subscribe(reload_callback)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_event.set)

    await userbot.connect()
    await job_queue.start()
    await parser_engine.start(userbot)
    await transfer_service.enable_live_transfer()
    await heartbeat.start()
    await reloader.start()

    await supervisor.start_module("admin_bot", bot_runner.run)
    await supervisor.start_module("supervisor", supervisor.watch)

    LOGGER.info("postmove_started")
    await shutdown_event.wait()
    LOGGER.info("shutdown_signal_received")

    await reloader.stop()
    await heartbeat.stop()
    await parser_engine.stop()
    await job_queue.stop()
    await bot_runner.stop()
    await supervisor.stop_all()
    await userbot.disconnect()
    await db.close()


def main() -> None:
    asyncio.run(bootstrap())


if __name__ == "__main__":
    main()
