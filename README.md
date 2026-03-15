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

## Деплой на Railway

Проект лучше разворачивать в Railway как 4 отдельных сервиса:

- `wb-helper-web` - Telegram webhook;
- `wb-helper-worker` - фоновые задачи;
- `PostgreSQL`;
- `Redis`.

### Что подготовить заранее

1. Репозиторий уже должен быть на GitHub.
2. Нужен Telegram bot token.
3. Для продакшена лучше выпустить новый токен у `@BotFather`, если старый уже светился в переписках или логах.

### Шаг 1. Создай проект в Railway

1. Зайди в Railway.
2. Нажми `New Project`.
3. Выбери `Deploy from GitHub repo`.
4. Выбери репозиторий `wb_helper`.

### Шаг 2. Добавь базы

Внутри проекта Railway:

1. `New` -> `Database` -> `Add PostgreSQL`.
2. `New` -> `Database` -> `Add Redis`.

После этого в проекте будет 3 сервиса: репозиторий, PostgreSQL и Redis.

### Шаг 3. Сделай 2 приложения из одного репозитория

Нужны отдельные сервисы для `web` и `worker`.

1. Открой сервис, созданный из GitHub-репозитория.
2. Переименуй его в `wb-helper-web`.
3. Создай второй сервис из того же репозитория и назови его `wb-helper-worker`.

### Шаг 4. Настрой сборку и запуск

Для сервиса `wb-helper-web`:

- `Source Repo`: этот репозиторий
- `Dockerfile Path`: `Dockerfile.web`

Для сервиса `wb-helper-worker`:

- `Source Repo`: этот репозиторий
- `Dockerfile Path`: `Dockerfile.worker`

### Шаг 5. Заполни переменные окружения

Добавь одинаковые переменные в `wb-helper-web` и `wb-helper-worker`:

```env
BOT_TOKEN=твой_токен_бота
WEBHOOK_SECRET=придумай_длинный_секрет
DATABASE_URL=<сюда DATABASE_URL из Railway Postgres>
REDIS_URL=<сюда REDIS_URL из Railway Redis>
YTDLP_BIN=python
REQUEST_TIMEOUT_SECONDS=8
CACHE_TTL_DAYS=30
LOG_LEVEL=INFO
AUTO_CREATE_SCHEMA=true
WEBHOOK_PATH=/telegram/webhook
EXTRACTOR_TIMEOUT_SECONDS=20
JOB_TIMEOUT_SECONDS=35
WB_BUTTON_CUSTOM_EMOJI_ID=
OZON_BUTTON_CUSTOM_EMOJI_ID=
```

Дополнительно только для `wb-helper-web`:

```env
WEBHOOK_BASE_URL=https://твой-public-domain.up.railway.app
```

Примечания:

- `DATABASE_URL` можно копировать из Railway Postgres как есть. Приложение само приведёт `postgresql://...` к нужному драйверу.
- Если хочешь, вместо `DATABASE_URL` можно задать `POSTGRES_DSN`, но это уже не обязательно.
- `REDIS_URL` можно копировать из Railway Redis как есть.
- Порт руками задавать не нужно: приложение уже умеет читать Railway-переменную `PORT`.

### Шаг 6. Открой публичный домен для web

Для сервиса `wb-helper-web`:

1. Открой вкладку `Settings`.
2. Найди `Networking`.
3. Нажми `Generate Domain`.

Этот домен и будет значением `WEBHOOK_BASE_URL`.

После смены `WEBHOOK_BASE_URL` перезапусти `wb-helper-web`.

### Шаг 7. Проверь health endpoints

Когда `wb-helper-web` поднялся, открой:

- `<WEBHOOK_BASE_URL>/healthz`
- `<WEBHOOK_BASE_URL>/readyz`

Ожидается:

- `/healthz` -> `{"status":"ok"}`
- `/readyz` -> `{"status":"ready",...}`

### Шаг 8. Проверь Telegram webhook

После запуска `wb-helper-web` приложение само вызовет `setWebhook`.
Проверить можно так:

```bash
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

В ответе должен быть URL вида:

```text
https://<your-domain>/telegram/webhook
```

### Шаг 9. Проверка бота

1. Открой чат с ботом.
2. Отправь `/start`.
3. Отправь публичный Instagram Reel.
4. Проверь:
   - `wb-helper-web` принимает update;
   - `wb-helper-worker` берёт задачу;
   - бот возвращает кнопки и описание товаров.

### Если что-то не работает

- `readyz` падает: обычно проблема в `POSTGRES_DSN` или `REDIS_URL`.
- бот молчит: проверь `getWebhookInfo` и значение `WEBHOOK_BASE_URL`.
- задача не обрабатывается: смотри логи `wb-helper-worker`.
- Telegram отвечает 403 на webhook: проверь `WEBHOOK_SECRET`.
