# Minibar Bot

Telegram бот для учёта списаний в минибарах.

## Быстрый старт (без Docker)

```bash
pip install -r requirements.txt
cp .env.example .env
# Впиши свой токен в .env
python run.py
```

## Деплой через Docker

```bash
cp .env.example .env
# Впиши свой токен в .env

docker compose up -d
```

Данные (history.json, экспорты) хранятся в Docker volume `bot_data` и переживают перезапуски.

## Обновление бота на сервере

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Переменные окружения

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
