from __future__ import annotations

import pytest

from wb_helper.url_utils import InvalidReelUrlError, normalize_reel_url


def test_normalize_reel_url() -> None:
    normalized, shortcode = normalize_reel_url("https://www.instagram.com/reel/ABC123/?utm_source=ig_web_copy_link")

    assert normalized == "https://www.instagram.com/reel/ABC123/"
    assert shortcode == "ABC123"


def test_reject_non_reel_urls() -> None:
    with pytest.raises(InvalidReelUrlError):
        normalize_reel_url("https://www.instagram.com/p/ABC123/")
