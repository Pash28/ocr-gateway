# OCRGateway

REST API для распознавания текста (OCR) на изображениях и PDF. Построен на **FastAPI** + **Tesseract OCR** + **Celery** + **Redis**. Готов к деплою в Docker.

![CI](https://github.com/YOUR_USERNAME/ocr-gateway/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Что умеет

- **Синхронный OCR** — ответ сразу, для изображений и коротких PDF (≤ 3 страниц по умолчанию)
- **Асинхронный OCR** — ставит задачу в очередь Celery, возвращает `job_id`, результат забираешь позже (для больших PDF)
- **Поддерживаемые форматы**: PNG, JPEG, WebP, BMP, TIFF, PDF (многостраничный)
- **Мультиязычность**: английский, русский и любые другие языки Tesseract через параметр `languages`
- **Confidence score** — средняя уверенность OCR для каждой страницы
- **API-key аутентификация** через заголовок `X-API-Key`
- **Rate limiting**: 30 запросов/минута по умолчанию (настраивается)
- **Swagger UI** на `/docs`, ReDoc на `/redoc`

---

## Стек

| Слой | Технология |
|---|---|
| API | FastAPI 0.111 |
| OCR-движок | Tesseract 5 (pytesseract) |
| PDF → изображения | pdf2image + Poppler |
| Фоновые задачи | Celery 5 |
| Брокер / хранилище статусов | Redis 7 |
| Rate limiting | slowapi |
| Конфигурация | pydantic-settings (.env) |
| Тесты | pytest + httpx + fakeredis |
| Линтер | ruff |
| Контейнеры | Docker + docker-compose |
| CI/CD | GitHub Actions → Render |

---

## Структура проекта

```
ocr-gateway/
├── app/
│   ├── core/
│   │   ├── config.py         # Настройки через pydantic-settings + .env
│   │   ├── exceptions.py     # Доменные исключения → аккуратный JSON
│   │   ├── logging.py        # Единое логирование
│   │   ├── rate_limit.py     # Объект Limiter (slowapi)
│   │   ├── security.py       # Проверка X-API-Key
│   │   └── validation.py     # Валидация загружаемых файлов
│   ├── routers/
│   │   ├── health.py         # GET /api/v1/health
│   │   └── ocr.py            # POST /sync, POST /async, GET /jobs/{id}
│   ├── schemas/
│   │   └── ocr.py            # Pydantic-схемы запросов/ответов
│   ├── services/
│   │   ├── ocr_service.py    # Вся логика OCR (Tesseract)
│   │   └── job_store.py      # CRUD для асинхронных job'ов (Redis)
│   ├── workers/
│   │   ├── celery_app.py     # Инициализация Celery
│   │   └── ocr_tasks.py      # Задача process_file_task
│   └── main.py               # Точка входа FastAPI
├── tests/
│   ├── conftest.py           # Фикстуры: клиент, тестовые файлы
│   ├── test_auth.py
│   ├── test_health.py
│   ├── test_job_store.py
│   └── test_ocr_sync.py
├── .github/workflows/ci.yml  # GitHub Actions CI/CD
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

---

## Быстрый старт

### Вариант 1 — Docker (рекомендуется)

```bash
# 1. Клонируем
git clone https://github.com/YOUR_USERNAME/ocr-gateway.git
cd ocr-gateway

# 2. Настраиваем переменные окружения
cp .env.example .env
# Отредактируйте .env: задайте API_KEY

# 3. Поднимаем всё одной командой
docker compose up --build

# Сервис доступен на http://localhost:8000
```

### Вариант 2 — локально (без Docker)

Требования: Python 3.12+, Tesseract 5, Poppler

```bash
# Установка системных зависимостей
# macOS:
brew install tesseract tesseract-lang poppler

# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus poppler-utils

# Установка Python-зависимостей
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Конфиг
cp .env.example .env

# Запуск API (Redis нужен только для /async эндпоинта)
uvicorn app.main:app --reload

# Запуск Celery-воркера (отдельный терминал)
celery -A app.workers.celery_app worker --loglevel=info
```

---

## API

### Аутентификация

Все OCR-эндпоинты требуют заголовок:
```
X-API-Key: your-secret-key
```

### Синхронное распознавание

```bash
curl -X POST http://localhost:8000/api/v1/ocr/sync \
  -H "X-API-Key: dev-secret-key" \
  -F "file=@document.png" \
  -F "languages=eng"
```

**Ответ:**
```json
{
  "filename": "document.png",
  "content_type": "image/png",
  "languages": "eng",
  "total_pages": 1,
  "processing_time_ms": 342.5,
  "pages": [
    {
      "page_number": 1,
      "text": "Hello, World! This is OCR.",
      "mean_confidence": 94.7,
      "word_count": 5
    }
  ]
}
```

### Асинхронное распознавание (большие PDF)

```bash
# 1. Ставим задачу в очередь
curl -X POST http://localhost:8000/api/v1/ocr/async \
  -H "X-API-Key: dev-secret-key" \
  -F "file=@big_document.pdf" \
  -F "languages=eng+rus"
```

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "pending",
  "status_url": "/api/v1/ocr/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "created_at": "2024-01-15T12:00:00Z"
}
```

```bash
# 2. Проверяем статус
curl http://localhost:8000/api/v1/ocr/jobs/3fa85f64-5717-4562-b3fc-2c963f66afa6 \
  -H "X-API-Key: dev-secret-key"
```

Поле `status` меняется: `pending → processing → completed` (или `failed`).

### Health check

```bash
curl http://localhost:8000/api/v1/health
```

```json
{
  "status": "ok",
  "app_name": "OCRGateway",
  "environment": "docker",
  "tesseract_available": true,
  "redis_available": true
}
```

---

## Тесты

```bash
# Запуск всех тестов
pytest tests/ -v

# С покрытием
pip install pytest-cov
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## Деплой на Render

1. Создайте новый **Web Service** на [render.com](https://render.com), подключите репозиторий
2. В настройках сервиса выберите **Docker** как Environment
3. Добавьте переменные окружения в Render Dashboard:
   ```
   API_KEY=your-production-secret
   REDIS_URL=redis://...  # URL из Render Redis instance
   ENVIRONMENT=production
   DEBUG=false
   ```
4. Создайте **Redis** инстанс на Render, скопируйте Internal URL в `REDIS_URL`
5. Для CI/CD: скопируйте **Deploy Hook URL** из Render → Settings, добавьте как GitHub Secret `RENDER_DEPLOY_HOOK_URL`

После этого каждый push в `main` → тесты → Docker build → автодеплой на Render.

---

## Переменные окружения

| Переменная | Дефолт | Описание |
|---|---|---|
| `API_KEY` | `dev-secret-key` | Секретный ключ для X-API-Key |
| `API_KEY_ENABLED` | `true` | Включить аутентификацию |
| `DEFAULT_LANGUAGES` | `eng` | Языки OCR по умолчанию |
| `MAX_UPLOAD_SIZE_MB` | `20` | Максимальный размер файла |
| `MAX_PDF_PAGES_SYNC` | `3` | Лимит страниц для /sync |
| `REDIS_URL` | `redis://localhost:6379/0` | URL Redis |
| `RATE_LIMIT_PER_MINUTE` | `30` | Rate limit |
| `DEBUG` | `false` | Verbose логи |

---

## Лицензия

MIT
