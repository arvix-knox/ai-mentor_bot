# Mentor Bot + Telegram Web App

## Локальный запуск (без сервера и домена)

1. Активируй окружение и установи зависимости:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

2. Запусти API (Web App backend):

```bash
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Если видишь `База данных недоступна`:
- это проблема сети к Postgres (или строки `DATABASE_URL`), а не Web App.
- для старта API статика теперь поднимется даже без БД, но CRUD-эндпоинты будут отдавать `503`.

3. Открой Web App локально в браузере:

- `http://127.0.0.1:8000/webapp`

4. В другом терминале запусти бота:

```bash
python3 -m src.main
```

Если нет доступа к `api.telegram.org`, бот не упадет: будет писать в лог и автоматически ретраить подключение.

5. Для локального открытия из бота:

- команда `/webapp_local` вернет прямую локальную ссылку
- команда `/webapp` откроет URL из `WEBAPP_URL`

## Настройка WEBAPP_URL

По умолчанию в проекте:

```env
WEBAPP_URL=http://127.0.0.1:8000/webapp
```

Если потом нужен прод:

```env
WEBAPP_URL=https://your-domain/webapp
```
