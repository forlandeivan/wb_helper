from __future__ import annotations

from datetime import datetime, timezone

from wb_helper.domain import ArticleCandidate, ExtractionResult, ResolutionResult


def test_repository_returns_cached_result(repository) -> None:
    request_id = repository.create_request(
        source_platform="instagram",
        source_url="https://www.instagram.com/reel/ABC123/",
        source_id="ABC123",
        chat_id=1,
        user_id=2,
        incoming_message_id=3,
        status_message_id=4,
    )
    repository.mark_processing(request_id)
    repository.mark_completed(
        request_id,
        ExtractionResult(
            source_url="https://www.instagram.com/reel/ABC123/",
            source_id="ABC123",
            caption_raw="WB 12345678",
            extractor="instagram",
            extractor_version="1.0",
            extracted_at=datetime.now(timezone.utc),
        ),
        [
            ArticleCandidate(
                raw_value="12345678",
                normalized_value="12345678",
                marketplace_hint="wb",
                confidence="high",
                span_start=0,
                span_end=11,
            )
        ],
        [
            ResolutionResult(
                marketplace="wb",
                article="12345678",
                mode="exact",
                final_url="https://www.wildberries.ru/catalog/12345678/detail.aspx",
                title=None,
                confidence="high",
                diagnostics={},
            )
        ],
    )

    cached = repository.find_cached_result("instagram", "ABC123", 30)

    assert cached is not None
    assert cached.extraction is not None
    assert cached.extraction.caption_raw == "WB 12345678"
    assert cached.resolutions[0].marketplace == "wb"


def test_repository_skips_empty_cached_result(repository) -> None:
    request_id = repository.create_request(
        source_platform="instagram",
        source_url="https://www.instagram.com/reel/ABC123/",
        source_id="ABC123",
        chat_id=1,
        user_id=2,
        incoming_message_id=3,
        status_message_id=4,
    )
    repository.mark_processing(request_id)
    repository.mark_completed(
        request_id,
        ExtractionResult(
            source_url="https://www.instagram.com/reel/ABC123/",
            source_id="ABC123",
            caption_raw="Без артикулов",
            extractor="instagram",
            extractor_version="1.0",
            extracted_at=datetime.now(timezone.utc),
        ),
        [],
        [],
    )

    assert repository.find_cached_result("instagram", "ABC123", 30) is None
