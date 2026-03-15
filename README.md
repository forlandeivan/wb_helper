# wb-helper

Telegram-бот для извлечения артикулов WB/Ozon из описания Instagram Reels.

## Что умеет

- принимает одну ссылку на публичный Instagram Reel в личном чате;
- извлекает caption через `yt-dlp` без скачивания видео;
- парсит явные артикулы `WB`, `Ozon`, `арт.`, `артикул`, `sku`;
- возвращает пользователю ссылки на Wildberries и Ozon с inline-кнопками;
- кэширует результат по `shortcode` Reels в PostgreSQL.

## Быстрый старт

1. `yt-dlp` ставится вместе с пакетом. По умолчанию код запускает его через текущий Python (`python -m yt_dlp`). Если нужен другой бинарник, укажи путь в `YTDLP_BIN`.
2. Скопировать `.env.example` в `.env` и заполнить `BOT_TOKEN`, `WEBHOOK_BASE_URL`, `WEBHOOK_SECRET`.
3. Запустить Postgres и Redis.
4. Установить пакет:

```bash
pip install -e .[dev]
```

5. Локальная разработка через polling:

```bash
wb-helper-polling
```

6. Продовый webhook-сервис:

```bash
wb-helper-web
```

7. Worker для фоновых задач:

```bash
wb-helper-worker
```

## Docker Compose

```bash
docker compose up --build
```

`web` слушает `0.0.0.0:8080`. Telegram webhook настраивается как `<WEBHOOK_BASE_URL>/telegram/webhook`.

## Тесты

```bash
pytest
```
