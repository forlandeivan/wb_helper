from __future__ import annotations

from html import escape

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from wb_helper.constants import NO_ARTICLES_MESSAGE
from wb_helper.domain import ArticleCard, CachedResultBundle
from wb_helper.services.presentation import ButtonBranding, build_article_cards


MARKETPLACE_LABELS = {
    "wb": "WB",
    "ozon": "Ozon",
}

MODE_LABELS = {
    "exact": "точное совпадение",
    "search": "поиск",
    "ambiguous": "поиск",
    "not_found": "не найдено",
}


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
        return NO_ARTICLES_MESSAGE

    return (
        f"<b>Найдено {len(cards)} {_pluralize_articles(len(cards))}</b>\n"
        "Выбери нужный товар кнопками ниже."
    )


def build_result_details(bundle: CachedResultBundle) -> str:
    cards = build_article_cards(bundle)
    if not cards:
        return NO_ARTICLES_MESSAGE

    lines = [f"<b>Найдено {len(cards)} {_pluralize_articles(len(cards))}</b>", ""]
    for card in cards:
        lines.extend(_render_card_lines(card))
        lines.append("")
    if lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


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


def _render_card_lines(card: ArticleCard) -> list[str]:
    return [
        f"<b>{card.appearance_index}. {escape(card.description)}</b>",
        f"<code>{escape(card.article)}</code>",
        f"<i>{escape(_marketplace_line(card))}</i>",
    ]


def _marketplace_line(card: ArticleCard) -> str:
    if card.marketplace_state == "unknown":
        return "WB / Ozon"
    label = MARKETPLACE_LABELS.get(card.marketplace_state, card.marketplace_state.upper())
    if card.mode == "exact":
        return f"{label} · карточка найдена"
    return label


def _resolve_button_emoji_id(marketplace: str, branding: ButtonBranding) -> str | None:
    if marketplace == "wb":
        return branding.wb_custom_emoji_id
    if marketplace == "ozon":
        return branding.ozon_custom_emoji_id
    return None
