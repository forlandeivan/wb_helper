from __future__ import annotations

import re
from urllib.parse import urlparse


URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com"}
REEL_PATH_PATTERN = re.compile(r"^/(?:reel|reels)/(?P<shortcode>[A-Za-z0-9_-]+)/?$", re.IGNORECASE)


class InvalidReelUrlError(ValueError):
    """Raised when a message does not contain a supported Instagram Reel URL."""


def extract_urls(text: str) -> list[str]:
    return URL_PATTERN.findall(text or "")


def normalize_reel_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise InvalidReelUrlError("Unsupported URL scheme")
    if parsed.netloc.lower() not in INSTAGRAM_HOSTS:
        raise InvalidReelUrlError("Unsupported host")

    match = REEL_PATH_PATTERN.match(parsed.path)
    if not match:
        raise InvalidReelUrlError("Unsupported Instagram path")

    shortcode = match.group("shortcode")
    normalized = f"https://www.instagram.com/reel/{shortcode}/"
    return normalized, shortcode
