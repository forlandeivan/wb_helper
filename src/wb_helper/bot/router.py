from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from rq import Queue

from wb_helper.constants import (
    GROUP_CHAT_MESSAGE,
    HELP_MESSAGE,
    INVALID_URL_MESSAGE,
    MULTIPLE_URLS_MESSAGE,
    PROCESSING_MESSAGE,
    QUEUE_FAILED_MESSAGE,
    START_MESSAGE,
)
from wb_helper.domain import CachedResultBundle
from wb_helper.queue import enqueue_request
from wb_helper.services.formatting import build_result_details, build_result_keyboard, build_result_message
from wb_helper.services.presentation import ButtonBranding
from wb_helper.storage.repository import RequestRepository
from wb_helper.url_utils import InvalidReelUrlError, extract_urls, normalize_reel_url

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BotRuntime:
    repository: RequestRepository
    queue: Queue
    cache_ttl_days: int
    job_timeout_seconds: int
    button_branding: ButtonBranding


def build_router(runtime: BotRuntime) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def handle_start(message: Message) -> None:
        await message.answer(START_MESSAGE)

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        await message.answer(HELP_MESSAGE)

    @router.message(F.text)
    async def handle_text(message: Message) -> None:
        if message.chat.type != "private":
            await message.answer(GROUP_CHAT_MESSAGE)
            return

        urls = extract_urls(message.text or "")
        if not urls:
            await message.answer(INVALID_URL_MESSAGE)
            return
        if len(urls) != 1:
            await message.answer(MULTIPLE_URLS_MESSAGE)
            return

        try:
            normalized_url, source_id = normalize_reel_url(urls[0])
        except InvalidReelUrlError:
            await message.answer(INVALID_URL_MESSAGE)
            return

        cached_bundle = await asyncio.to_thread(
            runtime.repository.find_cached_result,
            "instagram",
            source_id,
            runtime.cache_ttl_days,
        )
        if cached_bundle is not None:
            await _send_cached_result(message, cached_bundle, runtime.button_branding)
            return

        status_message = await message.answer(PROCESSING_MESSAGE)
        request_id: str | None = None

        try:
            request_id = await asyncio.to_thread(
                runtime.repository.create_request,
                source_platform="instagram",
                source_url=normalized_url,
                source_id=source_id,
                chat_id=message.chat.id,
                user_id=message.from_user.id if message.from_user else None,
                incoming_message_id=message.message_id,
                status_message_id=status_message.message_id,
            )
            await asyncio.to_thread(
                enqueue_request,
                runtime.queue,
                request_id,
                runtime.job_timeout_seconds,
            )
        except Exception:
            logger.exception("queue_enqueue_failed", extra={"source_id": source_id})
            if request_id is not None:
                await asyncio.to_thread(
                    runtime.repository.mark_failed,
                    request_id,
                    "queue_error",
                    "Failed to enqueue request",
                )
            await status_message.edit_text(QUEUE_FAILED_MESSAGE)

    return router


async def _send_cached_result(
    message: Message,
    bundle: CachedResultBundle,
    branding: ButtonBranding,
) -> None:
    await message.answer(
        build_result_message(bundle),
        parse_mode="HTML",
        reply_markup=build_result_keyboard(bundle, branding),
    )
    details_text = build_result_details(bundle)
    if details_text and details_text != build_result_message(bundle):
        await message.answer(
            details_text,
            parse_mode="HTML",
        )
