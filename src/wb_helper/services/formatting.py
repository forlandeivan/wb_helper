from __future__ import annotations

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from wb_helper.constants import NO_ARTICLES_MESSAGE
from wb_helper.domain import CachedResultBundle
from wb_helper.services.presentation import ButtonBranding, build_article_cards


SHOW_OZON_CALLBACK_PREFIX = "show_ozon:"


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

    lines = [
        f"<b>Найдено {len(cards)} {_pluralize_articles(len(cards))}</b>",
        "Выбери нужный товар кнопками ниже.",
    ]
    if _has_unknown_marketplace_cards(cards):
        lines.append("По умолчанию показал WB. Если нужен Ozon, нажми кнопку ниже.")
    return "\n".join(lines)


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
        primary_buttons = _pick_primary_buttons(card)
        if primary_buttons:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=button.label,
                        url=button.url,
                        icon_custom_emoji_id=_resolve_button_emoji_id(button.marketplace, branding),
                    )
                    for button in primary_buttons
                ]
            )
    if _has_unknown_marketplace_cards(cards):
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔵 Показать Ozon",
                    callback_data=f"{SHOW_OZON_CALLBACK_PREFIX}{bundle.source_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_marketplace_override_message(marketplace: str) -> str:
    if marketplace == "ozon":
        return "<b>Вариант для Ozon</b>\nОткрой нужный товар кнопками ниже."
    return "<b>Альтернативный вариант</b>\nОткрой нужный товар кнопками ниже."


def build_marketplace_override_keyboard(
    bundle: CachedResultBundle,
    marketplace: str,
    branding: ButtonBranding | None = None,
) -> InlineKeyboardMarkup | None:
    cards = build_article_cards(bundle)
    branding = branding or ButtonBranding()
    rows = []
    for card in cards:
        if card.marketplace_state != "unknown":
            continue
        for button in card.buttons:
            if button.marketplace != marketplace:
                continue
            rows.append(
                [
                    InlineKeyboardButton(
                        text=button.label,
                        url=button.url,
                        icon_custom_emoji_id=_resolve_button_emoji_id(button.marketplace, branding),
                    )
                ]
            )
            break
    if not rows:
        return None
    return InlineKeyboardMarkup(inline_keyboard=rows)


def parse_marketplace_override_callback(data: str | None) -> tuple[str, str] | None:
    if not data:
        return None
    if data.startswith(SHOW_OZON_CALLBACK_PREFIX):
        source_id = data.removeprefix(SHOW_OZON_CALLBACK_PREFIX).strip()
        if source_id:
            return ("ozon", source_id)
    return None


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


def _pick_primary_buttons(card) -> list:
    if card.marketplace_state != "unknown":
        return list(card.buttons)
    wb_button = next((button for button in card.buttons if button.marketplace == "wb"), None)
    if wb_button is not None:
        return [wb_button]
    return list(card.buttons[:1])


def _has_unknown_marketplace_cards(cards) -> bool:
    return any(card.marketplace_state == "unknown" for card in cards)


def _resolve_button_emoji_id(marketplace: str, branding: ButtonBranding) -> str | None:
    if marketplace == "wb":
        return branding.wb_custom_emoji_id
    if marketplace == "ozon":
        return branding.ozon_custom_emoji_id
    return None
