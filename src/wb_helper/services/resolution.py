from __future__ import annotations

from wb_helper.domain import ArticleCandidate, ResolutionResult
from wb_helper.marketplaces.ozon import OzonAdapter
from wb_helper.marketplaces.wb import WildberriesAdapter


class ResolutionService:
    def __init__(self, wb_adapter: WildberriesAdapter, ozon_adapter: OzonAdapter) -> None:
        self._wb = wb_adapter
        self._ozon = ozon_adapter

    def resolve_candidates(self, candidates: list[ArticleCandidate]) -> list[ResolutionResult]:
        results: list[ResolutionResult] = []
        for candidate in candidates:
            if candidate.marketplace_hint == "wb":
                results.append(self._wb.resolve(candidate))
                continue
            if candidate.marketplace_hint == "ozon":
                results.append(self._ozon.resolve(candidate))
                continue

            wb_result = self._wb.resolve(candidate)
            if wb_result.mode == "exact":
                results.append(wb_result)
                continue

            results.append(wb_result)
            results.append(self._ozon.resolve(candidate))

        deduped: list[ResolutionResult] = []
        seen: set[tuple[str, str, str]] = set()
        for result in results:
            cache_key = (result.marketplace, result.article, result.final_url)
            if cache_key in seen:
                continue
            seen.add(cache_key)
            deduped.append(result)
        return deduped
