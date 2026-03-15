from __future__ import annotations

from wb_helper.domain import ArticleCandidate, ResolutionResult


class OzonAdapter:
    marketplace = "ozon"

    def build_search_url(self, article: str) -> str:
        return f"https://www.ozon.ru/search/?text={article}"

    def resolve(self, candidate: ArticleCandidate) -> ResolutionResult:
        return ResolutionResult(
            marketplace=self.marketplace,
            article=candidate.normalized_value,
            mode="search",
            final_url=self.build_search_url(candidate.normalized_value),
            title=None,
            confidence="medium" if candidate.marketplace_hint == "ozon" else "low",
            diagnostics={"reason": "search_only_mvp"},
        )
