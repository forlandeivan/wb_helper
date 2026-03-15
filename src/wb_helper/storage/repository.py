from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from wb_helper.domain import ArticleCandidate, CachedResultBundle, ExtractionResult, ResolutionResult
from wb_helper.storage.models import Base, CandidateRecord, ExtractionRecord, RequestRecord, ResolutionRecord


class RequestRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    @contextmanager
    def _session(self) -> Session:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_schema(self, engine) -> None:
        Base.metadata.create_all(engine)

    def create_request(
        self,
        *,
        source_platform: str,
        source_url: str,
        source_id: str,
        chat_id: int,
        user_id: int | None,
        incoming_message_id: int,
        status_message_id: int,
    ) -> str:
        with self._session() as session:
            request = RequestRecord(
                source_platform=source_platform,
                source_url=source_url,
                source_id=source_id,
                chat_id=chat_id,
                user_id=user_id,
                incoming_message_id=incoming_message_id,
                status_message_id=status_message_id,
                status="queued",
            )
            session.add(request)
            session.flush()
            return request.id

    def mark_processing(self, request_id: str) -> RequestRecord:
        with self._session() as session:
            request = session.get(RequestRecord, request_id)
            if request is None:
                raise KeyError(f"request {request_id} not found")
            request.status = "processing"
            request.error_code = None
            request.error_message = None
            session.add(request)
            session.flush()
            session.refresh(request)
            return request

    def mark_failed(self, request_id: str, error_code: str, error_message: str) -> RequestRecord:
        with self._session() as session:
            request = session.get(RequestRecord, request_id)
            if request is None:
                raise KeyError(f"request {request_id} not found")
            request.status = "failed"
            request.error_code = error_code
            request.error_message = error_message
            request.completed_at = datetime.now(timezone.utc)
            session.add(request)
            session.flush()
            session.refresh(request)
            return request

    def mark_completed(
        self,
        request_id: str,
        extraction: ExtractionResult,
        candidates: list[ArticleCandidate],
        resolutions: list[ResolutionResult],
    ) -> RequestRecord:
        with self._session() as session:
            request = session.get(RequestRecord, request_id)
            if request is None:
                raise KeyError(f"request {request_id} not found")

            request.status = "completed"
            request.completed_at = datetime.now(timezone.utc)
            request.error_code = None
            request.error_message = None
            request.source_url = extraction.source_url
            request.source_id = extraction.source_id
            session.add(request)
            session.flush()

            extraction_record = ExtractionRecord(
                request_id=request.id,
                source_url=extraction.source_url,
                source_id=extraction.source_id,
                caption_raw=extraction.caption_raw,
                extractor=extraction.extractor,
                extractor_version=extraction.extractor_version,
                extracted_at=extraction.extracted_at,
            )
            session.add(extraction_record)
            session.flush()

            candidate_map: dict[tuple[str, str, int, int], int] = {}
            for candidate in candidates:
                candidate_record = CandidateRecord(
                    request_id=request.id,
                    raw_value=candidate.raw_value,
                    normalized_value=candidate.normalized_value,
                    marketplace_hint=candidate.marketplace_hint,
                    confidence=candidate.confidence,
                    span_start=candidate.span_start,
                    span_end=candidate.span_end,
                )
                session.add(candidate_record)
                session.flush()
                candidate_map[
                    (
                        candidate.normalized_value,
                        candidate.marketplace_hint,
                        candidate.span_start,
                        candidate.span_end,
                    )
                ] = candidate_record.id

            for resolution in resolutions:
                linked_candidate_id = None
                for candidate in candidates:
                    if candidate.normalized_value == resolution.article:
                        linked_candidate_id = candidate_map.get(
                            (
                                candidate.normalized_value,
                                candidate.marketplace_hint,
                                candidate.span_start,
                                candidate.span_end,
                            )
                        )
                        if linked_candidate_id is not None:
                            break
                resolution_record = ResolutionRecord(
                    request_id=request.id,
                    candidate_id=linked_candidate_id,
                    marketplace=resolution.marketplace,
                    article=resolution.article,
                    mode=resolution.mode,
                    final_url=resolution.final_url,
                    title=resolution.title,
                    confidence=resolution.confidence,
                    diagnostics_json=json.dumps(resolution.diagnostics, ensure_ascii=True),
                )
                session.add(resolution_record)

            session.flush()
            session.refresh(request)
            return request

    def find_cached_result(self, source_platform: str, source_id: str, ttl_days: int) -> CachedResultBundle | None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=ttl_days)
        with self._session() as session:
            statement = (
                select(RequestRecord)
                .where(
                    RequestRecord.source_platform == source_platform,
                    RequestRecord.source_id == source_id,
                    RequestRecord.status == "completed",
                    RequestRecord.completed_at.is_not(None),
                    RequestRecord.completed_at >= cutoff,
                )
                .order_by(desc(RequestRecord.completed_at))
                .options(
                    selectinload(RequestRecord.extraction),
                    selectinload(RequestRecord.candidates),
                    selectinload(RequestRecord.resolutions),
                )
                .limit(1)
            )
            record = session.execute(statement).scalar_one_or_none()
            if record is None:
                return None
            bundle = self._to_bundle(record)
            if not bundle.resolutions:
                return None
            return bundle

    def get_request(self, request_id: str) -> RequestRecord | None:
        with self._session() as session:
            return session.get(RequestRecord, request_id)

    def _to_bundle(self, record: RequestRecord) -> CachedResultBundle:
        extraction = None
        if record.extraction is not None:
            extraction = ExtractionResult(
                source_url=record.extraction.source_url,
                source_id=record.extraction.source_id,
                caption_raw=record.extraction.caption_raw,
                extractor=record.extraction.extractor,
                extractor_version=record.extraction.extractor_version,
                extracted_at=record.extraction.extracted_at,
            )

        candidates = [
            ArticleCandidate(
                raw_value=item.raw_value,
                normalized_value=item.normalized_value,
                marketplace_hint=item.marketplace_hint,
                confidence=item.confidence,
                span_start=item.span_start,
                span_end=item.span_end,
            )
            for item in sorted(record.candidates, key=lambda candidate: (candidate.span_start, candidate.id))
        ]
        resolutions = [
            ResolutionResult(
                marketplace=item.marketplace,
                article=item.article,
                mode=item.mode,
                final_url=item.final_url,
                title=item.title,
                confidence=item.confidence,
                diagnostics=json.loads(item.diagnostics_json),
            )
            for item in sorted(record.resolutions, key=lambda resolution: resolution.id)
        ]
        return CachedResultBundle(
            source_id=record.source_id,
            extraction=extraction,
            candidates=candidates,
            resolutions=resolutions,
        )
