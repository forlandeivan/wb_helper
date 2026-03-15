from __future__ import annotations

from wb_helper.domain import ArticleCandidate, ResolutionResult
from wb_helper.services.resolution import ResolutionService


class WbAdapterStub:
    def __init__(self, result: ResolutionResult) -> None:
        self._result = result

    def resolve(self, candidate: ArticleCandidate) -> ResolutionResult:
        return self._result


class OzonAdapterStub:
    def resolve(self, candidate: ArticleCandidate) -> ResolutionResult:
        return ResolutionResult(
            marketplace="ozon",
            article=candidate.normalized_value,
            mode="search",
            final_url=f"https://www.ozon.ru/search/?text={candidate.normalized_value}",
            title=None,
            confidence="low",
            diagnostics={},
        )


def test_generic_candidate_returns_only_wb_when_exact() -> None:
    service = ResolutionService(
        wb_adapter=WbAdapterStub(
            ResolutionResult(
                marketplace="wb",
                article="12345678",
                mode="exact",
                final_url="https://www.wildberries.ru/catalog/12345678/detail.aspx",
                title=None,
                confidence="medium",
                diagnostics={},
            )
        ),
        ozon_adapter=OzonAdapterStub(),
    )

    results = service.resolve_candidates(
        [
            ArticleCandidate(
                raw_value="12345678",
                normalized_value="12345678",
                marketplace_hint="generic",
                confidence="medium",
                span_start=0,
                span_end=13,
            )
        ]
    )

    assert len(results) == 1
    assert results[0].marketplace == "wb"
