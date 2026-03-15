from __future__ import annotations

import re

from wb_helper.domain import ArticleCandidate


MARKETPLACE_PATTERN = r"(?:wb|вб|wildberries|ozon|озон)"
GENERIC_LABEL_PATTERN = r"(?:арт(?:икул)?|article|sku)"
NUMBER_PATTERN = r"(?P<article>\d{6,14})"
BULLET_CHARS = r"\-\*\u2022•·▪"
LETTER_PATTERN = re.compile(r"[A-Za-zА-Яа-яЁё]", re.IGNORECASE)
SECTION_HEADER_PATTERN = re.compile(
    rf"(?:^|[^A-Za-zА-Яа-яЁё])(?:{GENERIC_LABEL_PATTERN})(?:ы|ов)?(?:[^A-Za-zА-Яа-яЁё]|$)",
    re.IGNORECASE,
)
BULLET_ONLY_NUMBER_PATTERN = re.compile(
    rf"^\s*[{BULLET_CHARS}]+\s*{NUMBER_PATTERN}\s*$",
    re.IGNORECASE,
)
ITEM_TRAILING_NUMBER_PATTERN = re.compile(
    rf"^\s*(?P<bullet>[{BULLET_CHARS}]+)?\s*(?P<label>.*?{LETTER_PATTERN.pattern}.*?)"
    rf"(?:\s+|[.:,;=-]\s*){NUMBER_PATTERN}\s*$",
    re.IGNORECASE,
)
PLAIN_NUMBER_PATTERN = re.compile(
    rf"^\s*{NUMBER_PATTERN}\s*$",
    re.IGNORECASE,
)
MARKETPLACE_CONTEXT_PATTERNS = {
    "wb": re.compile(r"(?:^|[^A-Za-zА-Яа-яЁё])(wb|вб|wildberries|вайлдберриз|вайлд|вбшк[аи]?)(?:[^A-Za-zА-Яа-яЁё]|$)", re.IGNORECASE),
    "ozon": re.compile(r"(?:^|[^A-Za-zА-Яа-яЁё])(ozon|озон)(?:[^A-Za-zА-Яа-яЁё]|$)", re.IGNORECASE),
}

PATTERNS = (
    re.compile(
        rf"(?P<marketplace>{MARKETPLACE_PATTERN})\s*(?:{GENERIC_LABEL_PATTERN})?\.?\s*[:#№-]?\s*{NUMBER_PATTERN}",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?P<label>{GENERIC_LABEL_PATTERN})\.?\s*[:#№-]?\s*{NUMBER_PATTERN}\s*(?:[-/,]\s*)?(?P<marketplace>{MARKETPLACE_PATTERN})?",
        re.IGNORECASE,
    ),
)


def normalize_marketplace_hint(raw_marketplace: str | None) -> str:
    if not raw_marketplace:
        return "generic"
    value = raw_marketplace.lower()
    if value in {"wb", "вб", "wildberries"}:
        return "wb"
    if value in {"ozon", "озон"}:
        return "ozon"
    return "generic"


def _build_candidate(match: re.Match[str], base_offset: int = 0) -> ArticleCandidate:
    article = match.group("article")
    marketplace_hint = normalize_marketplace_hint(match.groupdict().get("marketplace") or match.groupdict().get("label"))
    confidence = "high" if marketplace_hint in {"wb", "ozon"} else "medium"
    return ArticleCandidate(
        raw_value=article,
        normalized_value=article,
        marketplace_hint=marketplace_hint,
        confidence=confidence,
        span_start=base_offset + match.start("article"),
        span_end=base_offset + match.end("article"),
    )


def parse_article_candidates(text: str) -> list[ArticleCandidate]:
    if not text:
        return []

    seen: set[tuple[str, str]] = set()
    candidates: list[ArticleCandidate] = []
    document_marketplace_hint = _infer_document_marketplace_hint(text)

    for pattern in PATTERNS:
        for match in pattern.finditer(text):
            _append_candidate(candidates, seen, _apply_marketplace_hint(_build_candidate(match), document_marketplace_hint))

    _parse_contextual_candidates(text, candidates, seen, document_marketplace_hint)

    return sorted(candidates, key=lambda item: (item.span_start, item.normalized_value))


def _append_candidate(
    candidates: list[ArticleCandidate],
    seen: set[tuple[str, str]],
    candidate: ArticleCandidate,
) -> None:
    cache_key = (candidate.marketplace_hint, candidate.normalized_value)
    if cache_key in seen:
        return

    specific_marketplaces = {"wb", "ozon"}
    if candidate.marketplace_hint == "generic":
        if any(
            item.normalized_value == candidate.normalized_value and item.marketplace_hint in specific_marketplaces
            for item in candidates
        ):
            return
    else:
        generic_key = ("generic", candidate.normalized_value)
        if generic_key in seen:
            seen.remove(generic_key)
            candidates[:] = [
                item
                for item in candidates
                if not (item.marketplace_hint == "generic" and item.normalized_value == candidate.normalized_value)
            ]

    seen.add(cache_key)
    candidates.append(candidate)


def _parse_contextual_candidates(
    text: str,
    candidates: list[ArticleCandidate],
    seen: set[tuple[str, str]],
    document_marketplace_hint: str | None,
) -> None:
    caption_has_article_section = bool(SECTION_HEADER_PATTERN.search(text))
    if not caption_has_article_section and "•" not in text and "-" not in text and "*" not in text:
        return

    previous_non_empty_line = ""
    line_offset = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        stripped_line = line.strip()

        if stripped_line:
            previous_has_letters = bool(LETTER_PATTERN.search(previous_non_empty_line))
            line_marketplace_hint = _infer_document_marketplace_hint("\n".join([previous_non_empty_line, stripped_line]))

            bullet_only_match = BULLET_ONLY_NUMBER_PATTERN.match(line)
            if bullet_only_match and (caption_has_article_section or previous_has_letters):
                _append_candidate(
                    candidates,
                    seen,
                    _apply_marketplace_hint(
                        _build_candidate(bullet_only_match, base_offset=line_offset),
                        line_marketplace_hint or document_marketplace_hint,
                    ),
                )
            else:
                trailing_match = ITEM_TRAILING_NUMBER_PATTERN.match(line)
                if trailing_match and (
                    caption_has_article_section or trailing_match.group("bullet") or previous_has_letters
                ):
                    _append_candidate(
                        candidates,
                        seen,
                        _apply_marketplace_hint(
                            _build_candidate(trailing_match, base_offset=line_offset),
                            line_marketplace_hint or document_marketplace_hint,
                        ),
                    )
                else:
                    plain_number_match = PLAIN_NUMBER_PATTERN.match(line)
                    if plain_number_match and caption_has_article_section and previous_has_letters:
                        _append_candidate(
                            candidates,
                            seen,
                            _apply_marketplace_hint(
                                _build_candidate(plain_number_match, base_offset=line_offset),
                                line_marketplace_hint or document_marketplace_hint,
                            ),
                        )

            previous_non_empty_line = stripped_line

        line_offset += len(raw_line)


def _infer_document_marketplace_hint(text: str) -> str | None:
    present = [
        marketplace
        for marketplace, pattern in MARKETPLACE_CONTEXT_PATTERNS.items()
        if pattern.search(text)
    ]
    if len(present) == 1:
        return present[0]
    return None


def _apply_marketplace_hint(candidate: ArticleCandidate, marketplace_hint: str | None) -> ArticleCandidate:
    if candidate.marketplace_hint != "generic" or marketplace_hint is None:
        return candidate
    return ArticleCandidate(
        raw_value=candidate.raw_value,
        normalized_value=candidate.normalized_value,
        marketplace_hint=marketplace_hint,
        confidence=candidate.confidence,
        span_start=candidate.span_start,
        span_end=candidate.span_end,
    )
