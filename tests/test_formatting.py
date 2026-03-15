from __future__ import annotations

from datetime import datetime, timezone

from wb_helper.domain import ArticleCandidate, CachedResultBundle, ExtractionResult, ResolutionResult
from wb_helper.services.formatting import build_result_details, build_result_keyboard, build_result_message


def test_build_result_message() -> None:
    bundle = CachedResultBundle(
        source_id="ABC123",
        extraction=ExtractionResult(
            source_url="https://www.instagram.com/reel/ABC123/",
            source_id="ABC123",
            caption_raw="• Футболка белая 12345678",
            extractor="Instagram",
            extractor_version="1.0",
            extracted_at=datetime.now(timezone.utc),
        ),
        candidates=[
            ArticleCandidate(
                raw_value="12345678",
                normalized_value="12345678",
                marketplace_hint="wb",
                confidence="high",
                span_start=17,
                span_end=25,
            )
        ],
        resolutions=[
            ResolutionResult(
                marketplace="wb",
                article="12345678",
                mode="exact",
                final_url="https://example.com",
                title="Item",
                confidence="high",
                diagnostics={},
            )
        ],
    )

    message = build_result_message(bundle)

    assert "Найдено 1 артикул" in message
    assert "кнопками ниже" in message

    details = build_result_details(bundle)

    assert details == "• Футболка белая <code>12345678</code>"


def test_build_result_keyboard() -> None:
    bundle = CachedResultBundle(
        source_id="ABC123",
        extraction=ExtractionResult(
            source_url="https://www.instagram.com/reel/ABC123/",
            source_id="ABC123",
            caption_raw="• Футболка белая 99887766",
            extractor="Instagram",
            extractor_version="1.0",
            extracted_at=datetime.now(timezone.utc),
        ),
        candidates=[
            ArticleCandidate(
                raw_value="99887766",
                normalized_value="99887766",
                marketplace_hint="ozon",
                confidence="high",
                span_start=17,
                span_end=25,
            )
        ],
        resolutions=[
            ResolutionResult(
                marketplace="ozon",
                article="99887766",
                mode="search",
                final_url="https://ozon.ru/search/?text=99887766",
                title=None,
                confidence="medium",
                diagnostics={},
            )
        ],
    )

    keyboard = build_result_keyboard(bundle)

    assert keyboard is not None
    assert keyboard.inline_keyboard[0][0].url == "https://ozon.ru/search/?text=99887766"
    assert keyboard.inline_keyboard[0][0].text.startswith("🔵 Ozon ·")
    assert len(keyboard.inline_keyboard) == 1


def test_build_result_details_wraps_alphanumeric_article_only() -> None:
    bundle = CachedResultBundle(
        source_id="ABC123",
        extraction=ExtractionResult(
            source_url="https://www.instagram.com/reel/ABC123/",
            source_id="ABC123",
            caption_raw="Черное платье Арсеника WW285677",
            extractor="Instagram",
            extractor_version="1.0",
            extracted_at=datetime.now(timezone.utc),
        ),
        candidates=[
            ArticleCandidate(
                raw_value="WW285677",
                normalized_value="WW285677",
                marketplace_hint="wb",
                confidence="high",
                span_start=23,
                span_end=31,
            )
        ],
        resolutions=[
            ResolutionResult(
                marketplace="wb",
                article="WW285677",
                mode="search",
                final_url="https://www.wildberries.ru/catalog/0/search.aspx?search=WW285677",
                title=None,
                confidence="medium",
                diagnostics={},
            )
        ],
    )

    details = build_result_details(bundle)

    assert details == "Черное платье Арсеника <code>WW285677</code>"


def test_build_result_details_returns_none_without_caption() -> None:
    bundle = CachedResultBundle(
        source_id="ABC123",
        extraction=None,
        candidates=[],
        resolutions=[],
    )

    assert build_result_details(bundle) is None


def test_build_result_message_mentions_caption_when_no_articles_found() -> None:
    bundle = CachedResultBundle(
        source_id="ABC123",
        extraction=ExtractionResult(
            source_url="https://www.instagram.com/reel/ABC123/",
            source_id="ABC123",
            caption_raw="Подборка джинс в синем цвете",
            extractor="Instagram",
            extractor_version="1.0",
            extracted_at=datetime.now(timezone.utc),
        ),
        candidates=[],
        resolutions=[],
    )

    message = build_result_message(bundle)

    assert "не найдено явных артикулов" in message
    assert "оригинальное описание автора" in message
