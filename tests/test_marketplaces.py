from __future__ import annotations

import pytest

from wb_helper.domain import ArticleCandidate
from wb_helper.marketplaces.ozon import OzonAdapter
from wb_helper.marketplaces.wb import WildberriesAdapter


class ResponseStub:
    def __init__(self, status_code: int, url: str, text: str = "") -> None:
        self.status_code = status_code
        self.url = url
        self.text = text


class ClientStub:
    def __init__(self, response: ResponseStub) -> None:
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url: str) -> ResponseStub:
        return self._response


def test_wb_exact_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    response = ResponseStub(
        status_code=200,
        url="https://www.wildberries.ru/catalog/12345678/detail.aspx",
        text="<title>Good item</title>",
    )
    monkeypatch.setattr("wb_helper.marketplaces.wb.httpx.Client", lambda **kwargs: ClientStub(response))

    adapter = WildberriesAdapter(timeout_seconds=8, user_agent="Mozilla/5.0")
    result = adapter.resolve(
        ArticleCandidate(
            raw_value="12345678",
            normalized_value="12345678",
            marketplace_hint="wb",
            confidence="high",
            span_start=0,
            span_end=11,
        )
    )

    assert result.mode == "exact"
    assert result.final_url.endswith("/12345678/detail.aspx")


def test_wb_anti_bot_falls_back_to_search(monkeypatch: pytest.MonkeyPatch) -> None:
    response = ResponseStub(status_code=498, url="https://www.wildberries.ru/catalog/12345678/detail.aspx")
    monkeypatch.setattr("wb_helper.marketplaces.wb.httpx.Client", lambda **kwargs: ClientStub(response))

    adapter = WildberriesAdapter(timeout_seconds=8, user_agent="Mozilla/5.0")
    result = adapter.resolve(
        ArticleCandidate(
            raw_value="12345678",
            normalized_value="12345678",
            marketplace_hint="wb",
            confidence="high",
            span_start=0,
            span_end=11,
        )
    )

    assert result.mode == "search"
    assert "search=12345678" in result.final_url


def test_ozon_returns_search_link() -> None:
    adapter = OzonAdapter()
    result = adapter.resolve(
        ArticleCandidate(
            raw_value="99887766",
            normalized_value="99887766",
            marketplace_hint="ozon",
            confidence="high",
            span_start=0,
            span_end=12,
        )
    )

    assert result.mode == "search"
    assert result.final_url == "https://www.ozon.ru/search/?text=99887766"


def test_wb_alphanumeric_article_uses_search_only() -> None:
    adapter = WildberriesAdapter(timeout_seconds=8, user_agent="Mozilla/5.0")
    result = adapter.resolve(
        ArticleCandidate(
            raw_value="WW285677",
            normalized_value="WW285677",
            marketplace_hint="wb",
            confidence="high",
            span_start=0,
            span_end=8,
        )
    )

    assert result.mode == "search"
    assert result.final_url == "https://www.wildberries.ru/catalog/0/search.aspx?search=WW285677"
    assert result.diagnostics["reason"] == "alphanumeric_search_only"
