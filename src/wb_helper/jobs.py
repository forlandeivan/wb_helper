from __future__ import annotations

import logging

from wb_helper.config import Settings
from wb_helper.constants import EXTRACTION_AUTH_REQUIRED_MESSAGE, EXTRACTION_FAILED_MESSAGE
from wb_helper.domain import CachedResultBundle
from wb_helper.extractors.reels import ReelExtractionError, YtDlpReelExtractor
from wb_helper.marketplaces.ozon import OzonAdapter
from wb_helper.marketplaces.wb import WildberriesAdapter
from wb_helper.parsers.articles import parse_article_candidates
from wb_helper.services.presentation import ButtonBranding
from wb_helper.services.resolution import ResolutionService
from wb_helper.storage.db import create_db_engine, create_session_factory
from wb_helper.storage.repository import RequestRepository
from wb_helper.telegram_client import notify_failure, notify_success

logger = logging.getLogger(__name__)


def process_reel_request(request_id: str) -> None:
    settings = Settings.from_env()
    engine = create_db_engine(settings.postgres_dsn)
    session_factory = create_session_factory(engine)
    repository = RequestRepository(session_factory)
    extractor = YtDlpReelExtractor(
        settings.ytdlp_bin,
        settings.extractor_timeout_seconds,
        cookies_file=settings.ytdlp_cookies_file,
        cookies_content=settings.ytdlp_cookies_content,
        instagram_sessionid=settings.instagram_sessionid,
    )
    resolver = ResolutionService(
        wb_adapter=WildberriesAdapter(settings.request_timeout_seconds, settings.telegram_user_agent),
        ozon_adapter=OzonAdapter(),
    )
    branding = ButtonBranding(
        wb_custom_emoji_id=settings.wb_button_custom_emoji_id,
        ozon_custom_emoji_id=settings.ozon_button_custom_emoji_id,
    )
    logger.info(
        "request_started",
        extra={
            "request_id": request_id,
            "instagram_auth_mode": extractor.auth_mode,
            "has_instagram_sessionid": bool(settings.instagram_sessionid),
            "has_ytdlp_cookies_content": bool(settings.ytdlp_cookies_content),
            "has_ytdlp_cookies_file": bool(settings.ytdlp_cookies_file),
        },
    )

    request = repository.mark_processing(request_id)

    try:
        extraction = extractor.extract(request.source_url, request.source_id)
        candidates = parse_article_candidates(extraction.caption_raw)
        resolutions = resolver.resolve_candidates(candidates)
        repository.mark_completed(request_id, extraction, candidates, resolutions)
        bundle = CachedResultBundle(
            source_id=extraction.source_id,
            extraction=extraction,
            candidates=candidates,
            resolutions=resolutions,
        )
        try:
            notify_success(settings.bot_token, request.chat_id, request.status_message_id, bundle, branding)
        except Exception:
            logger.exception("notify_success_failed", extra={"request_id": request_id})
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "source_id": extraction.source_id,
                "candidate_count": len(candidates),
                "resolution_count": len(resolutions),
            },
        )
    except ReelExtractionError as exc:
        repository.mark_failed(request_id, exc.code, str(exc))
        try:
            failure_text = EXTRACTION_AUTH_REQUIRED_MESSAGE if exc.code == "auth_required" else EXTRACTION_FAILED_MESSAGE
            notify_failure(settings.bot_token, request.chat_id, request.status_message_id, failure_text)
        except Exception:
            logger.exception("notify_failure_failed", extra={"request_id": request_id})
        logger.warning("request_failed", extra={"request_id": request_id, "error_code": exc.code})
    except Exception as exc:  # pragma: no cover
        repository.mark_failed(request_id, "unexpected", str(exc))
        try:
            notify_failure(settings.bot_token, request.chat_id, request.status_message_id, EXTRACTION_FAILED_MESSAGE)
        except Exception:
            logger.exception("notify_failure_failed", extra={"request_id": request_id})
        logger.exception("request_crashed", extra={"request_id": request_id})
