from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher

from wb_helper.bot.router import BotRuntime, build_router
from wb_helper.config import Settings
from wb_helper.logging import configure_logging
from wb_helper.queue import create_queue, create_redis
from wb_helper.services.presentation import ButtonBranding
from wb_helper.storage.db import create_db_engine, create_session_factory
from wb_helper.storage.repository import RequestRepository


async def _run() -> None:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    engine = create_db_engine(settings.postgres_dsn)
    session_factory = create_session_factory(engine)
    repository = RequestRepository(session_factory)
    if settings.auto_create_schema:
        repository.create_schema(engine)
    queue = create_queue(settings, create_redis(settings))

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(
        build_router(
            BotRuntime(
                repository=repository,
                queue=queue,
                cache_ttl_days=settings.cache_ttl_days,
                job_timeout_seconds=settings.job_timeout_seconds,
                button_branding=ButtonBranding(
                    wb_custom_emoji_id=settings.wb_button_custom_emoji_id,
                    ozon_custom_emoji_id=settings.ozon_button_custom_emoji_id,
                ),
            )
        )
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
