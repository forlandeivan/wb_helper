from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.enums import ParseMode

from wb_helper.constants import EXTRACTION_FAILED_MESSAGE
from wb_helper.domain import CachedResultBundle
from wb_helper.services.formatting import build_result_details, build_result_keyboard, build_result_message
from wb_helper.services.presentation import ButtonBranding


async def _edit_message(
    *,
    bot_token: str,
    chat_id: int,
    message_id: int,
    text: str,
    bundle: CachedResultBundle,
    branding: ButtonBranding,
    send_details: bool,
) -> None:
    bot = Bot(token=bot_token)
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_result_keyboard(bundle, branding),
        )
        details_text = build_result_details(bundle)
        if send_details and details_text and details_text != text:
            await bot.send_message(
                chat_id=chat_id,
                text=details_text,
                parse_mode=ParseMode.HTML,
            )
    finally:
        await bot.session.close()


def edit_request_message(
    bot_token: str,
    chat_id: int,
    message_id: int,
    text: str,
    bundle: CachedResultBundle,
    branding: ButtonBranding,
    *,
    send_details: bool = True,
) -> None:
    asyncio.run(
        _edit_message(
            bot_token=bot_token,
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            bundle=bundle,
            branding=branding,
            send_details=send_details,
        )
    )


def notify_success(
    bot_token: str,
    chat_id: int,
    message_id: int,
    bundle: CachedResultBundle,
    branding: ButtonBranding,
) -> None:
    edit_request_message(
        bot_token=bot_token,
        chat_id=chat_id,
        message_id=message_id,
        text=build_result_message(bundle),
        bundle=bundle,
        branding=branding,
        send_details=True,
    )


def notify_failure(bot_token: str, chat_id: int, message_id: int, text: str = EXTRACTION_FAILED_MESSAGE) -> None:
    empty_bundle = CachedResultBundle(source_id="", extraction=None, candidates=[], resolutions=[])
    edit_request_message(
        bot_token=bot_token,
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        bundle=empty_bundle,
        branding=ButtonBranding(),
        send_details=False,
    )
