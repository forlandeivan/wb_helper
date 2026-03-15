from __future__ import annotations

import json
import subprocess

import pytest

from wb_helper.extractors.reels import ReelExtractionError, YtDlpReelExtractor


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
