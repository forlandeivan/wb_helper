from __future__ import annotations

from datetime import datetime, timezone

from wb_helper.domain import ArticleCandidate, CachedResultBundle, ExtractionResult, ResolutionResult
from wb_helper.services.presentation import build_article_cards


def _bundle(
    *,
    caption: str,
    candidates: list[ArticleCandidate],
    resolutions: list[ResolutionResult],
) -> CachedResultBundle:
    return CachedResultBundle(
        source_id="ABC123",
        extraction=ExtractionResult(
            source_url="https://www.instagram.com/reel/ABC123/",
            source_id="ABC123",
            caption_raw=caption,
            extractor="Instagram",
            extractor_version="1.0",
            extracted_at=datetime.now(timezone.utc),
        ),
        candidates=candidates,
        resolutions=resolutions,
    )


def test_build_article_cards_extracts_same_line_description() -> None:
    bundle = _bundle(
        caption="• Футболка белая 28515518",
        candidates=[
            ArticleCandidate(
                raw_value="28515518",
                normalized_value="28515518",
                marketplace_hint="wb",
                confidence="high",
                span_start=17,
                span_end=25,
            )
        ],
        resolutions=[
            ResolutionResult(
                marketplace="wb",
                article="28515518",
                mode="search",
                final_url="https://www.wildberries.ru/catalog/0/search.aspx?search=28515518",
                title=None,
                confidence="medium",
                diagnostics={},
            )
        ],
    )

    cards = build_article_cards(bundle)

    assert len(cards) == 1
    assert cards[0].description == "Футболка белая"
    assert cards[0].marketplace_state == "wb"


def test_build_article_cards_extracts_previous_line_description() -> None:
    caption = "Коричневый с лампасами ⤵️\n• 464532320"
    bundle = _bundle(
        caption=caption,
        candidates=[
            ArticleCandidate(
                raw_value="464532320",
                normalized_value="464532320",
                marketplace_hint="generic",
                confidence="medium",
                span_start=31,
                span_end=40,
            )
        ],
        resolutions=[
            ResolutionResult(
                marketplace="wb",
                article="464532320",
                mode="search",
                final_url="https://www.wildberries.ru/catalog/0/search.aspx?search=464532320",
                title=None,
                confidence="low",
                diagnostics={},
            ),
            ResolutionResult(
                marketplace="ozon",
                article="464532320",
                mode="search",
                final_url="https://www.ozon.ru/search/?text=464532320",
                title=None,
                confidence="low",
                diagnostics={},
            ),
        ],
    )

    cards = build_article_cards(bundle)

    assert len(cards) == 1
    assert cards[0].description == "Коричневый с лампасами"
    assert cards[0].marketplace_state == "unknown"
    assert [button.marketplace for button in cards[0].buttons] == ["wb", "ozon"]


def test_build_article_cards_ignores_metadata_lines() -> None:
    caption = "Артикулы ⤵️\nРост 186см Вес 83кг\n• 464532320"
    bundle = _bundle(
        caption=caption,
        candidates=[
            ArticleCandidate(
                raw_value="464532320",
                normalized_value="464532320",
                marketplace_hint="generic",
                confidence="medium",
                span_start=34,
                span_end=43,
            )
        ],
        resolutions=[
            ResolutionResult(
                marketplace="wb",
                article="464532320",
                mode="search",
                final_url="https://www.wildberries.ru/catalog/0/search.aspx?search=464532320",
                title="Брюки",
                confidence="low",
                diagnostics={},
            ),
            ResolutionResult(
                marketplace="ozon",
                article="464532320",
                mode="search",
                final_url="https://www.ozon.ru/search/?text=464532320",
                title=None,
                confidence="low",
                diagnostics={},
            ),
        ],
    )

    cards = build_article_cards(bundle)

    assert len(cards) == 1
    assert cards[0].description == "Брюки"


def test_build_article_cards_collapses_unique_exact_resolution() -> None:
    bundle = _bundle(
        caption="• 12345678",
        candidates=[
            ArticleCandidate(
                raw_value="12345678",
                normalized_value="12345678",
                marketplace_hint="generic",
                confidence="medium",
                span_start=2,
                span_end=10,
            )
        ],
        resolutions=[
            ResolutionResult(
                marketplace="wb",
                article="12345678",
                mode="exact",
                final_url="https://www.wildberries.ru/catalog/12345678/detail.aspx",
                title="Худи",
                confidence="high",
                diagnostics={},
            )
        ],
    )

    cards = build_article_cards(bundle)

    assert len(cards) == 1
    assert cards[0].marketplace_state == "wb"
    assert len(cards[0].buttons) == 1


def test_build_article_cards_cleans_numbered_hash_descriptions() -> None:
    caption = "WB\n1 джинсы #789076262"
    bundle = _bundle(
        caption=caption,
        candidates=[
            ArticleCandidate(
                raw_value="789076262",
                normalized_value="789076262",
                marketplace_hint="wb",
                confidence="high",
                span_start=13,
                span_end=22,
            )
        ],
        resolutions=[
            ResolutionResult(
                marketplace="wb",
                article="789076262",
                mode="search",
                final_url="https://www.wildberries.ru/catalog/0/search.aspx?search=789076262",
                title=None,
                confidence="medium",
                diagnostics={},
            )
        ],
    )

    cards = build_article_cards(bundle)

    assert len(cards) == 1
    assert cards[0].description == "джинсы"
    assert cards[0].buttons[0].label.startswith("WB · джинсы")
