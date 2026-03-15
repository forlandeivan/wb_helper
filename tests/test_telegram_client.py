from __future__ import annotations

from datetime import datetime, timezone

from wb_helper.domain import CachedResultBundle, ExtractionResult
from wb_helper.services.presentation import ButtonBranding
from wb_helper.telegram_client import edit_request_message


class BotStub:
    instances: list["BotStub"] = []

    def __init__(self, token: str) -> None:
        self.token = token
        self.edits: list[dict[str, object]] = []
        self.sent_messages: list[dict[str, object]] = []
        self.session = SessionStub()
        BotStub.instances.append(self)

    async def edit_message_text(self, **kwargs) -> None:
        self.edits.append(kwargs)

    async def send_message(self, **kwargs) -> None:
        self.sent_messages.append(kwargs)


class SessionStub:
    async def close(self) -> None:
        return None


def test_edit_request_message_skips_details_on_failure(monkeypatch) -> None:
    BotStub.instances.clear()
    monkeypatch.setattr("wb_helper.telegram_client.Bot", BotStub)

    bundle = CachedResultBundle(source_id="", extraction=None, candidates=[], resolutions=[])

    edit_request_message(
        bot_token="token",
        chat_id=1,
        message_id=2,
        text="Не удалось извлечь описание.",
        bundle=bundle,
        branding=ButtonBranding(),
        send_details=False,
    )

    bot = BotStub.instances[0]
    assert len(bot.edits) == 1
    assert bot.sent_messages == []


def test_edit_request_message_sends_caption_when_articles_not_found(monkeypatch) -> None:
    BotStub.instances.clear()
    monkeypatch.setattr("wb_helper.telegram_client.Bot", BotStub)

    bundle = CachedResultBundle(
        source_id="ABC123",
        extraction=ExtractionResult(
            source_url="https://www.instagram.com/reel/ABC123/",
            source_id="ABC123",
            caption_raw="Подборка джинс в синем цвете",
            extractor="Instagram",
            extractor_version="1.0",
            extracted_at=datetime.now(timezone.utc),
        ),
        candidates=[],
        resolutions=[],
    )

    edit_request_message(
        bot_token="token",
        chat_id=1,
        message_id=2,
        text="В описании Reels не найдено явных артикулов WB/Ozon.\nНиже отправлю оригинальное описание автора.",
        bundle=bundle,
        branding=ButtonBranding(),
        send_details=True,
    )

    bot = BotStub.instances[0]
    assert len(bot.edits) == 1
    assert len(bot.sent_messages) == 1
    assert bot.sent_messages[0]["text"] == "Подборка джинс в синем цвете"
