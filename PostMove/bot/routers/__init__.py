from __future__ import annotations

from aiogram import Router

from PostMove.bot.context import BotContext
from PostMove.bot.routers.channels import build_channels_router
from PostMove.bot.routers.logs import build_logs_router
from PostMove.bot.routers.parsers import build_parsers_router
from PostMove.bot.routers.runtime import build_runtime_router
from PostMove.bot.routers.settings import build_settings_router
from PostMove.bot.routers.start import build_start_router
from PostMove.bot.routers.transfer import build_transfer_router


def build_root_router(ctx: BotContext) -> Router:
    router = Router(name="admin-root")
    router.include_router(build_start_router())
    router.include_router(build_channels_router(ctx))
    router.include_router(build_parsers_router(ctx))
    router.include_router(build_transfer_router(ctx))
    router.include_router(build_settings_router(ctx))
    router.include_router(build_logs_router(ctx))
    router.include_router(build_runtime_router(ctx))
    return router
