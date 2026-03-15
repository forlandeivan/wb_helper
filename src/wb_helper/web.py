from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiohttp import web

from wb_helper.bot.router import BotRuntime, build_router
from wb_helper.config import Settings
from wb_helper.logging import configure_logging
from wb_helper.queue import create_queue, create_redis
from wb_helper.services.presentation import ButtonBranding
from wb_helper.storage.db import create_db_engine, create_session_factory, ping_database
from wb_helper.storage.repository import RequestRepository

logger = logging.getLogger(__name__)


async def handle_health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def handle_ready(request: web.Request) -> web.Response:
    settings: Settings = request.app["settings"]
    engine = request.app["db_engine"]
    redis = request.app["redis"]
    try:
        await asyncio.to_thread(ping_database, engine)
        await asyncio.to_thread(redis.ping)
    except Exception as exc:
        return web.json_response({"status": "degraded", "detail": str(exc)}, status=503)
    return web.json_response({"status": "ready", "queue": settings.redis_queue_name})


async def handle_webhook(request: web.Request) -> web.Response:
    settings: Settings = request.app["settings"]
    expected_secret = settings.webhook_secret
    if expected_secret:
        provided_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if provided_secret != expected_secret:
            return web.json_response({"status": "forbidden"}, status=403)

    payload = await request.json()
    bot: Bot = request.app["bot"]
    dispatcher: Dispatcher = request.app["dispatcher"]
    update = Update.model_validate(payload)
    await dispatcher.feed_update(bot, update)
    return web.json_response({"status": "ok"})


async def on_startup(app: web.Application) -> None:
    settings: Settings = app["settings"]
    bot: Bot = app["bot"]
    repository: RequestRepository = app["repository"]
    if settings.auto_create_schema:
        await asyncio.to_thread(repository.create_schema, app["db_engine"])
    if settings.webhook_url:
        await bot.set_webhook(settings.webhook_url, secret_token=settings.webhook_secret)
        logger.info("webhook_configured", extra={"webhook_url": settings.webhook_url})


async def on_cleanup(app: web.Application) -> None:
    bot: Bot = app["bot"]
    await bot.session.close()


def build_application(settings: Settings) -> web.Application:
    configure_logging(settings.log_level)
    engine = create_db_engine(settings.postgres_dsn)
    session_factory = create_session_factory(engine)
    repository = RequestRepository(session_factory)
    redis = create_redis(settings)
    queue = create_queue(settings, redis)

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

    app = web.Application()
    app["settings"] = settings
    app["bot"] = bot
    app["dispatcher"] = dispatcher
    app["db_engine"] = engine
    app["repository"] = repository
    app["redis"] = redis
    app.router.add_get("/healthz", handle_health)
    app.router.add_get("/readyz", handle_ready)
    app.router.add_post(settings.webhook_path, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


def main() -> None:
    settings = Settings.from_env()
    app = build_application(settings)
    web.run_app(app, host=settings.bind_host, port=settings.bind_port)


if __name__ == "__main__":
    main()
