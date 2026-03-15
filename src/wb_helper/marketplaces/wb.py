from __future__ import annotations

import html
import logging
import re

import httpx

from wb_helper.domain import ArticleCandidate, ResolutionResult

logger = logging.getLogger(__name__)

TITLE_PATTERN = re.compile(r"<title>(?P<title>.*?)</title>", re.IGNORECASE | re.DOTALL)
BLOCKED_STATUSES = {403, 429, 498, 503}


class WildberriesAdapter:
    marketplace = "wb"

    def __init__(self, timeout_seconds: int, user_agent: str) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent

    def build_search_url(self, article: str) -> str:
        return f"https://www.wildberries.ru/catalog/0/search.aspx?search={article}"

    def build_exact_url(self, article: str) -> str:
        return f"https://www.wildberries.ru/catalog/{article}/detail.aspx"

    def resolve(self, candidate: ArticleCandidate) -> ResolutionResult:
        article = candidate.normalized_value
        if not article.isdigit():
            return ResolutionResult(
                marketplace=self.marketplace,
                article=article,
                mode="search",
                final_url=self.build_search_url(article),
                title=None,
                confidence="medium" if candidate.marketplace_hint == "wb" else "low",
                diagnostics={"reason": "alphanumeric_search_only"},
            )

        exact_url = self.build_exact_url(article)
        headers = {"User-Agent": self._user_agent}

        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=True,
                headers=headers,
            ) as client:
                response = client.get(exact_url)
        except httpx.HTTPError as exc:
            logger.warning("wb_exact_request_failed", extra={"article": article, "error": str(exc)})
            return ResolutionResult(
                marketplace=self.marketplace,
                article=article,
                mode="search",
                final_url=self.build_search_url(article),
                title=None,
                confidence="low" if candidate.marketplace_hint == "generic" else "medium",
                diagnostics={"reason": "network_error", "error": str(exc)},
            )

        if response.status_code in BLOCKED_STATUSES:
            return ResolutionResult(
                marketplace=self.marketplace,
                article=article,
                mode="search",
                final_url=self.build_search_url(article),
                title=None,
                confidence="low" if candidate.marketplace_hint == "generic" else "medium",
                diagnostics={"reason": "anti_bot", "status_code": response.status_code},
            )

        if response.status_code == 200 and f"/catalog/{article}/detail.aspx" in str(response.url):
            title_match = TITLE_PATTERN.search(response.text)
            title = None
            if title_match:
                title = html.unescape(title_match.group("title")).strip()
            return ResolutionResult(
                marketplace=self.marketplace,
                article=article,
                mode="exact",
                final_url=str(response.url),
                title=title,
                confidence="high" if candidate.marketplace_hint == "wb" else "medium",
                diagnostics={"status_code": response.status_code},
            )

        return ResolutionResult(
            marketplace=self.marketplace,
            article=article,
            mode="search",
            final_url=self.build_search_url(article),
            title=None,
            confidence="low" if candidate.marketplace_hint == "generic" else "medium",
            diagnostics={"reason": "exact_unverified", "status_code": response.status_code},
        )
