# Mentor Bot + Telegram Web App

## Запуск бота

```bash
python3 -m src.main
```

## Запуск Web App API

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

Web App доступен по адресу:

- `http://localhost:8000/webapp`

## Важно для Telegram Web App

1. Укажи публичный HTTPS URL в `.env`:

```env
WEBAPP_URL=https://<your-domain>/webapp
```

2. Перезапусти бота после обновления `.env`.
3. Нажми `/start` или `/webapp` в боте и открой кнопку `🌐 Открыть Web App`.
