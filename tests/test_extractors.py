from __future__ import annotations

import json
import os
import subprocess

import pytest

from wb_helper.extractors.reels import ReelExtractionError, YtDlpReelExtractor, _build_cookie_text


class CompletedProcessStub:
    def __init__(self, *, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_extractor_returns_caption(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "id": "ABC123",
        "description": "WB 12345678",
        "webpage_url": "https://www.instagram.com/reel/ABC123/",
        "extractor_key": "Instagram",
    }

    def fake_run(*args, **kwargs):
        if "--version" in args[0]:
            return subprocess.CompletedProcess(args[0], 0, stdout="2025.01.01", stderr="")
        return CompletedProcessStub(returncode=0, stdout=json.dumps(payload))

    monkeypatch.setattr("wb_helper.extractors.reels.subprocess.run", fake_run)

    extractor = YtDlpReelExtractor("yt-dlp", 20)
    result = extractor.extract("https://www.instagram.com/reel/ABC123/", "ABC123")

    assert result.caption_raw == "WB 12345678"
    assert result.source_id == "ABC123"


def test_extractor_maps_private_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        return CompletedProcessStub(returncode=1, stderr="Private video")

    monkeypatch.setattr("wb_helper.extractors.reels.subprocess.run", fake_run)

    extractor = YtDlpReelExtractor("yt-dlp", 20)
    with pytest.raises(ReelExtractionError) as exc_info:
        extractor.extract("https://www.instagram.com/reel/ABC123/", "ABC123")

    assert exc_info.value.code == "private_or_unavailable"


def test_extractor_maps_auth_required_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        return CompletedProcessStub(
            returncode=1,
            stderr="Requested content is not available, rate-limit reached or login required. Use --cookies",
        )

    monkeypatch.setattr("wb_helper.extractors.reels.subprocess.run", fake_run)

    extractor = YtDlpReelExtractor("yt-dlp", 20)
    with pytest.raises(ReelExtractionError) as exc_info:
        extractor.extract("https://www.instagram.com/reel/ABC123/", "ABC123")

    assert exc_info.value.code == "auth_required"


def test_extractor_passes_generated_cookie_file(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "id": "ABC123",
        "description": "WB 12345678",
        "webpage_url": "https://www.instagram.com/reel/ABC123/",
        "extractor_key": "Instagram",
    }
    commands: list[list[str]] = []

    def fake_run(*args, **kwargs):
        commands.append(args[0])
        if "--version" in args[0]:
            return subprocess.CompletedProcess(args[0], 0, stdout="2025.01.01", stderr="")
        return CompletedProcessStub(returncode=0, stdout=json.dumps(payload))

    monkeypatch.setattr("wb_helper.extractors.reels.subprocess.run", fake_run)

    extractor = YtDlpReelExtractor("yt-dlp", 20, instagram_sessionid="session-value")
    extractor.extract("https://www.instagram.com/reel/ABC123/", "ABC123")

    extract_command = commands[0]
    assert "--cookies" in extract_command
    cookie_path = extract_command[extract_command.index("--cookies") + 1]
    assert not os.path.exists(cookie_path)


def test_build_cookie_text_from_sessionid() -> None:
    cookie_text = _build_cookie_text(cookies_content=None, instagram_sessionid="session-value")

    assert cookie_text is not None
    assert "# Netscape HTTP Cookie File" in cookie_text
    assert "sessionid\tsession-value" in cookie_text


def test_extractor_auth_mode() -> None:
    assert YtDlpReelExtractor("yt-dlp", 20).auth_mode == "none"
    assert YtDlpReelExtractor("yt-dlp", 20, instagram_sessionid="session").auth_mode == "sessionid"
    assert YtDlpReelExtractor("yt-dlp", 20, cookies_content="cookie").auth_mode == "cookies_content"
    assert YtDlpReelExtractor("yt-dlp", 20, cookies_file="/tmp/cookies.txt").auth_mode == "cookies_file"
