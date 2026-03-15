from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re

from wb_helper.domain import ArticleCard, ArticleCardButton, ArticleCandidate, CachedResultBundle, ResolutionResult
from wb_helper.parsers.articles import GENERIC_LABEL_PATTERN, MARKETPLACE_PATTERN


BULLET_PREFIX_PATTERN = re.compile(r"^\s*[\-\*\u2022•·▪]+\s*")
ARROW_SUFFIX_PATTERN = re.compile(r"\s*[⤵️↘⬇️↓⇣↙➡️→]+[\s:：-]*$", re.IGNORECASE)
LEADING_MARKETPLACE_PATTERN = re.compile(rf"^\s*(?:{MARKETPLACE_PATTERN})\s*[\.:,;:：-]*\s*", re.IGNORECASE)
LEADING_GENERIC_LABEL_PATTERN = re.compile(
    rf"^\s*(?:{GENERIC_LABEL_PATTERN})(?:ы|ов)?\s*[\.:,;:：#№-]*\s*",
    re.IGNORECASE,
)
METADATA_LINE_PATTERNS = (
    re.compile(rf"^\s*(?:{GENERIC_LABEL_PATTERN})(?:ы|ов)?(?:\s|$)", re.IGNORECASE),
    re.compile(r"^\s*(?:рост|вес|размер|параметры|мой рост|мой вес)\b", re.IGNORECASE),
)
WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class ButtonBranding:
    wb_custom_emoji_id: str | None = None
    ozon_custom_emoji_id: str | None = None


@dataclass(frozen=True, slots=True)
class CaptionLine:
    raw_text: str
    stripped_text: str
    start: int
    end: int


def build_article_cards(bundle: CachedResultBundle) -> list[ArticleCard]:
    caption = bundle.extraction.caption_raw if bundle.extraction is not None else ""
    descriptions = _extract_descriptions(caption, bundle.candidates)
    resolutions_by_article: dict[str, list[ResolutionResult]] = defaultdict(list)
    for resolution in bundle.resolutions:
        resolutions_by_article[resolution.article].append(resolution)

    cards: list[ArticleCard] = []
    for appearance_index, candidate in enumerate(bundle.candidates, start=1):
        candidate_resolutions = _dedupe_resolutions(resolutions_by_article.get(candidate.normalized_value, []))
        if not candidate_resolutions:
            continue

        marketplace_state = _resolve_marketplace_state(candidate, candidate_resolutions)
        description = (
            descriptions.get(candidate.normalized_value)
            or _pick_resolution_title(candidate_resolutions)
            or "Товар без подписи"
        )
        buttons = _build_buttons(description, marketplace_state, candidate_resolutions)
        mode = _select_card_mode(candidate_resolutions, marketplace_state)
        cards.append(
            ArticleCard(
                article=candidate.normalized_value,
                description=description,
                marketplace_state=marketplace_state,
                buttons=buttons,
                appearance_index=appearance_index,
                mode=mode,
            )
        )

    return cards


def _extract_descriptions(caption: str, candidates: list[ArticleCandidate]) -> dict[str, str]:
    if not caption:
        return {}

    lines = _split_caption_lines(caption)
    descriptions: dict[str, str] = {}
    for candidate in candidates:
        current_line_index = _find_line_index(lines, candidate.span_start)
        if current_line_index is None:
            continue

        current_line = lines[current_line_index]
        same_line_prefix = current_line.raw_text[: max(0, candidate.span_start - current_line.start)]
        same_line_description = _normalize_description_text(same_line_prefix)
        if _is_good_description(same_line_description):
            descriptions[candidate.normalized_value] = same_line_description
            continue

        previous_line = _find_previous_meaningful_line(lines, current_line_index)
        if previous_line is None:
            continue
        previous_description = _normalize_description_text(previous_line.stripped_text)
        if _is_good_description(previous_description):
            descriptions[candidate.normalized_value] = previous_description

    return descriptions


def _split_caption_lines(caption: str) -> list[CaptionLine]:
    lines: list[CaptionLine] = []
    offset = 0
    for raw_line in caption.splitlines(keepends=True):
        line_without_break = raw_line.rstrip("\r\n")
        lines.append(
            CaptionLine(
                raw_text=line_without_break,
                stripped_text=line_without_break.strip(),
                start=offset,
                end=offset + len(line_without_break),
            )
        )
        offset += len(raw_line)
    if not lines and caption:
        lines.append(CaptionLine(raw_text=caption, stripped_text=caption.strip(), start=0, end=len(caption)))
    return lines


def _find_line_index(lines: list[CaptionLine], position: int) -> int | None:
    for index, line in enumerate(lines):
        if line.start <= position <= line.end:
            return index
    return None


def _find_previous_meaningful_line(lines: list[CaptionLine], start_index: int) -> CaptionLine | None:
    for index in range(start_index - 1, -1, -1):
        line = lines[index]
        if not line.stripped_text:
            continue
        normalized = _normalize_description_text(line.stripped_text)
        if _is_good_description(normalized):
            return line
    return None


def _normalize_description_text(text: str) -> str:
    if not text:
        return ""
    normalized = BULLET_PREFIX_PATTERN.sub("", text)
    normalized = LEADING_MARKETPLACE_PATTERN.sub("", normalized)
    normalized = LEADING_GENERIC_LABEL_PATTERN.sub("", normalized)
    normalized = ARROW_SUFFIX_PATTERN.sub("", normalized)
    normalized = normalized.strip(" .,:;|/\\-")
    normalized = WHITESPACE_PATTERN.sub(" ", normalized).strip()
    return normalized


def _is_good_description(text: str) -> bool:
    if not text:
        return False
    if not re.search(r"[A-Za-zА-Яа-яЁё]", text):
        return False
    if any(pattern.match(text) for pattern in METADATA_LINE_PATTERNS):
        return False
    if re.fullmatch(rf"(?:{MARKETPLACE_PATTERN})", text, re.IGNORECASE):
        return False
    return True


def _dedupe_resolutions(resolutions: list[ResolutionResult]) -> list[ResolutionResult]:
    deduped: list[ResolutionResult] = []
    seen: set[tuple[str, str]] = set()
    for resolution in sorted(resolutions, key=lambda item: (_resolution_rank(item), item.marketplace)):
        cache_key = (resolution.marketplace, resolution.final_url)
        if cache_key in seen:
            continue
        seen.add(cache_key)
        deduped.append(resolution)
    return deduped


def _resolve_marketplace_state(candidate: ArticleCandidate, resolutions: list[ResolutionResult]) -> str:
    if candidate.marketplace_hint in {"wb", "ozon"}:
        return candidate.marketplace_hint

    exact_marketplaces = {item.marketplace for item in resolutions if item.mode == "exact"}
    if len(exact_marketplaces) == 1:
        return next(iter(exact_marketplaces))

    marketplaces = {item.marketplace for item in resolutions}
    if len(marketplaces) == 1:
        return next(iter(marketplaces))

    return "unknown"


def _build_buttons(description: str, marketplace_state: str, resolutions: list[ResolutionResult]) -> list[ArticleCardButton]:
    if marketplace_state in {"wb", "ozon"}:
        resolution = _pick_best_resolution(resolutions, marketplace_state)
        if resolution is None:
            return []
        return [
            ArticleCardButton(
                marketplace=marketplace_state,
                label=_build_button_label(marketplace_state, description, resolution.article),
                url=resolution.final_url,
            )
        ]

    buttons: list[ArticleCardButton] = []
    for marketplace in ("wb", "ozon"):
        resolution = _pick_best_resolution(resolutions, marketplace)
        if resolution is None:
            continue
        buttons.append(
            ArticleCardButton(
                marketplace=marketplace,
                label=_build_button_label(marketplace, description, resolution.article),
                url=resolution.final_url,
            )
        )
    return buttons


def _pick_best_resolution(resolutions: list[ResolutionResult], marketplace: str) -> ResolutionResult | None:
    filtered = [item for item in resolutions if item.marketplace == marketplace]
    if not filtered:
        return None
    return sorted(filtered, key=_resolution_rank)[0]


def _resolution_rank(resolution: ResolutionResult) -> tuple[int, int]:
    mode_rank = {"exact": 0, "search": 1, "ambiguous": 2, "not_found": 3}
    confidence_rank = {"high": 0, "medium": 1, "low": 2}
    return (mode_rank.get(resolution.mode, 9), confidence_rank.get(resolution.confidence, 9))


def _select_card_mode(resolutions: list[ResolutionResult], marketplace_state: str) -> str:
    if marketplace_state in {"wb", "ozon"}:
        resolution = _pick_best_resolution(resolutions, marketplace_state)
        return resolution.mode if resolution is not None else "search"
    if any(item.mode == "exact" for item in resolutions):
        return "exact"
    return "search"


def _pick_resolution_title(resolutions: list[ResolutionResult]) -> str | None:
    for resolution in sorted(resolutions, key=_resolution_rank):
        if resolution.title:
            return resolution.title
    return None


def _build_button_label(marketplace: str, description: str, article: str) -> str:
    marketplace_label = "WB" if marketplace == "wb" else "Ozon"
    cue = _truncate_label(description, 18)
    if not cue or cue == "Товар без подписи":
        cue = article
    return f"{marketplace_label} · {cue}"


def _truncate_label(label: str, limit: int) -> str:
    cleaned = WHITESPACE_PATTERN.sub(" ", label).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 1)].rstrip() + "…"
