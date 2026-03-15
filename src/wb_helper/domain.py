from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


MarketplaceHint = Literal["wb", "ozon", "generic"]
CandidateConfidence = Literal["high", "medium"]
ResolutionMode = Literal["exact", "search", "not_found", "ambiguous"]
ResolutionConfidence = Literal["high", "medium", "low"]
MarketplaceState = Literal["wb", "ozon", "unknown"]


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    source_url: str
    source_id: str
    caption_raw: str
    extractor: str
    extractor_version: str | None
    extracted_at: datetime


@dataclass(frozen=True, slots=True)
class ArticleCandidate:
    raw_value: str
    normalized_value: str
    marketplace_hint: MarketplaceHint
    confidence: CandidateConfidence
    span_start: int
    span_end: int


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    marketplace: Literal["wb", "ozon"]
    article: str
    mode: ResolutionMode
    final_url: str
    title: str | None
    confidence: ResolutionConfidence
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ArticleCardButton:
    marketplace: Literal["wb", "ozon"]
    label: str
    url: str


@dataclass(frozen=True, slots=True)
class ArticleCard:
    article: str
    description: str
    marketplace_state: MarketplaceState
    buttons: list[ArticleCardButton]
    appearance_index: int
    mode: ResolutionMode


@dataclass(frozen=True, slots=True)
class CachedResultBundle:
    source_id: str
    extraction: ExtractionResult | None
    candidates: list[ArticleCandidate]
    resolutions: list[ResolutionResult]
