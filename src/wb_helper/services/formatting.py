from __future__ import annotations

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from wb_helper.constants import NO_ARTICLES_MESSAGE
from wb_helper.domain import CachedResultBundle
from wb_helper.services.presentation import ButtonBranding, build_article_cards


def _pluralize_articles(count: int) -> str:
    remainder_ten = count % 10
    remainder_hundred = count % 100
    if remainder_ten == 1 and remainder_hundred != 11:
        return "артикул"
    if remainder_ten in {2, 3, 4} and remainder_hundred not in {12, 13, 14}:
        return "артикула"
    return "артикулов"


def build_result_message(bundle: CachedResultBundle) -> str:
    cards = build_article_cards(bundle)
    if not cards:
        if build_result_details(bundle):
            return f"{NO_ARTICLES_MESSAGE}\nНиже отправлю оригинальное описание автора."
        return NO_ARTICLES_MESSAGE

    return (
        f"<b>Найдено {len(cards)} {_pluralize_articles(len(cards))}</b>\n"
        "Выбери нужный товар кнопками ниже."
    )


def build_result_details(bundle: CachedResultBundle) -> str | None:
    caption_raw = (bundle.extraction.caption_raw if bundle.extraction else "").strip()
    if not caption_raw:
        return None
    return _wrap_caption_articles(caption_raw, bundle)


def build_result_keyboard(bundle: CachedResultBundle, branding: ButtonBranding | None = None) -> InlineKeyboardMarkup | None:
    cards = build_article_cards(bundle)
    if not cards:
        return None
    branding = branding or ButtonBranding()
    rows = []
    for card in cards:
        row = []
        for button in card.buttons:
            row.append(
                InlineKeyboardButton(
                    text=button.label,
                    url=button.url,
                    icon_custom_emoji_id=_resolve_button_emoji_id(button.marketplace, branding),
                )
            )
        if row:
            rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _wrap_caption_articles(caption_raw: str, bundle: CachedResultBundle) -> str:
    if not bundle.candidates:
        return escape(caption_raw)

    parts: list[str] = []
    cursor = 0
    for candidate in sorted(bundle.candidates, key=lambda item: (item.span_start, item.span_end)):
        start = max(0, min(candidate.span_start, len(caption_raw)))
        end = max(start, min(candidate.span_end, len(caption_raw)))
        if start < cursor or start == end:
            continue
        parts.append(escape(caption_raw[cursor:start]))
        parts.append(f"<code>{escape(caption_raw[start:end])}</code>")
        cursor = end

    parts.append(escape(caption_raw[cursor:]))
    return "".join(parts)


def _resolve_button_emoji_id(marketplace: str, branding: ButtonBranding) -> str | None:
    if marketplace == "wb":
        return branding.wb_custom_emoji_id
    if marketplace == "ozon":
        return branding.ozon_custom_emoji_id
    return None
