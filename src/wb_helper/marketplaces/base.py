from __future__ import annotations

from typing import Protocol

from wb_helper.domain import ArticleCandidate, ResolutionResult


class MarketplaceAdapter(Protocol):
    marketplace: str

    def resolve(self, candidate: ArticleCandidate) -> ResolutionResult:
        raise NotImplementedError

    def build_search_url(self, article: str) -> str:
        raise NotImplementedError
